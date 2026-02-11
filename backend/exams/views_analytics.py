"""
Analytics views for upload monitoring and statistics.
P8 FIX: Rewritten to use existing Exam/Copy/ExamPDF models instead of non-existent UploadMetrics.
"""
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.db.models import Count, Q
from django.utils import timezone
from datetime import timedelta
from core.auth import IsAdminOnly
from exams.models import Exam, Copy, ExamPDF


class UploadAnalyticsView(APIView):
    """
    Endpoint pour analytics des uploads.
    GET /api/exams/analytics/uploads/
    """
    permission_classes = [IsAdminOnly]
    
    def get(self, request):
        days = int(request.GET.get('days', 30))
        start_date = timezone.now() - timedelta(days=days)
        
        exams = Exam.objects.filter(created_at__gte=start_date) if hasattr(Exam, 'created_at') else Exam.objects.all()
        
        batch_count = exams.filter(upload_mode='BATCH_A3').count()
        individual_count = exams.filter(upload_mode='INDIVIDUAL_A4').count()
        total_count = batch_count + individual_count
        
        batch_ratio = (batch_count / total_count * 100) if total_count > 0 else 0
        individual_ratio = (individual_count / total_count * 100) if total_count > 0 else 0
        
        # Copy stats
        total_copies = Copy.objects.filter(exam__in=exams).count()
        ready_copies = Copy.objects.filter(exam__in=exams, status=Copy.Status.READY).count()
        graded_copies = Copy.objects.filter(exam__in=exams, status=Copy.Status.GRADED).count()
        
        response_data = {
            'period': {
                'days': days,
                'start_date': start_date.isoformat(),
                'end_date': timezone.now().isoformat()
            },
            'upload_type_distribution': {
                'BATCH_A3': {
                    'count': batch_count,
                    'percentage': round(batch_ratio, 2)
                },
                'INDIVIDUAL_A4': {
                    'count': individual_count,
                    'percentage': round(individual_ratio, 2)
                }
            },
            'global_metrics': {
                'total_exams': total_count,
                'total_copies': total_copies,
                'ready_copies': ready_copies,
                'graded_copies': graded_copies,
                'processed_exams': exams.filter(is_processed=True).count()
            },
        }
        
        return Response(response_data, status=status.HTTP_200_OK)


class StorageAnalyticsView(APIView):
    """
    Endpoint pour analytics du stockage.
    GET /api/exams/analytics/storage/
    """
    permission_classes = [IsAdminOnly]
    
    def get(self, request):
        batch_copies = Copy.objects.filter(
            exam__upload_mode='BATCH_A3',
            pdf_source__isnull=False
        ).count()
        
        individual_copies = Copy.objects.filter(
            exam__upload_mode='INDIVIDUAL_A4',
            pdf_source__isnull=False
        ).count()
        
        exam_pdfs_count = ExamPDF.objects.count()
        
        response_data = {
            'storage_by_mode': {
                'BATCH_A3': {
                    'copies_count': batch_copies,
                },
                'INDIVIDUAL_A4': {
                    'copies_count': individual_copies,
                    'exam_pdfs_count': exam_pdfs_count,
                }
            },
        }
        
        return Response(response_data, status=status.HTTP_200_OK)
