#!/usr/bin/env python3
"""
SCRIPT DE RECONSTITUTION COMPLÈTE DE LA BASE DE DONNÉES KORRIGO
================================================================
Ce script reconstitue la DB Korrigo à partir de :
1. Les données extraites du dump PostgreSQL du 20/02/2026
2. Les PDFs source de vérité (BB_J1 + BB_J2)
3. Les CSV d'élèves

À exécuter dans le conteneur backend Docker :
  docker exec -it docker-backend-1 python /app/reconstitute_db.py

Prérequis :
- Les fichiers reconstitution_data.json, CSVs, et PDFs doivent être
  accessibles depuis le conteneur (montés en volume)
"""

import os
import sys
import json
import uuid
import shutil
from pathlib import Path
from datetime import datetime, date

# Django setup
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
import django
django.setup()

from django.contrib.auth.models import User, Group
from django.core.files.base import ContentFile
from django.db import transaction
from django.utils import timezone

from exams.models import Exam, Booklet, Copy
from grading.models import Annotation, Score, QuestionRemark, GradingEvent, AnnotationTemplate
from students.models import Student

# ============================================================
# CONFIGURATION - À adapter selon le montage des volumes
# ============================================================
DATA_FILE = os.environ.get(
    'RECONSTITUTION_DATA',
    '/data/reconstitution_data.json'
)
J1_PDF_DIR = os.environ.get(
    'J1_PDF_DIR',
    '/data/copies_J1/'
)
J2_PDF_DIR = os.environ.get(
    'J2_PDF_DIR',
    '/data/copies_J2/'
)
J1_CSV = os.environ.get(
    'J1_CSV',
    '/data/eleves_maths_J1.csv'
)
J2_CSV = os.environ.get(
    'J2_CSV',
    '/data/eleves_maths_J2.csv'
)

DRY_RUN = os.environ.get('DRY_RUN', '0') == '1'


def log(msg: str) -> None:
    """Print with timestamp."""
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")


def load_csv_students(csv_path: str) -> list[dict]:
    """Load students from CSV file."""
    students = []
    with open(csv_path, 'r', encoding='utf-8') as f:
        header = f.readline().strip().split(',')
        for line in f:
            parts = line.strip().split(',')
            if len(parts) >= 5:
                nom_prenom = parts[0]
                # Split "NOM PRENOM" -> last_name, first_name
                name_parts = nom_prenom.split(' ', 1)
                last_name = name_parts[0] if name_parts else ''
                first_name = name_parts[1] if len(name_parts) > 1 else ''
                students.append({
                    'nom_prenom': nom_prenom,
                    'last_name': last_name,
                    'first_name': first_name,
                    'date_naissance': parts[1],
                    'email': parts[2],
                    'classe': parts[3],
                    'groupe': parts[4],
                })
    return students


def parse_date_naissance(date_str: str) -> date:
    """Parse date from DD/MM/YYYY format."""
    try:
        return datetime.strptime(date_str, '%d/%m/%Y').date()
    except ValueError:
        try:
            return datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            return date(2008, 1, 1)


def parse_timestamp(ts_str: str | None) -> datetime | None:
    """Parse a PostgreSQL timestamp string."""
    if not ts_str or ts_str == '\\N':
        return None
    try:
        # Format: 2026-02-14 11:19:07.3857+00
        return datetime.fromisoformat(ts_str.replace('+00', '+00:00'))
    except (ValueError, TypeError):
        try:
            return datetime.fromisoformat(ts_str)
        except (ValueError, TypeError):
            return timezone.now()


def rasterize_pdf(pdf_path: str, output_dir: str) -> list[str]:
    """
    Rasterize a PDF into page images using PyMuPDF.
    Returns list of relative image paths.
    """
    try:
        import fitz  # PyMuPDF
    except ImportError:
        log("WARNING: PyMuPDF not available, skipping rasterization")
        return []

    doc = fitz.open(pdf_path)
    pages = []
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    for i in range(len(doc)):
        page = doc[i]
        mat = fitz.Matrix(2.0, 2.0)  # 2x zoom for quality
        pix = page.get_pixmap(matrix=mat)
        img_filename = f"page_{i+1}.png"
        img_path = os.path.join(output_dir, img_filename)
        pix.save(img_path)
        pages.append(img_filename)

    doc.close()
    return pages


def generate_anonymous_id(exam_prefix: str, index: int) -> str:
    """Generate sequential anonymous ID like 0F8E-001."""
    return f"{exam_prefix}-{index:03d}"


# ============================================================
# MAIN RECONSTITUTION
# ============================================================
@transaction.atomic
def reconstitute():
    """Main reconstitution logic."""
    log("=" * 70)
    log("RECONSTITUTION COMPLÈTE DE LA BASE KORRIGO")
    log("=" * 70)

    if DRY_RUN:
        log("*** MODE DRY RUN - Aucune modification ne sera effectuée ***")

    # Load reconstitution data
    log(f"Chargement des données: {DATA_FILE}")
    with open(DATA_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)

    copies_data = data['copies']
    exam_data = data['exams']
    teachers_data = data['teachers']
    teacher_passwords = data['teacher_passwords']
    correctors_data = data['exam_correctors']
    templates_data = data.get('annotation_templates', [])
    grading_structures = data.get('grading_structures', {})

    # ============================================================
    # STEP 1: Create groups
    # ============================================================
    log("\n--- STEP 1: Groupes ---")
    teacher_group, _ = Group.objects.get_or_create(name='teacher')
    admin_group, _ = Group.objects.get_or_create(name='admin')
    student_group, _ = Group.objects.get_or_create(name='student')
    log(f"  Groupes créés: teacher, admin, student")

    # ============================================================
    # STEP 2: Create admin + teacher users
    # ============================================================
    log("\n--- STEP 2: Utilisateurs (admin + enseignants) ---")
    user_map = {}  # old_id -> new User

    for t in teachers_data:
        username = t['username']
        old_id = t['id']

        user, created = User.objects.get_or_create(
            username=username,
            defaults={
                'first_name': t.get('first_name', ''),
                'last_name': t.get('last_name', ''),
                'email': t.get('email', username),
                'is_staff': t.get('is_staff', 'f') == 't',
                'is_superuser': t.get('is_superuser', 'f') == 't',
                'is_active': True,
            }
        )
        if created:
            # Restore the hashed password directly
            pwd = teacher_passwords.get(username)
            if pwd:
                user.password = pwd
                user.save(update_fields=['password'])
            log(f"  Créé: {username} (staff={user.is_staff}, super={user.is_superuser})")
        else:
            log(f"  Existant: {username}")

        # Add to groups
        if user.is_superuser:
            user.groups.add(admin_group)
        user.groups.add(teacher_group)

        user_map[old_id] = user

    log(f"  Total enseignants: {len(user_map)}")

    # ============================================================
    # STEP 3: Create students + student users
    # ============================================================
    log("\n--- STEP 3: Étudiants ---")
    j1_students = load_csv_students(J1_CSV)
    j2_students = load_csv_students(J2_CSV)

    # Merge unique students by email
    all_students_by_email = {}
    for s in j1_students + j2_students:
        all_students_by_email[s['email']] = s

    student_map = {}  # email -> Student
    for email, sdata in all_students_by_email.items():
        dn = parse_date_naissance(sdata['date_naissance'])

        # Create user for student
        student_user, _ = User.objects.get_or_create(
            username=email,
            defaults={
                'first_name': sdata['first_name'],
                'last_name': sdata['last_name'],
                'email': email,
                'is_active': True,
            }
        )
        if not student_user.has_usable_password():
            student_user.set_password(dn.strftime('%d%m%Y'))
            student_user.save()
        student_user.groups.add(student_group)

        student, created = Student.objects.get_or_create(
            last_name=sdata['last_name'],
            first_name=sdata['first_name'],
            date_naissance=dn,
            defaults={
                'email': email,
                'class_name': sdata['classe'],
                'groupe': sdata['groupe'],
                'user': student_user,
            }
        )
        if not created and not student.user:
            student.user = student_user
            student.save(update_fields=['user'])

        student_map[email] = student

    log(f"  Total étudiants: {len(student_map)}")

    # ============================================================
    # STEP 4: Create exams with grading structures
    # ============================================================
    log("\n--- STEP 4: Examens ---")
    exam_map = {}  # old_id -> new Exam

    for e in exam_data:
        if e['name'] == 'Prod Validation Exam - Bac Blanc Maths':
            continue  # Skip test exam

        gs = e.get('grading_structure')
        if isinstance(gs, str):
            try:
                gs = json.loads(gs)
            except (json.JSONDecodeError, TypeError):
                gs = []

        exam, created = Exam.objects.get_or_create(
            name=e['name'],
            defaults={
                'date': e['date'],
                'grading_structure': gs or [],
                'upload_mode': 'INDIVIDUAL_A4',
                'is_processed': True,
                'pages_per_booklet': 1,
            }
        )
        exam_map[e['id']] = exam
        status = "Créé" if created else "Existant"
        log(f"  {status}: {exam.name} (ID: {exam.id})")

    # Assign correctors
    for ec in correctors_data:
        exam = exam_map.get(ec['exam_id'])
        user = user_map.get(ec['user_id'])
        if exam and user:
            exam.correctors.add(user)
            log(f"  Correcteur {user.username} -> {exam.name}")

    # ============================================================
    # STEP 5: Import copies from PDFs
    # ============================================================
    log("\n--- STEP 5: Import des copies PDF ---")

    # Build mapping: student_email -> copy_data from dump
    email_to_dump_copy = {}
    for copy_id, cd in copies_data.items():
        if cd.get('student_email'):
            key = (cd['exam'], cd['student_email'])
            email_to_dump_copy[key] = cd

    # Map pdf filename -> student email
    def build_pdf_to_email(csv_students: list[dict], exam_name: str) -> dict:
        """Build mapping from PDF filename pattern to student data."""
        mapping = {}
        for s in csv_students:
            name_parts = s['nom_prenom'].split(' ', 1)
            last = name_parts[0]
            first = name_parts[1].replace(' ', '_') if len(name_parts) > 1 else ''
            # J1 pattern: copie_finale_LAST_FIRST.pdf
            # J2 pattern: LAST_FIRST.pdf
            key = f"{last}_{first}".upper()
            mapping[key] = s
        return mapping

    j1_name_map = build_pdf_to_email(j1_students, 'BB_J1')
    j2_name_map = build_pdf_to_email(j2_students, 'BB_J2')

    copy_map = {}  # old_copy_id -> new Copy
    media_root = os.environ.get('MEDIA_ROOT', '/app/media')

    for exam_name, pdf_dir, csv_students, name_map, prefix in [
        ('BB_J1', J1_PDF_DIR, j1_students, j1_name_map, '0F8E'),
        ('BB_J2', J2_PDF_DIR, j2_students, j2_name_map, '75FB'),
    ]:
        exam = None
        for eid, ex in exam_map.items():
            if ex.name == exam_name:
                exam = ex
                break
        if not exam:
            log(f"  ERREUR: Exam {exam_name} non trouvé!")
            continue

        pdf_files = sorted(os.listdir(pdf_dir))
        log(f"\n  {exam_name}: {len(pdf_files)} PDFs dans {pdf_dir}")

        idx = 0
        for pdf_file in pdf_files:
            if not pdf_file.endswith('.pdf'):
                continue
            idx += 1

            # Extract student name from filename
            name_key = pdf_file.replace('.pdf', '')
            if name_key.startswith('copie_finale_'):
                name_key = name_key.replace('copie_finale_', '')

            # Find student
            student_data = name_map.get(name_key.upper())
            if not student_data:
                # Try fuzzy match
                for k, v in name_map.items():
                    if k.replace('-', '').replace("'", '') == name_key.upper().replace('-', '').replace("'", ''):
                        student_data = v
                        break

            student = student_map.get(student_data['email']) if student_data else None
            email = student_data['email'] if student_data else None

            # Find dump data for this copy
            dump_copy = email_to_dump_copy.get((exam_name, email)) if email else None
            old_copy_id = dump_copy['id'] if dump_copy else None
            anon_id = dump_copy['anonymous_id'] if dump_copy else generate_anonymous_id(prefix, idx)

            # Determine status from dump
            status = 'READY'
            if dump_copy:
                status = dump_copy.get('status', 'READY')

            # Find corrector
            corrector = None
            if dump_copy and dump_copy.get('corrector_id'):
                corrector = user_map.get(dump_copy['corrector_id'])

            # Read PDF
            pdf_path = os.path.join(pdf_dir, pdf_file)
            with open(pdf_path, 'rb') as f:
                pdf_bytes = f.read()

            # Create or get copy
            try:
                copy = Copy.objects.get(anonymous_id=anon_id)
                log(f"    Existant: {anon_id} ({pdf_file})")
            except Copy.DoesNotExist:
                copy = Copy(
                    exam=exam,
                    anonymous_id=anon_id,
                    status=status,
                    student=student,
                    is_identified=student is not None,
                    assigned_corrector=corrector,
                )
                if dump_copy:
                    if dump_copy.get('graded_at'):
                        copy.graded_at = parse_timestamp(dump_copy['graded_at'])
                    if dump_copy.get('global_appreciation'):
                        copy.global_appreciation = dump_copy['global_appreciation']
                    if dump_copy.get('llm_summary'):
                        copy.llm_summary = dump_copy['llm_summary']
                    if dump_copy.get('dispatch_run_id'):
                        try:
                            copy.dispatch_run_id = uuid.UUID(dump_copy['dispatch_run_id'])
                        except (ValueError, TypeError):
                            pass

                # Save PDF source
                copy.pdf_source.save(
                    f"copie_{name_key}.pdf",
                    ContentFile(pdf_bytes),
                    save=False
                )
                copy.save()
                log(f"    Créé: {anon_id} -> {student or 'N/A'} [{status}]")

            # Rasterize PDF into page images
            pages_dir = os.path.join(media_root, 'copies', 'pages', str(copy.id))
            page_images = rasterize_pdf(pdf_path, pages_dir)

            # Create booklet
            if page_images:
                booklet = Booklet.objects.create(
                    exam=exam,
                    start_page=1,
                    end_page=len(page_images),
                    pages_images=[f"copies/pages/{copy.id}/{p}" for p in page_images],
                )
                copy.booklets.add(booklet)

            if old_copy_id:
                copy_map[old_copy_id] = copy

    log(f"\n  Total copies créées/trouvées: {Copy.objects.count()}")
    log(f"  Copies mappées au dump: {len(copy_map)}")

    # ============================================================
    # STEP 6: Inject scores
    # ============================================================
    log("\n--- STEP 6: Injection des scores (105 notes) ---")
    scores_created = 0

    for old_copy_id, cd in copies_data.items():
        if not cd.get('scores_data'):
            continue
        copy = copy_map.get(old_copy_id)
        if not copy:
            log(f"  WARN: Copy {old_copy_id} ({cd.get('student_last_name')}) non mappée")
            continue

        score, created = Score.objects.get_or_create(
            copy=copy,
            defaults={
                'scores_data': cd['scores_data'],
                'final_comment': cd.get('score_final_comment') or '',
            }
        )
        if created:
            scores_created += 1

    log(f"  Scores injectés: {scores_created}")

    # ============================================================
    # STEP 7: Inject annotations
    # ============================================================
    log("\n--- STEP 7: Injection des annotations (544) ---")
    annots_created = 0

    for old_copy_id, cd in copies_data.items():
        if not cd.get('annotations'):
            continue
        copy = copy_map.get(old_copy_id)
        if not copy:
            continue

        for a in cd['annotations']:
            creator = user_map.get(a.get('created_by_id'))
            if not creator:
                # Fallback to the corrector
                creator = copy.assigned_corrector or User.objects.filter(is_superuser=True).first()

            try:
                score_delta = int(a['score_delta']) if a.get('score_delta') and a['score_delta'] != '\\N' else None
            except (ValueError, TypeError):
                score_delta = None

            Annotation.objects.create(
                id=a['id'],
                copy=copy,
                page_index=int(a.get('page_index', 0)),
                x=float(a.get('x', 0)),
                y=float(a.get('y', 0)),
                w=float(a.get('w', 0.1)),
                h=float(a.get('h', 0.1)),
                content=a.get('content', ''),
                type=a.get('type', 'COMMENT'),
                score_delta=score_delta,
                created_by=creator,
                version=int(a.get('version', 0)),
            )
            annots_created += 1

    log(f"  Annotations injectées: {annots_created}")

    # ============================================================
    # STEP 8: Inject question remarks
    # ============================================================
    log("\n--- STEP 8: Injection des remarques (1075) ---")
    remarks_created = 0

    for old_copy_id, cd in copies_data.items():
        if not cd.get('remarks'):
            continue
        copy = copy_map.get(old_copy_id)
        if not copy:
            continue

        for r in cd['remarks']:
            creator = user_map.get(r.get('created_by_id'))
            if not creator:
                creator = copy.assigned_corrector or User.objects.filter(is_superuser=True).first()

            QuestionRemark.objects.get_or_create(
                copy=copy,
                question_id=r.get('question_id', ''),
                defaults={
                    'remark': r.get('remark', ''),
                    'created_by': creator,
                }
            )
            remarks_created += 1

    log(f"  Remarques injectées: {remarks_created}")

    # ============================================================
    # STEP 9: Inject annotation templates
    # ============================================================
    log("\n--- STEP 9: Templates d'annotation ---")
    templates_created = 0

    for t in templates_data:
        owner = user_map.get(t.get('owner_id'))
        if not owner:
            continue
        exam = exam_map.get(t.get('exam_id'))

        try:
            AnnotationTemplate.objects.get_or_create(
                id=t['id'],
                defaults={
                    'title': t.get('title', ''),
                    'content': t.get('content', ''),
                    'type': t.get('type', 'COMMENT'),
                    'owner': owner,
                    'exam': exam,
                    'is_shared': t.get('is_shared', 'f') == 't',
                    'usage_count': int(t.get('usage_count', 0)),
                    'category': t.get('category', ''),
                    'shortcut': t.get('shortcut', ''),
                    'score_delta': int(t['score_delta']) if t.get('score_delta') and t['score_delta'] != '\\N' else None,
                }
            )
            templates_created += 1
        except Exception as e:
            log(f"  WARN: Template {t['id']}: {e}")

    log(f"  Templates créés: {templates_created}")

    # ============================================================
    # STEP 10: Final verification
    # ============================================================
    log("\n" + "=" * 70)
    log("VÉRIFICATION FINALE")
    log("=" * 70)

    total_users = User.objects.count()
    total_students = Student.objects.count()
    total_exams = Exam.objects.count()
    total_copies = Copy.objects.count()
    total_booklets = Booklet.objects.count()
    total_scores = Score.objects.count()
    total_annots = Annotation.objects.count()
    total_remarks = QuestionRemark.objects.count()

    log(f"  Users: {total_users}")
    log(f"  Students: {total_students}")
    log(f"  Exams: {total_exams}")
    log(f"  Copies: {total_copies}")
    log(f"  Booklets: {total_booklets}")
    log(f"  Scores: {total_scores}")
    log(f"  Annotations: {total_annots}")
    log(f"  Remarques: {total_remarks}")

    for exam in Exam.objects.all():
        exam_copies = Copy.objects.filter(exam=exam)
        graded = exam_copies.filter(status='GRADED').count()
        with_scores = Score.objects.filter(copy__exam=exam).count()
        log(f"\n  {exam.name}:")
        log(f"    Copies: {exam_copies.count()} (GRADED: {graded})")
        log(f"    Scores: {with_scores}")
        log(f"    Correcteurs: {', '.join(u.username for u in exam.correctors.all())}")

    # Verify scores match
    log("\n--- Vérification des notes ---")
    mismatches = 0
    for old_id, cd in copies_data.items():
        if not cd.get('scores_data'):
            continue
        copy = copy_map.get(old_id)
        if not copy:
            continue
        try:
            score = Score.objects.get(copy=copy)
            expected_total = sum(float(v) for v in cd['scores_data'].values())
            actual_total = sum(float(v) for v in score.scores_data.values())
            if abs(expected_total - actual_total) > 0.01:
                log(f"  MISMATCH: {copy.anonymous_id} expected={expected_total} actual={actual_total}")
                mismatches += 1
        except Score.DoesNotExist:
            log(f"  MISSING: {copy.anonymous_id}")
            mismatches += 1

    if mismatches == 0:
        log("  ✓ Toutes les notes correspondent")
    else:
        log(f"  ✗ {mismatches} incohérences détectées")

    log("\n" + "=" * 70)
    log("RECONSTITUTION TERMINÉE")
    log("=" * 70)

    if DRY_RUN:
        log("*** DRY RUN - Transaction annulée ***")
        transaction.set_rollback(True)


if __name__ == '__main__':
    reconstitute()
