"""
Audit complet de l'état des corrections par correcteur.
Pour chaque copie : élève, statut, scores par exercice, annotations, remarques, appréciation.
Run inside Django shell on the server.
"""
import json
from exams.models import Copy, Exam
from grading.models import Score, Annotation, GradingEvent
from django.contrib.auth import get_user_model

User = get_user_model()

# Get both exams
exams = Exam.objects.all().order_by('name')
for exam in exams:
    print(f"\n{'#'*80}")
    print(f"# EXAM: {exam.name} (id={exam.id})")
    print(f"{'#'*80}")

    # Get all correctors for this exam
    correctors = User.objects.filter(
        assigned_copies__exam=exam
    ).distinct().order_by('email')

    for corrector in correctors:
        copies = Copy.objects.filter(
            exam=exam,
            assigned_corrector=corrector
        ).order_by('anonymous_id')

        total_copies = copies.count()
        graded = copies.filter(status='GRADED').count()
        ready = copies.filter(status='READY').count()
        staging = copies.filter(status='STAGING').count()

        print(f"\n{'='*80}")
        print(f"CORRECTEUR: {corrector.first_name} {corrector.last_name} ({corrector.email})")
        print(f"  Copies: {total_copies} | GRADED: {graded} | READY: {ready} | STAGING: {staging}")
        print(f"{'='*80}")

        for copy in copies:
            student = copy.student
            student_name = "NON IDENTIFIE"
            if student and student.user:
                student_name = f"{student.user.last_name} {student.user.first_name}"
            elif student:
                student_name = f"Student#{student.id}"

            # Score
            score_obj = Score.objects.filter(copy=copy).first()
            scores_data = score_obj.scores_data if score_obj and score_obj.scores_data else {}
            final_comment = score_obj.final_comment if score_obj else ""
            nb_questions = len(scores_data)

            # Group scores by exercise
            ex_scores = {}
            for qid, val in sorted(scores_data.items()):
                ex = qid.split('.')[0]
                if ex not in ex_scores:
                    ex_scores[ex] = {}
                ex_scores[ex][qid] = val

            total_score = round(sum(v for v in scores_data.values() if isinstance(v, (int, float))), 2)

            # Annotations
            annotations = Annotation.objects.filter(copy=copy)
            nb_annotations = annotations.count()
            annotation_types = {}
            for ann in annotations:
                t = ann.type or 'UNKNOWN'
                annotation_types[t] = annotation_types.get(t, 0) + 1

            # Remarks (from score_obj or annotations with remarks)
            remarks = []
            for ann in annotations:
                if ann.content and ann.content.strip():
                    remarks.append(f"p{ann.page_index+1 if ann.page_index is not None else '?'}: {ann.content[:80]}")

            # Appreciation
            appreciation = copy.global_appreciation or ""

            # Grading events
            events = GradingEvent.objects.filter(copy=copy).count()

            # Subject variant
            variant = copy.subject_variant or "-"

            print(f"\n  --- {copy.anonymous_id} | {student_name} | Status: {copy.status} | Sujet: {variant} ---")
            print(f"      Note globale: {total_score}/20 ({nb_questions} questions)")

            if ex_scores:
                for ex_name, questions in sorted(ex_scores.items()):
                    ex_total = round(sum(v for v in questions.values() if isinstance(v, (int, float))), 2)
                    q_detail = ", ".join(f"{q}={v}" for q, v in sorted(questions.items()))
                    print(f"      Ex {ex_name}: {ex_total} pts [{q_detail}]")
            else:
                print(f"      AUCUN SCORE SAISI")

            print(f"      Annotations: {nb_annotations}", end="")
            if annotation_types:
                print(f" ({', '.join(f'{t}:{n}' for t, n in sorted(annotation_types.items()))})", end="")
            print()

            if remarks:
                print(f"      Remarques ({len(remarks)}):")
                for r in remarks[:10]:
                    print(f"        - {r}")
                if len(remarks) > 10:
                    print(f"        ... et {len(remarks)-10} de plus")
            else:
                print(f"      Remarques: AUCUNE")

            if appreciation:
                print(f"      Appreciation: {appreciation[:200]}{'...' if len(appreciation) > 200 else ''}")
            else:
                print(f"      Appreciation: AUCUNE")

            if final_comment:
                print(f"      Commentaire final: {final_comment[:200]}")

            print(f"      Events de correction: {events}")

        # Summary for this corrector
        all_scores = []
        copies_with_scores = 0
        copies_with_annotations = 0
        copies_with_appreciation = 0
        copies_complete_27q = 0
        for copy in copies:
            s = Score.objects.filter(copy=copy).first()
            if s and s.scores_data and len(s.scores_data) > 0:
                copies_with_scores += 1
                total = round(sum(v for v in s.scores_data.values() if isinstance(v, (int, float))), 2)
                all_scores.append(total)
                if len(s.scores_data) >= 27:
                    copies_complete_27q += 1
            ann_count = Annotation.objects.filter(copy=copy).count()
            if ann_count > 0:
                copies_with_annotations += 1
            if copy.global_appreciation:
                copies_with_appreciation += 1

        avg = round(sum(all_scores) / len(all_scores), 2) if all_scores else 0
        min_s = min(all_scores) if all_scores else 0
        max_s = max(all_scores) if all_scores else 0

        print(f"\n  >>> RESUME {corrector.first_name} {corrector.last_name}:")
        print(f"      Copies avec scores: {copies_with_scores}/{total_copies}")
        print(f"      Copies 27 questions completes: {copies_complete_27q}/{total_copies}")
        print(f"      Copies avec annotations: {copies_with_annotations}/{total_copies}")
        print(f"      Copies avec appreciation: {copies_with_appreciation}/{total_copies}")
        print(f"      Copies GRADED: {graded}/{total_copies}")
        if all_scores:
            print(f"      Moyenne: {avg}/20 | Min: {min_s}/20 | Max: {max_s}/20")

print(f"\n\n{'#'*80}")
print(f"# RESUME GLOBAL")
print(f"{'#'*80}")

all_copies = Copy.objects.all()
total = all_copies.count()
graded = all_copies.filter(status='GRADED').count()
with_scores = 0
with_27q = 0
with_annotations = 0
with_appreciation = 0
for c in all_copies:
    s = Score.objects.filter(copy=c).first()
    if s and s.scores_data and len(s.scores_data) > 0:
        with_scores += 1
        if len(s.scores_data) >= 27:
            with_27q += 1
    if Annotation.objects.filter(copy=c).exists():
        with_annotations += 1
    if c.global_appreciation:
        with_appreciation += 1

print(f"Total copies: {total}")
print(f"GRADED: {graded}/{total}")
print(f"Avec scores: {with_scores}/{total}")
print(f"Avec 27 questions: {with_27q}/{total}")
print(f"Avec annotations: {with_annotations}/{total}")
print(f"Avec appreciation: {with_appreciation}/{total}")
