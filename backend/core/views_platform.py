"""
Public platform statistics endpoint for the landing page.
Returns aggregated, non-sensitive data about the platform state.
"""
from django.db.models import Count
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from exams.models import Exam, Copy
from students.models import Student


class PlatformStatsView(APIView):
    """
    GET /api/platform-stats/
    Public endpoint — returns aggregated platform metrics for the landing page.
    Only non-sensitive totals are exposed (no corrector/annotation/activity data).
    """
    permission_classes = [AllowAny]

    def get(self, request):
        copies_qs = Copy.objects.all()
        copies_by_status = {
            row['status']: row['c']
            for row in copies_qs.values('status').annotate(c=Count('id'))
        }

        total_copies = sum(copies_by_status.values())
        finalized = copies_by_status.get(Copy.Status.FINALIZED, 0)

        total_exams = Exam.objects.count()
        exams_with_results = Exam.objects.filter(
            results_released_at__isnull=False
        ).count()

        students = Student.objects.count()

        # Exam types breakdown
        exam_types = list(
            Exam.objects.values('exam_type__name')
            .annotate(count=Count('id'))
            .order_by('-count')
        )

        return Response({
            'total_copies': total_copies,
            'copies_finalized': finalized,
            'finalization_rate': round(
                finalized / total_copies * 100, 1
            ) if total_copies > 0 else 0,
            'total_exams': total_exams,
            'exams_with_results': exams_with_results,
            'students_count': students,
            'exam_types': [
                {
                    'name': et['exam_type__name'] or 'Non classé',
                    'count': et['count'],
                }
                for et in exam_types
            ],
        })
