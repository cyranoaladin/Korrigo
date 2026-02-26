#!/usr/bin/env python3
"""
Analyse complète du dump PostgreSQL du 20/02/2026.
Croise toutes les données extraites pour préparer la reconstitution.
Génère un rapport JSON complet prêt à injecter dans la nouvelle DB.
"""

import json
import os
from pathlib import Path
from collections import defaultdict

DATA_DIR = Path("/home/alaeddine/viatique__PMF/proofs/RC_2026-02-20/extracted_data")
OUTPUT = Path("/home/alaeddine/viatique__PMF/proofs/RC_2026-02-20/reconstitution_data.json")

# Sources de vérité pour les PDFs
J1_PDF_DIR = Path("/home/alaeddine/Téléchargements/scan_J1_BB_maths/copies_finales_J1_korrigo")
J2_PDF_DIR = Path("/home/alaeddine/Bureau/scan_J2_BB_maths/Copies_completes")

# CSV élèves
J1_CSV = Path("/home/alaeddine/viatique__PMF/eleves_maths_J1.csv")
J2_CSV = Path("/home/alaeddine/viatique__PMF/eleves_maths_J2.csv")


def load_json(name: str) -> list[dict]:
    """Load a JSON file from extracted data."""
    path = DATA_DIR / f"{name}.json"
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def load_csv_students(csv_path: Path) -> list[dict]:
    """Load students from CSV."""
    students = []
    with open(csv_path, 'r', encoding='utf-8') as f:
        header = f.readline().strip().split(',')
        for line in f:
            parts = line.strip().split(',')
            if len(parts) >= 5:
                students.append({
                    'nom_prenom': parts[0],
                    'date_naissance': parts[1],
                    'email': parts[2],
                    'classe': parts[3],
                    'groupe': parts[4],
                })
    return students


def main():
    print("=" * 70)
    print("ANALYSE COMPLÈTE DU DUMP - PRÉPARATION RECONSTITUTION")
    print("=" * 70)

    # Load all data
    users = load_json("auth_user")
    user_groups = load_json("auth_user_groups")
    groups = load_json("auth_group")
    students = load_json("students_student")
    exams = load_json("exams_exam")
    copies = load_json("exams_copy")
    booklets = load_json("exams_booklet")
    copy_booklets = load_json("exams_copy_booklets")
    exam_correctors = load_json("exams_exam_correctors")
    annotations = load_json("grading_annotation")
    scores = load_json("grading_score")
    remarks = load_json("grading_questionremark")
    events = load_json("grading_gradingevent")
    drafts = load_json("grading_draftstate")
    profiles = load_json("core_userprofile")
    templates = load_json("grading_annotationtemplate")

    # Index maps
    user_by_id = {u['id']: u for u in users}
    student_by_id = {s['id']: s for s in students}
    exam_by_id = {e['id']: e for e in exams}
    copy_by_id = {c['id']: c for c in copies}

    # Group ID -> name
    group_by_id = {g['id']: g['name'] for g in groups}
    user_group_map = defaultdict(list)
    for ug in user_groups:
        user_group_map[ug['user_id']].append(group_by_id.get(ug['group_id'], '?'))

    # Scores indexed by copy_id
    score_by_copy = {s['copy_id']: s for s in scores}

    # Annotations by copy_id
    annots_by_copy = defaultdict(list)
    for a in annotations:
        annots_by_copy[a['copy_id']].append(a)

    # Remarks by copy_id
    remarks_by_copy = defaultdict(list)
    for r in remarks:
        remarks_by_copy[r['copy_id']].append(r)

    # Events by copy_id
    events_by_copy = defaultdict(list)
    for ev in events:
        events_by_copy[ev['copy_id']].append(ev)

    # Copy-booklet mapping
    booklet_for_copy = {}
    booklet_by_id = {b['id']: b for b in booklets}
    for cb in copy_booklets:
        booklet_for_copy[cb['copy_id']] = cb['booklet_id']

    # ============================================================
    # 1. EXAMS
    # ============================================================
    print("\n" + "=" * 50)
    print("1. EXAMENS")
    print("=" * 50)

    exam_ids = {}
    for e in exams:
        print(f"\n  ID: {e['id']}")
        print(f"  Nom: {e['name']}")
        print(f"  Date: {e['date']}")
        print(f"  Barème: {e.get('grading_structure', 'N/A')[:200]}")
        exam_ids[e['name']] = e['id']

    BB_J1_ID = exam_ids.get('BB_J1')
    BB_J2_ID = exam_ids.get('BB_J2')

    # ============================================================
    # 2. CORRECTORS
    # ============================================================
    print("\n" + "=" * 50)
    print("2. CORRECTEURS")
    print("=" * 50)

    for ec in exam_correctors:
        exam_name = exam_by_id.get(ec['exam_id'], {}).get('name', '?')
        user = user_by_id.get(ec['user_id'], {})
        print(f"  {exam_name}: {user.get('username', '?')} (user_id={ec['user_id']})")

    # ============================================================
    # 3. USERS (teachers only)
    # ============================================================
    print("\n" + "=" * 50)
    print("3. UTILISATEURS (enseignants)")
    print("=" * 50)

    teachers = []
    for u in users:
        groups_list = user_group_map.get(u['id'], [])
        if 'teacher' in groups_list or 'admin' in groups_list:
            teachers.append(u)
            print(f"  {u['username']} (id={u['id']}) groups={groups_list} staff={u['is_staff']} super={u['is_superuser']}")

    # ============================================================
    # 4. COPIES ANALYSIS
    # ============================================================
    print("\n" + "=" * 50)
    print("4. COPIES - ANALYSE DÉTAILLÉE")
    print("=" * 50)

    reconstitution = {
        'exams': exams,
        'teachers': [{k: v for k, v in u.items() if k != 'password'} for u in teachers],
        'teacher_passwords': {u['username']: u['password'] for u in teachers},
        'exam_correctors': exam_correctors,
        'grading_structures': {e['name']: e.get('grading_structure') for e in exams},
        'copies': {},
        'annotation_templates': templates,
        'stats': {}
    }

    # Load CSV students
    j1_csv_students = load_csv_students(J1_CSV)
    j2_csv_students = load_csv_students(J2_CSV)
    csv_email_to_name = {}
    for s in j1_csv_students + j2_csv_students:
        csv_email_to_name[s['email']] = s['nom_prenom']

    # Process each exam
    for exam_name, exam_id in [('BB_J1', BB_J1_ID), ('BB_J2', BB_J2_ID)]:
        if not exam_id:
            continue

        print(f"\n  --- {exam_name} (ID: {exam_id}) ---")
        exam_copies = [c for c in copies if c['exam_id'] == exam_id]

        stats = {
            'total': len(exam_copies),
            'graded': 0,
            'with_scores': 0,
            'with_annotations': 0,
            'with_remarks': 0,
            'with_appreciation': 0,
            'with_llm_summary': 0,
            'without_data': 0,
            'by_corrector': defaultdict(lambda: {'assigned': 0, 'graded': 0, 'with_scores': 0}),
        }

        for c in exam_copies:
            copy_id = c['id']
            student = student_by_id.get(c.get('student_id'), {})
            corrector = user_by_id.get(c.get('assigned_corrector_id'), {})
            corrector_name = corrector.get('username', 'N/A')

            score = score_by_copy.get(copy_id)
            copy_annots = annots_by_copy.get(copy_id, [])
            copy_remarks = remarks_by_copy.get(copy_id, [])
            copy_events = events_by_copy.get(copy_id, [])

            has_score = score is not None
            has_annots = len(copy_annots) > 0
            has_remarks = len(copy_remarks) > 0
            has_appreciation = c.get('global_appreciation') not in (None, '', '\\N')
            has_llm = c.get('llm_summary') not in (None, '', '\\N')

            # Compute total from scores_data
            total_score = None
            if has_score and score.get('scores_data'):
                try:
                    sd = json.loads(score['scores_data'])
                    total_score = sum(float(v) for v in sd.values())
                except (json.JSONDecodeError, TypeError, ValueError):
                    total_score = None

            stats['by_corrector'][corrector_name]['assigned'] += 1
            if c['status'] == 'GRADED':
                stats['graded'] += 1
                stats['by_corrector'][corrector_name]['graded'] += 1
            if has_score:
                stats['with_scores'] += 1
                stats['by_corrector'][corrector_name]['with_scores'] += 1
            if has_annots:
                stats['with_annotations'] += 1
            if has_remarks:
                stats['with_remarks'] += 1
            if has_appreciation:
                stats['with_appreciation'] += 1
            if has_llm:
                stats['with_llm_summary'] += 1
            if not has_score and c['status'] != 'GRADED':
                stats['without_data'] += 1

            # Store copy data for reconstitution
            copy_data = {
                'id': copy_id,
                'anonymous_id': c['anonymous_id'],
                'exam': exam_name,
                'exam_id': exam_id,
                'status': c['status'],
                'student_email': student.get('email', ''),
                'student_first_name': student.get('first_name', ''),
                'student_last_name': student.get('last_name', ''),
                'student_id': c.get('student_id'),
                'corrector_username': corrector_name,
                'corrector_id': c.get('assigned_corrector_id'),
                'graded_at': c.get('graded_at'),
                'global_appreciation': c.get('global_appreciation') if has_appreciation else None,
                'llm_summary': c.get('llm_summary') if has_llm else None,
                'total_score': total_score,
                'scores_data': json.loads(score['scores_data']) if has_score and score.get('scores_data') else None,
                'score_final_comment': score.get('final_comment') if has_score else None,
                'annotations': copy_annots,
                'remarks': copy_remarks,
                'events_count': len(copy_events),
                'pdf_source': c.get('pdf_source'),
            }
            reconstitution['copies'][copy_id] = copy_data

        # Print stats
        print(f"    Total copies: {stats['total']}")
        print(f"    GRADED: {stats['graded']}")
        print(f"    Avec scores: {stats['with_scores']}")
        print(f"    Avec annotations: {stats['with_annotations']}")
        print(f"    Avec remarques: {stats['with_remarks']}")
        print(f"    Avec appreciation: {stats['with_appreciation']}")
        print(f"    Avec bilan LLM: {stats['with_llm_summary']}")
        print(f"    Sans données: {stats['without_data']}")

        print(f"\n    Par correcteur:")
        for corr, cstats in sorted(stats['by_corrector'].items()):
            print(f"      {corr}: assignées={cstats['assigned']} graded={cstats['graded']} scores={cstats['with_scores']}")

        reconstitution['stats'][exam_name] = {
            'total': stats['total'],
            'graded': stats['graded'],
            'with_scores': stats['with_scores'],
            'with_annotations': stats['with_annotations'],
            'with_remarks': stats['with_remarks'],
            'with_appreciation': stats['with_appreciation'],
            'with_llm_summary': stats['with_llm_summary'],
            'without_data': stats['without_data'],
        }

    # ============================================================
    # 5. PDF SOURCE VERIFICATION
    # ============================================================
    print("\n" + "=" * 50)
    print("5. VÉRIFICATION DES PDFs SOURCE DE VÉRITÉ")
    print("=" * 50)

    j1_pdfs = sorted(os.listdir(J1_PDF_DIR)) if J1_PDF_DIR.exists() else []
    j2_pdfs = sorted(os.listdir(J2_PDF_DIR)) if J2_PDF_DIR.exists() else []
    print(f"  BB_J1 PDFs (source vérité): {len(j1_pdfs)}")
    print(f"  BB_J2 PDFs (source vérité): {len(j2_pdfs)}")

    reconstitution['pdf_sources'] = {
        'BB_J1': {
            'dir': str(J1_PDF_DIR),
            'count': len(j1_pdfs),
            'files': j1_pdfs,
        },
        'BB_J2': {
            'dir': str(J2_PDF_DIR),
            'count': len(j2_pdfs),
            'files': j2_pdfs,
        }
    }

    # ============================================================
    # 6. CSV STUDENTS
    # ============================================================
    print("\n" + "=" * 50)
    print("6. ÉTUDIANTS CSV")
    print("=" * 50)
    print(f"  BB_J1: {len(j1_csv_students)} étudiants")
    print(f"  BB_J2: {len(j2_csv_students)} étudiants")

    reconstitution['csv_students'] = {
        'BB_J1': j1_csv_students,
        'BB_J2': j2_csv_students,
    }

    # ============================================================
    # 7. ALL STUDENTS FROM DB
    # ============================================================
    reconstitution['db_students'] = [{k: v for k, v in s.items()} for s in students]
    reconstitution['db_users'] = [{k: v for k, v in u.items() if k != 'password'} for u in users]
    reconstitution['user_groups'] = user_groups

    # ============================================================
    # 8. GRADING STRUCTURES (barèmes)
    # ============================================================
    print("\n" + "=" * 50)
    print("7. BARÈMES")
    print("=" * 50)
    for e in exams:
        gs = e.get('grading_structure')
        if gs and gs != '\\N':
            print(f"\n  {e['name']}:")
            try:
                parsed = json.loads(gs)
                if isinstance(parsed, list):
                    for item in parsed:
                        label = item.get('label', '?')
                        pts = item.get('points', 0)
                        children = item.get('children', [])
                        print(f"    {label}: {pts} pts ({len(children)} sous-questions)")
                elif isinstance(parsed, dict):
                    for q, details in sorted(parsed.items()):
                        print(f"    {q}: {details}")
            except (json.JSONDecodeError, TypeError):
                print(f"    (raw): {gs[:200]}")

    # ============================================================
    # SAVE
    # ============================================================
    with open(OUTPUT, 'w', encoding='utf-8') as f:
        json.dump(reconstitution, f, ensure_ascii=False, indent=2, default=str)

    print(f"\n{'=' * 70}")
    print(f"DONNÉES DE RECONSTITUTION SAUVEGARDÉES: {OUTPUT}")
    print(f"  Copies avec données: {sum(1 for c in reconstitution['copies'].values() if c['scores_data'])}")
    print(f"  Copies sans données: {sum(1 for c in reconstitution['copies'].values() if not c['scores_data'])}")
    print(f"  Total annotations: {len(annotations)}")
    print(f"  Total remarques: {len(remarks)}")
    print(f"  Total events: {len(events)}")
    print(f"  Templates annotation: {len(templates)}")
    print(f"{'=' * 70}")


if __name__ == '__main__':
    main()
