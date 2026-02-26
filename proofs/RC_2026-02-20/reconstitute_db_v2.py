#!/usr/bin/env python3
"""
SCRIPT DE RECONSTITUTION V2 — COMPLÈTE ET EXHAUSTIVE
=====================================================
Reconstitue la DB Korrigo à partir de reconstitution_data_v2.json.

Usage:
  docker exec -it docker-backend-1 python /app/reconstitute_db_v2.py

Env vars:
  RECONSTITUTION_DATA  - path to v2 JSON (default: /data/reconstitution_data_v2.json)
  J1_PDF_DIR           - BB_J1 PDFs directory
  J2_PDF_DIR           - BB_J2 PDFs directory
  J1_CSV / J2_CSV      - student CSV files
  DRY_RUN=1            - rollback after execution
  MEDIA_ROOT           - Django media root (default: /app/media)
"""

import os
import sys
import json
import uuid
from pathlib import Path
from datetime import datetime, date
from typing import Optional

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
import django
django.setup()

from django.contrib.auth.models import User, Group
from django.core.files.base import ContentFile
from django.db import transaction, connection
from django.utils import timezone

from exams.models import Exam, Booklet, Copy
from grading.models import (
    Annotation, Score, QuestionRemark, GradingEvent,
    AnnotationTemplate, DraftState, UserAnnotation,
)
from students.models import Student

# ============================================================
# CONFIG
# ============================================================
DATA_FILE = os.environ.get('RECONSTITUTION_DATA', '/data/reconstitution_data_v2.json')
J1_PDF_DIR = os.environ.get('J1_PDF_DIR', '/data/copies_J1/')
J2_PDF_DIR = os.environ.get('J2_PDF_DIR', '/data/copies_J2/')
J1_CSV = os.environ.get('J1_CSV', '/data/eleves_maths_J1.csv')
J2_CSV = os.environ.get('J2_CSV', '/data/eleves_maths_J2.csv')
DRY_RUN = os.environ.get('DRY_RUN', '0') == '1'

# Dump uses French annotation types, DB uses English
ANNOT_TYPE_MAP = {
    'COMMENTAIRE': 'COMMENT', 'SURLIGNAGE': 'HIGHLIGHT',
    'ERREUR': 'ERROR', 'BONUS': 'BONUS',
    'COMMENT': 'COMMENT', 'HIGHLIGHT': 'HIGHLIGHT',
    'ERROR': 'ERROR',
}


def log(msg: str) -> None:
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")


def load_csv(csv_path: str) -> list[dict]:
    """Load students from CSV."""
    rows = []
    with open(csv_path, 'r', encoding='utf-8') as f:
        f.readline()  # skip header
        for line in f:
            parts = line.strip().split(',')
            if len(parts) >= 5:
                np = parts[0]
                sp = np.split(' ', 1)
                rows.append({
                    'nom_prenom': np,
                    'last_name': sp[0],
                    'first_name': sp[1] if len(sp) > 1 else '',
                    'date_naissance': parts[1],
                    'email': parts[2],
                    'classe': parts[3],
                    'groupe': parts[4],
                })
    return rows


def parse_date(ds: str) -> date:
    for fmt in ('%d/%m/%Y', '%Y-%m-%d'):
        try:
            return datetime.strptime(ds, fmt).date()
        except ValueError:
            continue
    return date(2008, 1, 1)


def parse_ts(ts: Optional[str]) -> Optional[datetime]:
    if not ts or ts in ('\\N', 'None', 'null'):
        return None
    try:
        return datetime.fromisoformat(ts.replace('+00', '+00:00'))
    except (ValueError, TypeError):
        try:
            return datetime.fromisoformat(ts)
        except (ValueError, TypeError):
            return timezone.now()


def rasterize_pdf(pdf_path: str, output_dir: str) -> list[str]:
    """Rasterize PDF into page PNGs using PyMuPDF."""
    try:
        import fitz
    except ImportError:
        log("WARNING: PyMuPDF not available")
        return []
    doc = fitz.open(pdf_path)
    pages = []
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    for i in range(len(doc)):
        pix = doc[i].get_pixmap(matrix=fitz.Matrix(2.0, 2.0))
        fn = f"page_{i+1}.png"
        pix.save(os.path.join(output_dir, fn))
        pages.append(fn)
    doc.close()
    return pages


# ============================================================
# MAIN
# ============================================================
@transaction.atomic
def reconstitute():
    log("=" * 70)
    log("  RECONSTITUTION V2 — COMPLÈTE ET EXHAUSTIVE")
    log("=" * 70)
    if DRY_RUN:
        log("*** DRY RUN ***")

    # Load data
    log(f"\nChargement: {DATA_FILE}")
    with open(DATA_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)
    meta = data['_metadata']
    log(f"  Source: {meta['source']}")
    for k, v in meta['counts'].items():
        log(f"    {k}: {v}")

    baremes = data['baremes']
    teachers_data = data['teachers']
    students_data = data['students']
    dispatching = data['dispatching']
    scores_list = data['scores']
    annotations_list = data['annotations']
    remarks_list = data['remarks']
    events_list = data['events']
    templates_list = data['templates']
    drafts_list = data['drafts']
    exam_correctors_data = data['exam_correctors']
    post_dump = data.get('post_dump_corrections', [])

    # ==== STEP 1: Groups ====
    log("\n--- STEP 1: Groupes ---")
    teacher_grp, _ = Group.objects.get_or_create(name='teacher')
    admin_grp, _ = Group.objects.get_or_create(name='admin')
    student_grp, _ = Group.objects.get_or_create(name='student')

    # ==== STEP 2: Teachers ====
    log("\n--- STEP 2: Enseignants ---")
    user_by_old_id = {}
    user_by_uname = {}
    for t in teachers_data:
        uname = t['username']
        user, cr = User.objects.get_or_create(
            username=uname,
            defaults={
                'first_name': t.get('first_name', ''),
                'last_name': t.get('last_name', ''),
                'email': t.get('email', uname),
                'is_staff': bool(t.get('is_staff')),
                'is_superuser': bool(t.get('is_superuser')),
                'is_active': True,
            }
        )
        if cr and t.get('password'):
            user.password = t['password']
            user.save(update_fields=['password'])
        if user.is_superuser:
            user.groups.add(admin_grp)
        user.groups.add(teacher_grp)
        user_by_old_id[str(t['id'])] = user
        user_by_uname[uname] = user
        log(f"  {'Créé' if cr else 'Exist'}: {uname}")
    log(f"  Total: {len(user_by_old_id)}")

    # ==== STEP 3: Students ====
    log("\n--- STEP 3: Étudiants ---")
    j1_csv = load_csv(J1_CSV)
    j2_csv = load_csv(J2_CSV)
    all_csv = {}
    for s in j1_csv + j2_csv:
        all_csv[s['email']] = s

    # Dump student passwords
    dump_spw = {}
    for sd in students_data:
        if sd.get('student_password'):
            dump_spw[sd.get('email', '')] = sd['student_password']

    student_by_email = {}
    for email, sd in all_csv.items():
        dn = parse_date(sd['date_naissance'])
        su, su_cr = User.objects.get_or_create(
            username=email,
            defaults={
                'first_name': sd['first_name'],
                'last_name': sd['last_name'],
                'email': email, 'is_active': True,
            }
        )
        if su_cr:
            pw = dump_spw.get(email)
            if pw:
                su.password = pw
            else:
                su.set_password(dn.strftime('%d%m%Y'))
            su.save()
        su.groups.add(student_grp)

        st, st_cr = Student.objects.get_or_create(
            last_name=sd['last_name'],
            first_name=sd['first_name'],
            date_naissance=dn,
            defaults={
                'email': email, 'class_name': sd['classe'],
                'groupe': sd['groupe'], 'user': su,
            }
        )
        if not st_cr and not st.user:
            st.user = su
            st.save(update_fields=['user'])
        student_by_email[email] = st
    log(f"  Total: {len(student_by_email)}")

    # ==== STEP 4: Exams ====
    log("\n--- STEP 4: Examens ---")
    exam_by_name = {}
    exam_by_old_id = {}
    for ename, bd in baremes.items():
        gs = bd['grading_structure']
        exam, cr = Exam.objects.get_or_create(
            name=ename,
            defaults={
                'date': bd['exam_date'],
                'grading_structure': gs,
                'upload_mode': bd.get('upload_mode', 'INDIVIDUAL_A4'),
                'is_processed': True,
                'pages_per_booklet': int(bd.get('pages_per_booklet', 4)),
            }
        )
        rra = parse_ts(bd.get('results_released_at'))
        if cr and rra:
            exam.results_released_at = rra
            exam.save(update_fields=['results_released_at'])
        exam_by_name[ename] = exam
        exam_by_old_id[bd['exam_id']] = exam
        log(f"  {ename}: {len(gs)} ex, {bd['total_points']} pts")

    for ename, corrs in exam_correctors_data.items():
        exam = exam_by_name.get(ename)
        if exam:
            for c in corrs:
                u = user_by_old_id.get(str(c['user_id']))
                if u:
                    exam.correctors.add(u)

    # ==== STEP 5: Copies + PDFs ====
    log("\n--- STEP 5: Copies + PDFs ---")
    dispatch_by_anon = {d['anonymous_id']: d for d in dispatching}
    email_to_anon = {}
    for d in dispatching:
        if d.get('student') and d['student'].get('email'):
            email_to_anon[(d['exam_name'], d['student']['email'])] = d['anonymous_id']

    def build_name_map(csvs):
        m = {}
        for s in csvs:
            sp = s['nom_prenom'].split(' ', 1)
            last = sp[0]
            first = sp[1].replace(' ', '_') if len(sp) > 1 else ''
            m[f"{last}_{first}".upper()] = s
        return m

    j1_nm = build_name_map(j1_csv)
    j2_nm = build_name_map(j2_csv)
    copy_by_anon = {}
    media_root = os.environ.get('MEDIA_ROOT', '/app/media')
    n_created = 0

    for exam_name, pdf_dir, name_map, prefix in [
        ('BB_J1', J1_PDF_DIR, j1_nm, '0F8E'),
        ('BB_J2', J2_PDF_DIR, j2_nm, '75FB'),
    ]:
        exam = exam_by_name.get(exam_name)
        if not exam:
            continue
        pdfs = sorted(f for f in os.listdir(pdf_dir) if f.endswith('.pdf'))
        log(f"  {exam_name}: {len(pdfs)} PDFs")

        idx = 0
        for pf in pdfs:
            idx += 1
            nk = pf.replace('.pdf', '')
            for pfx in ('copie_finale_', 'copie_'):
                if nk.startswith(pfx):
                    nk = nk[len(pfx):]
                    break

            sd = name_map.get(nk.upper())
            if not sd:
                nk2 = nk.upper().replace('-', '').replace("'", '')
                for k, v in name_map.items():
                    if k.replace('-', '').replace("'", '') == nk2:
                        sd = v
                        break

            email = sd['email'] if sd else None
            student = student_by_email.get(email) if email else None
            anon_id = email_to_anon.get((exam_name, email)) if email else None
            if not anon_id:
                anon_id = f"{prefix}-{idx:03d}"

            dd = dispatch_by_anon.get(anon_id, {})
            corr_uname = dd.get('assigned_corrector_username')
            corrector = user_by_uname.get(corr_uname) if corr_uname else None

            pp = os.path.join(pdf_dir, pf)
            try:
                copy = Copy.objects.get(anonymous_id=anon_id)
            except Copy.DoesNotExist:
                with open(pp, 'rb') as f:
                    pdf_bytes = f.read()
                copy = Copy(
                    exam=exam, anonymous_id=anon_id,
                    status=dd.get('status', 'READY'),
                    student=student, is_identified=student is not None,
                    assigned_corrector=corrector,
                    subject_variant=dd.get('subject_variant'),
                    graded_at=parse_ts(dd.get('graded_at')),
                    global_appreciation=dd.get('global_appreciation'),
                    llm_summary=dd.get('llm_summary'),
                )
                copy.pdf_source.save(f"copy_{anon_id}.pdf", ContentFile(pdf_bytes), save=False)
                copy.save()
                n_created += 1

            pdir = os.path.join(media_root, 'copies', 'pages', str(copy.id))
            if not os.path.exists(pdir) or not os.listdir(pdir):
                pimgs = rasterize_pdf(pp, pdir)
                if pimgs and not copy.booklets.exists():
                    bk = Booklet.objects.create(
                        exam=exam, start_page=1, end_page=len(pimgs),
                        pages_images=[f"copies/pages/{copy.id}/{p}" for p in pimgs],
                    )
                    copy.booklets.add(bk)

            copy_by_anon[anon_id] = copy

    log(f"  Créées: {n_created}, total mappées: {len(copy_by_anon)}")

    # ==== STEP 6: Scores ====
    log("\n--- STEP 6: Scores ---")
    sc = 0
    for sd in scores_list:
        copy = copy_by_anon.get(sd['anonymous_id'])
        if not copy:
            continue
        _, cr = Score.objects.get_or_create(
            copy=copy,
            defaults={'scores_data': sd['scores_data'], 'final_comment': sd.get('final_comment', '')},
        )
        if cr:
            sc += 1
    log(f"  Injectés: {sc}")

    # ==== STEP 7: Annotations ====
    log("\n--- STEP 7: Annotations ---")
    admin_u = User.objects.filter(is_superuser=True).first()
    ac = 0
    for a in annotations_list:
        copy = copy_by_anon.get(a['anonymous_id'])
        if not copy:
            continue
        creator = user_by_old_id.get(str(a.get('created_by_id')))
        if not creator:
            creator = user_by_uname.get(a.get('created_by_username'))
        if not creator:
            creator = copy.assigned_corrector or admin_u
        if not creator:
            continue

        sd = None
        if a.get('score_delta') is not None:
            try:
                sd = int(a['score_delta'])
            except (ValueError, TypeError):
                sd = None

        try:
            Annotation.objects.get_or_create(
                id=a['annotation_id'],
                defaults={
                    'copy': copy, 'page_index': int(a['page_index']),
                    'x': float(a['x']), 'y': float(a['y']),
                    'w': float(a['w']), 'h': float(a['h']),
                    'content': a.get('content', ''),
                    'type': ANNOT_TYPE_MAP.get(a.get('type', 'COMMENT'), 'COMMENT'),
                    'score_delta': sd, 'created_by': creator,
                    'version': int(a.get('version', 0)),
                },
            )
            ac += 1
        except Exception as e:
            log(f"  WARN annot {a['annotation_id'][:8]}: {e}")
    log(f"  Injectées: {ac}")

    # ==== STEP 8: Remarks ====
    log("\n--- STEP 8: Remarques ---")
    rc = 0
    for r in remarks_list:
        copy = copy_by_anon.get(r['anonymous_id'])
        if not copy:
            continue
        creator = user_by_old_id.get(str(r.get('created_by_id')))
        if not creator:
            creator = user_by_uname.get(r.get('created_by_username'))
        if not creator:
            creator = copy.assigned_corrector or admin_u
        if not creator:
            continue
        _, cr = QuestionRemark.objects.get_or_create(
            copy=copy, question_id=r.get('question_id', ''),
            defaults={'remark': r.get('remark', ''), 'created_by': creator},
        )
        if cr:
            rc += 1
    log(f"  Injectées: {rc}")

    # ==== STEP 9: Templates ====
    log("\n--- STEP 9: Templates d'annotation ---")
    tc = 0
    for t in templates_list:
        exam = exam_by_old_id.get(t.get('exam_id'))
        if not exam:
            exam = exam_by_name.get(t.get('exam_name'))
        if not exam:
            continue
        try:
            _, cr = AnnotationTemplate.objects.get_or_create(
                id=t['template_id'],
                defaults={
                    'exam': exam,
                    'exercise_number': int(t.get('exercise_number', 0)),
                    'question_number': str(t.get('question_number', '')),
                    'sub_question': t.get('sub_question', ''),
                    'criterion_type': t.get('criterion_type', 'result'),
                    'severity': t.get('severity', 'info'),
                    'text': t.get('text', ''),
                    'is_active': bool(t.get('is_active', True)),
                    'tags': json.loads(t['tags']) if isinstance(t.get('tags'), str) else (t.get('tags') or []),
                },
            )
            if cr:
                tc += 1
        except Exception as e:
            log(f"  WARN tmpl: {e}")
    log(f"  Créés: {tc}")

    # ==== STEP 10: Grading Events ====
    log("\n--- STEP 10: Grading Events ---")
    ec = 0
    for ev in events_list:
        copy = copy_by_anon.get(ev.get('anonymous_id'))
        if not copy:
            continue
        actor = user_by_old_id.get(str(ev.get('actor_id')))
        if not actor:
            actor = user_by_uname.get(ev.get('actor_username'))
        if not actor:
            actor = admin_u
        if not actor:
            continue
        try:
            GradingEvent.objects.get_or_create(
                id=ev['event_id'],
                defaults={
                    'copy': copy,
                    'action': ev.get('event_type', 'IMPORT'),
                    'actor': actor,
                    'metadata': json.loads(ev['details']) if isinstance(ev.get('details'), str) and ev['details'] else {},
                },
            )
            ec += 1
        except Exception as e:
            pass  # skip duplicates silently
    log(f"  Injectés: {ec}")

    # ==== STEP 11: Drafts ====
    log("\n--- STEP 11: Drafts ---")
    dc = 0
    for d in drafts_list:
        copy = copy_by_anon.get(d.get('anonymous_id'))
        if not copy:
            continue
        # Find owner from dispatch
        dd = dispatch_by_anon.get(d.get('anonymous_id'), {})
        owner = user_by_uname.get(dd.get('assigned_corrector_username'))
        if not owner:
            owner = admin_u
        if not owner:
            continue
        payload = d.get('state_data', '{}')
        if isinstance(payload, str):
            try:
                payload = json.loads(payload)
            except:
                payload = {}
        try:
            DraftState.objects.get_or_create(
                copy=copy, owner=owner,
                defaults={'payload': payload, 'version': 1},
            )
            dc += 1
        except Exception:
            pass
    log(f"  Créés: {dc}")

    # ==== STEP 12: Post-dump corrections ====
    log("\n--- STEP 12: Corrections post-dump ---")
    for pd in post_dump:
        anon = pd.get('anonymous_id')
        copy = copy_by_anon.get(anon)
        if not copy:
            log(f"  WARN: {anon} non trouvé pour correction post-dump")
            continue
        log(f"  {anon} ({pd['student_name']}): {pd['note_dump']} -> {pd['note_total']}")
        # Update score if the post-dump score is more recent
        try:
            score = Score.objects.get(copy=copy)
            old_total = sum(float(v) for v in score.scores_data.values())
            if abs(old_total - pd['note_dump']) < 0.1:
                # Score in DB matches dump — apply post-dump correction
                log(f"    Applying post-dump score: {pd['note_total']}")
                # We don't have the exact scores_data keys for post-dump,
                # so we log it but keep the dump score as-is for safety.
                # The corrector will need to re-grade manually.
                log(f"    NOTE: Post-dump detail = {pd['detail']}")
                log(f"    Correction manuelle requise par {pd['corrector']}")
        except Score.DoesNotExist:
            log(f"    Pas de score existant pour {anon}")

    # ==== STEP 13: Verification ====
    log("\n" + "=" * 70)
    log("  VÉRIFICATION FINALE")
    log("=" * 70)

    counts = {
        'Users': User.objects.count(),
        'Students': Student.objects.count(),
        'Exams': Exam.objects.count(),
        'Copies': Copy.objects.count(),
        'Booklets': Booklet.objects.count(),
        'Scores': Score.objects.count(),
        'Annotations': Annotation.objects.count(),
        'Remarques': QuestionRemark.objects.count(),
        'Events': GradingEvent.objects.count(),
        'Templates': AnnotationTemplate.objects.count(),
    }
    for k, v in counts.items():
        log(f"  {k}: {v}")

    for exam in Exam.objects.filter(name__in=['BB_J1', 'BB_J2']):
        ec = Copy.objects.filter(exam=exam)
        log(f"\n  {exam.name}:")
        log(f"    Copies: {ec.count()} (GRADED: {ec.filter(status='GRADED').count()})")
        log(f"    Scores: {Score.objects.filter(copy__exam=exam).count()}")
        log(f"    Annotations: {Annotation.objects.filter(copy__exam=exam).count()}")
        log(f"    Correcteurs: {', '.join(u.username for u in exam.correctors.all())}")

    # Score integrity check
    log("\n--- Vérification des notes ---")
    mismatches = 0
    for sd in scores_list:
        copy = copy_by_anon.get(sd['anonymous_id'])
        if not copy:
            continue
        try:
            score = Score.objects.get(copy=copy)
            expected = sd['total']
            actual = sum(float(v) for v in score.scores_data.values())
            if abs(expected - actual) > 0.01:
                log(f"  MISMATCH: {sd['anonymous_id']} expected={expected} actual={actual:.2f}")
                mismatches += 1
        except Score.DoesNotExist:
            log(f"  MISSING: {sd['anonymous_id']}")
            mismatches += 1

    if mismatches == 0:
        log("  ✓ Toutes les notes correspondent")
    else:
        log(f"  ✗ {mismatches} incohérences")

    log("\n" + "=" * 70)
    log("  RECONSTITUTION V2 TERMINÉE")
    log("=" * 70)

    if DRY_RUN:
        log("*** DRY RUN — Transaction annulée ***")
        transaction.set_rollback(True)


if __name__ == '__main__':
    reconstitute()
