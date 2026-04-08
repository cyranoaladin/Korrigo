"""
Views pour la fonctionnalité "Mes Élèves" des correcteurs.
Permet à un correcteur de voir les élèves de son groupe avec leurs bilans.
"""
from rest_framework import views, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from exams.permissions import IsTeacherOrAdmin

from django.db.models import Prefetch
from students.models import Student
from exams.models import Copy
from grading.models import Score, Annotation, QuestionRemark

from django.db.models import Q

try:
    from exams.models import TeacherGroupAssignment
    _HAS_TGA_MODEL = True
except ImportError:
    _HAS_TGA_MODEL = False


def _get_teacher_assignments(user, level=None):
    """Renvoie la liste des assignations d'un correcteur, optionnellement filtrée par niveau.
    Chaque élément est un dict {level, assignment_type, group_name}."""
    if not _HAS_TGA_MODEL:
        return []
    qs = TeacherGroupAssignment.objects.filter(teacher=user)
    if level:
        qs = qs.filter(level=level)
    return list(qs.values('level', 'assignment_type', 'group_name'))


# Map level to class_name prefix patterns for cross-level disambiguation
_LEVEL_CLASS_PREFIXES = {
    'terminale': ['T.', 'Terminale'],
    'premiere':  ['1.'],
    'troisieme': ['3.'],
}


def _class_prefix_q(level):
    """Build a Q filter restricting to students whose class_name matches the level."""
    prefixes = _LEVEL_CLASS_PREFIXES.get(level, [])
    if not prefixes:
        return Q()
    q = Q(pk__in=[])  # empty base
    for pfx in prefixes:
        q |= Q(class_name__startswith=pfx)
    return q


def _students_for_assignments(assignments):
    """Construit un queryset Student couvrant toutes les assignations données,
    en filtrant par niveau pour éviter les collisions (ex: G1 terminale vs G1 première)."""
    q = Q(pk__in=[])  # empty base
    for a in assignments:
        level_q = _class_prefix_q(a['level'])
        if a['assignment_type'] == 'classe':
            q |= (Q(class_name=a['group_name']) & level_q)
        else:
            q |= (Q(groupe=a['group_name']) & level_q)
    return Student.objects.filter(q)


def _student_matches_assignments(student, assignments):
    """Vérifie si un élève correspond à au moins une assignation (avec vérification de niveau)."""
    for a in assignments:
        # Check level prefix
        prefixes = _LEVEL_CLASS_PREFIXES.get(a['level'], [])
        level_ok = any(student.class_name.startswith(pfx) for pfx in prefixes) if prefixes else True
        if not level_ok:
            continue
        if a['assignment_type'] == 'classe' and student.class_name == a['group_name']:
            return True
        if a['assignment_type'] == 'groupe' and student.groupe == a['group_name']:
            return True
    return False


def _build_question_labels(exam):
    """Construit un mapping {question_id: label_lisible} depuis le grading_structure de l'examen.
    Utilise le module partagé grading_utils pour gérer les deux formats d'ID (UUID et positionnel)."""
    from exams.grading_utils import build_question_labels
    if not exam:
        return {}
    return build_question_labels(exam.grading_structure)


class MyStudentsListView(views.APIView):
    """
    GET /api/grading/my-students/
    Liste les élèves du groupe du correcteur connecté avec leurs notes.
    """
    permission_classes = [IsTeacherOrAdmin]

    def get(self, request):
        level = request.query_params.get('level', None)
        assignments = _get_teacher_assignments(request.user, level=level)
        
        if not assignments:
            return Response({
                'detail': 'Aucun groupe associé à ce correcteur.' + (f' (niveau={level})' if level else ''),
                'students': []
            }, status=status.HTTP_200_OK)
        
        # Récupérer les élèves couverts par toutes les assignations
        students = _students_for_assignments(assignments).order_by('last_name', 'first_name').prefetch_related(
            Prefetch('copies', queryset=Copy.objects.select_related('exam', 'assigned_corrector').prefetch_related(
                Prefetch('scores', queryset=Score.objects.only('id', 'copy_id', 'scores_data'))
            ))
        )

        result = []
        for student in students:
            copies = student.copies.all()
            
            student_data = {
                'id': student.id,
                'first_name': student.first_name,
                'last_name': student.last_name,
                'class_name': student.class_name,
                'groupe': student.groupe,
                'email': student.email,
                'copies': []
            }
            
            for copy in copies:
                # Utiliser les scores prefetchés (scores.all() exploite le cache prefetch)
                scores_list = list(copy.scores.all())
                score_obj = scores_list[0] if scores_list else None
                total_score = None
                if score_obj and score_obj.scores_data:
                    total_score = sum(
                        float(v) for v in score_obj.scores_data.values()
                        if v is not None and v != ''
                    )
                
                # Nom du correcteur
                corrector_name = None
                if copy.assigned_corrector:
                    corrector_name = f"{copy.assigned_corrector.first_name} {copy.assigned_corrector.last_name}".strip()
                    if not corrector_name:
                        corrector_name = copy.assigned_corrector.username
                
                student_data['copies'].append({
                    'copy_id': str(copy.id),
                    'exam_name': copy.exam.name if copy.exam else 'N/A',
                    'status': copy.status,
                    'total_score': round(total_score, 2) if total_score is not None else None,
                    'anonymous_id': copy.anonymous_id,
                    'corrector_name': corrector_name,
                })
            
            result.append(student_data)
        
        group_labels = [f"{a['group_name']} ({a['level']})" for a in assignments]
        return Response({
            'assignments': assignments,
            'groupe': ', '.join(group_labels),
            'count': len(result),
            'students': result
        })


class StudentBilanView(views.APIView):
    """
    GET /api/grading/students/<student_id>/bilan/
    Détails complets du bilan d'un élève: notes, remarques, annotations, appréciation.
    """
    permission_classes = [IsTeacherOrAdmin]

    def get(self, request, student_id):
        assignments = _get_teacher_assignments(request.user)
        
        student = get_object_or_404(Student, id=student_id)
        
        # Vérifier que l'élève est dans au moins une assignation du correcteur (sauf admin)
        from core.auth import UserRole
        is_admin = (
            request.user.is_superuser
            or request.user.groups.filter(name__iexact=UserRole.ADMIN).exists()
        )
        if not is_admin:
            if not _student_matches_assignments(student, assignments):
                return Response({
                    'detail': 'Vous n\'avez pas accès à cet élève.'
                }, status=status.HTTP_403_FORBIDDEN)
        
        # Récupérer toutes les copies de l'élève
        copies = Copy.objects.filter(student=student).select_related('exam')

        copies_data = []
        for copy in copies:
            # Score
            score_obj = Score.objects.filter(copy=copy).first()
            scores_data = {}
            total_score = None
            final_comment = ''
            if score_obj:
                scores_data = score_obj.scores_data or {}
                total_score = sum(
                    float(v) for v in scores_data.values()
                    if v is not None and v != ''
                ) if scores_data else None
                final_comment = score_obj.final_comment or ''

            # Build question_labels mapping from grading_structure
            question_labels = _build_question_labels(copy.exam) if copy.exam else {}

            # Remarques par question
            remarks = QuestionRemark.objects.filter(copy=copy)
            remarks_data = {r.question_id: r.remark for r in remarks}

            # Annotations
            annotations = Annotation.objects.filter(copy=copy)
            annotations_data = [{
                'id': str(a.id),
                'page_index': a.page_index,
                'content': a.content,
                'type': a.type,
                'x': a.x,
                'y': a.y,
                'w': a.w,
                'h': a.h,
            } for a in annotations]

            # Appréciation globale
            global_appreciation = copy.global_appreciation or ''

            # LLM Summary
            llm_summary = copy.llm_summary or ''

            # PDF URL
            pdf_url = f'/grading/copies/{copy.id}/final-pdf/' if copy.status == 'FINALIZED' else None

            copies_data.append({
                'copy_id': str(copy.id),
                'exam_name': copy.exam.name if copy.exam else 'N/A',
                'exam_id': str(copy.exam.id) if copy.exam else None,
                'status': copy.status,
                'anonymous_id': copy.anonymous_id,
                'total_score': round(total_score, 2) if total_score is not None else None,
                'scores_data': scores_data,
                'question_labels': question_labels,
                'final_comment': final_comment,
                'remarks': remarks_data,
                'annotations': annotations_data,
                'global_appreciation': global_appreciation,
                'llm_summary': llm_summary,
                'pdf_url': pdf_url,
            })
        
        return Response({
            'student': {
                'id': student.id,
                'first_name': student.first_name,
                'last_name': student.last_name,
                'class_name': student.class_name,
                'groupe': student.groupe,
                'email': student.email,
            },
            'copies': copies_data
        })
