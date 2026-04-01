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
from exams.models import Copy, TeacherGroupAssignment
from grading.models import Score, Annotation, QuestionRemark


def _get_teacher_group(user):
    """Récupère le groupe assigné à un correcteur depuis la DB."""
    assignment = TeacherGroupAssignment.objects.filter(teacher=user).first()
    return assignment.group_name if assignment else None


class MyStudentsListView(views.APIView):
    """
    GET /api/grading/my-students/
    Liste les élèves du groupe du correcteur connecté avec leurs notes.
    """
    permission_classes = [IsTeacherOrAdmin]

    def get(self, request):
        groupe = _get_teacher_group(request.user)
        
        if not groupe:
            return Response({
                'detail': 'Aucun groupe associé à ce correcteur.',
                'students': []
            }, status=status.HTTP_200_OK)
        
        # Récupérer les élèves du groupe avec prefetch pour éviter N+1 queries
        students = Student.objects.filter(groupe=groupe).order_by('last_name', 'first_name').prefetch_related(
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
                # Utiliser les scores prefetchés
                score_obj = copy.scores.first() if hasattr(copy, '_prefetched_objects_cache') else Score.objects.filter(copy=copy).first()
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
        
        return Response({
            'groupe': groupe,
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
        groupe = _get_teacher_group(request.user)
        
        student = get_object_or_404(Student, id=student_id)
        
        # Vérifier que l'élève est dans le groupe du correcteur (sauf admin)
        from core.auth import UserRole
        is_admin = (
            request.user.is_superuser
            or request.user.groups.filter(name__iexact=UserRole.ADMIN).exists()
        )
        if not is_admin:
            if student.groupe != groupe:
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
