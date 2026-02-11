"""
Analytics views for upload monitoring and statistics.
"""
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.db.models import Count, Sum, Avg, Q
from django.utils import timezone
from datetime import timedelta
from core.permissions import IsAdminOnly
from exams.models import UploadMetrics, Exam


class UploadAnalyticsView(APIView):
    """
    Endpoint pour analytics des uploads.
    GET /api/exams/analytics/uploads/
    
    Returns:
    - Ratios BATCH_A3 vs INDIVIDUAL_A4
    - Taux de succès par mode
    - Volumes uploadés
    - Performance metrics
    """
    permission_classes = [IsAdminOnly]
    
    def get(self, request):
        # Période d'analyse (paramètres optionnels)
        days = int(request.GET.get('days', 30))
        start_date = timezone.now() - timedelta(days=days)
        
        # Récupérer les métriques de la période
        metrics = UploadMetrics.objects.filter(uploaded_at__gte=start_date)
        
        # 1. Ratios par type d'upload
        upload_type_stats = metrics.values('upload_type').annotate(
            count=Count('id'),
            total_files=Sum('total_files'),
            successful_files=Sum('successful_files'),
            failed_files=Sum('failed_files'),
            total_size=Sum('total_size_bytes'),
            avg_duration=Avg('duration_seconds')
        )
        
        # 2. Statistiques par statut
        status_stats = metrics.values('upload_status').annotate(
            count=Count('id')
        )
        
        # 3. Tendances quotidiennes (7 derniers jours)
        last_7_days = timezone.now() - timedelta(days=7)
        daily_stats = metrics.filter(uploaded_at__gte=last_7_days).extra(
            select={'day': 'DATE(uploaded_at)'}
        ).values('day').annotate(
            uploads=Count('id'),
            total_files=Sum('total_files'),
            successful_files=Sum('successful_files')
        ).order_by('day')
        
        # 4. Métriques globales
        total_metrics = metrics.aggregate(
            total_uploads=Count('id'),
            total_files_uploaded=Sum('total_files'),
            total_successful=Sum('successful_files'),
            total_failed=Sum('failed_files'),
            total_data_uploaded_gb=Sum('total_size_bytes') / (1024**3) if metrics.exists() else 0,
            avg_upload_time=Avg('duration_seconds')
        )
        
        # 5. Top utilisateurs
        top_users = metrics.values(
            'uploaded_by__username'
        ).annotate(
            uploads=Count('id'),
            total_files=Sum('total_files')
        ).order_by('-uploads')[:5]
        
        # 6. Calcul du taux de succès global
        if total_metrics['total_files_uploaded']:
            success_rate = (
                total_metrics['total_successful'] / total_metrics['total_files_uploaded']
            ) * 100
        else:
            success_rate = 0
        
        # 7. Comparaison BATCH_A3 vs INDIVIDUAL_A4
        batch_count = metrics.filter(upload_type='BATCH_A3').count()
        individual_count = metrics.filter(upload_type='INDIVIDUAL_A4').count()
        total_count = batch_count + individual_count
        
        batch_ratio = (batch_count / total_count * 100) if total_count > 0 else 0
        individual_ratio = (individual_count / total_count * 100) if total_count > 0 else 0
        
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
            'upload_type_stats': list(upload_type_stats),
            'status_distribution': list(status_stats),
            'daily_trends': list(daily_stats),
            'global_metrics': {
                **total_metrics,
                'success_rate': round(success_rate, 2),
                'total_data_uploaded_gb': round(total_metrics['total_data_uploaded_gb'], 2) if total_metrics['total_data_uploaded_gb'] else 0
            },
            'top_users': list(top_users),
        }
        
        return Response(response_data, status=status.HTTP_200_OK)


class StorageAnalyticsView(APIView):
    """
    Endpoint pour analytics du stockage.
    GET /api/exams/analytics/storage/
    
    Returns:
    - Utilisation du stockage par mode
    - Économies réalisées grâce à la déduplication
    - Projections
    """
    permission_classes = [IsAdminOnly]
    
    def get(self, request):
        from exams.models import ExamPDF, Copy
        
        # Calcul de l'utilisation du stockage
        # BATCH_A3: Les copies ont leur propre pdf_source
        batch_copies = Copy.objects.filter(
            exam__upload_mode='BATCH_A3',
            pdf_source__isnull=False
        )
        
        # INDIVIDUAL_A4: Les copies référencent ExamPDF (pas de duplication)
        individual_copies = Copy.objects.filter(
            exam__upload_mode='INDIVIDUAL_A4',
            source_exam_pdf__isnull=False
        )
        
        # Nombre de fichiers ExamPDF
        exam_pdfs_count = ExamPDF.objects.count()
        
        # Estimation de l'espace économisé
        # Avant optimisation: chaque copie INDIVIDUAL_A4 aurait eu son propre fichier
        # Après: un seul fichier ExamPDF partagé
        estimated_savings = individual_copies.count()  # Nombre de fichiers dupliqués évités
        
        # Métriques récentes de taille (des 30 derniers jours)
        recent_metrics = UploadMetrics.objects.filter(
            uploaded_at__gte=timezone.now() - timedelta(days=30)
        ).aggregate(
            batch_storage=Sum('total_size_bytes', filter=Q(upload_type='BATCH_A3')),
            individual_storage=Sum('total_size_bytes', filter=Q(upload_type='INDIVIDUAL_A4'))
        )
        
        response_data = {
            'storage_by_mode': {
                'BATCH_A3': {
                    'copies_count': batch_copies.count(),
                    'estimated_storage_gb': round((recent_metrics['batch_storage'] or 0) / (1024**3), 2)
                },
                'INDIVIDUAL_A4': {
                    'copies_count': individual_copies.count(),
                    'exam_pdfs_count': exam_pdfs_count,
                    'estimated_storage_gb': round((recent_metrics['individual_storage'] or 0) / (1024**3), 2),
                    'deduplication': {
                        'files_saved': estimated_savings,
                        'description': f'{estimated_savings} fichiers dupliqués évités grâce à la référence ExamPDF'
                    }
                }
            },
            'total_storage_saved_percentage': round(
                (estimated_savings / (individual_copies.count() + estimated_savings) * 100)
                if (individual_copies.count() + estimated_savings) > 0 else 0, 2
            )
        }
        
        return Response(response_data, status=status.HTTP_200_OK)
