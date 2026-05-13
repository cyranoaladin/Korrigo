"""
Views for Direction (Proviseur) dashboard
Simple endpoints that allow Direction users to view exam data
"""
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Count, Q

from .models import Exam

DIRECTION_GROUPS = ['direction_all', 'direction_lycee', 'direction_college']


def _get_exams_with_bilan():
    """Retourne les exam_id qui ont un BilanReport DONE."""
    try:
        from bilan.models import BilanReport
        return set(
            BilanReport.objects.filter(exam_id__isnull=False, status='DONE')
            .values_list('exam_id', flat=True)
        )
    except Exception:
        return set()


def _is_bac_blanc_exam(exam):
    exam_type = getattr(exam, 'exam_type', None)
    exam_type_code = getattr(exam_type, 'code', '') or ''
    exam_type_name = getattr(exam_type, 'name', '') or ''
    name = exam.name or ''
    return (
        exam_type_code == 'BAC_BLANC_MATHS_2026'
        or 'bac blanc' in exam_type_name.lower()
        or name in {'BB_J1', 'BB_J2'}
    )


def _is_test_exam(exam):
    name = (exam.name or '').lower()
    return 'test' in name or 'validation' in name or 'prod validation' in name


class IsDirectionUser:
    """Simple permission check for Direction users"""
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        return request.user.groups.filter(name__in=DIRECTION_GROUPS).exists()


class DirectionExamListView(APIView):
    """
    GET /api/direction/exams/
    Returns exam list for Direction users (proviseurs)
    """
    permission_classes = [IsAuthenticated, IsDirectionUser]
    
    def get(self, request):
        exams = Exam.objects.all().select_related('exam_type').order_by('-date').annotate(
            copies_count=Count('copies'),
            ready_count=Count('copies', filter=Q(copies__status='READY')),
            in_progress_count=Count('copies', filter=Q(copies__status='IN_PROGRESS')),
            finalized_count=Count('copies', filter=Q(copies__status='FINALIZED')),
        )

        bilan_exam_ids = _get_exams_with_bilan()

        data = []
        for exam in exams:
            if _is_test_exam(exam):
                continue
            data.append({
                'id': str(exam.id),
                'name': exam.name,
                'date': exam.date.isoformat() if exam.date else None,
                'upload_mode': exam.upload_mode,
                'exam_type': exam.exam_type.name if exam.exam_type else None,
                'copies_count': exam.copies_count,
                'ready_count': exam.ready_count,
                'in_progress_count': exam.in_progress_count,
                'finalized_count': exam.finalized_count,
                'has_bilan': exam.id in bilan_exam_ids or _is_bac_blanc_exam(exam),
            })
        
        return Response(data)
