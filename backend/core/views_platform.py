"""
Public platform statistics endpoint for the landing page.
Returns aggregated, non-sensitive data about the platform state.
"""
from django.contrib.auth import get_user_model
from django.db.models import Count, Q, Max
from django.utils import timezone
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from exams.models import Exam, Copy
from grading.models import Annotation, GradingEvent
from students.models import Student
from core.auth import UserRole

User = get_user_model()


class PlatformStatsView(APIView):
    """
    GET /api/platform-stats/
    Public endpoint — returns aggregated platform metrics for the landing page.
    No sensitive data is exposed.
    """
    permission_classes = [AllowAny]

    def get(self, request):
        copies_qs = Copy.objects.all()
        copies_by_status = {
            row['status']: row['c']
            for row in copies_qs.values('status').annotate(c=Count('id'))
        }

        total_copies = sum(copies_by_status.values())
        ready = copies_by_status.get(Copy.Status.READY, 0)
        in_progress = copies_by_status.get(Copy.Status.IN_PROGRESS, 0)
        finalized = copies_by_status.get(Copy.Status.FINALIZED, 0)

        total_exams = Exam.objects.count()
        exams_with_results = Exam.objects.filter(
            results_released_at__isnull=False
        ).count()

        correctors = User.objects.filter(
            groups__name__iexact=UserRole.TEACHER
        ).distinct().count()

        students = Student.objects.count()

        annotations = Annotation.objects.count()

        # Latest activity timestamp
        latest_event = GradingEvent.objects.aggregate(
            last=Max('created_at')
        )['last']

        # Exam types breakdown
        exam_types = list(
            Exam.objects.values('exam_type__name')
            .annotate(count=Count('id'))
            .order_by('-count')
        )

        return Response({
            'total_copies': total_copies,
            'copies_ready': ready,
            'copies_in_progress': in_progress,
            'copies_finalized': finalized,
            'finalization_rate': round(
                finalized / total_copies * 100, 1
            ) if total_copies > 0 else 0,
            'total_exams': total_exams,
            'exams_with_results': exams_with_results,
            'correctors_count': correctors,
            'students_count': students,
            'annotations_count': annotations,
            'last_activity': latest_event.isoformat() if latest_event else None,
            'exam_types': [
                {
                    'name': et['exam_type__name'] or 'Non classé',
                    'count': et['count'],
                }
                for et in exam_types
            ],
        })
