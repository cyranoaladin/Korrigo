"""
API Views for DNB Bilan Generation and Consultation
"""

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.http import HttpResponse

import logging

from .permissions import IsAdminOrTeacher
from .services.orchestrator import BilanOrchestrator
from .services.eam_orchestrator import EamBilanOrchestrator
from .models import BilanReport

logger = logging.getLogger(__name__)


@api_view(['POST'])
@permission_classes([IsAuthenticated, IsAdminOrTeacher])
def generate_bilan(request):
    """
    Génère un bilan pédagogique.

    POST /api/bilan/generate/
    { "exam_slug": "DNB_2026" | "EAM BLANCHE 2026", "force": false }
    """
    try:
        def _as_bool(val) -> bool:
            if isinstance(val, bool):
                return val
            if val is None:
                return False
            if isinstance(val, (int, float)):
                return bool(val)
            if isinstance(val, str):
                return val.strip().lower() in {"1", "true", "yes", "y", "on"}
            return bool(val)

        # Backward/Frontend compatibility: accept either exam_slug or exam_type.
        exam_slug = request.data.get('exam_slug') or request.data.get('exam_type') or 'DNB_2026'
        force = _as_bool(request.data.get('force') if 'force' in request.data else request.query_params.get('force'))

        existing = BilanReport.objects.filter(
            exam_type=exam_slug,
            status='DONE'
        ).order_by('-generated_at').first()

        if existing and not force:
            return Response({
                'message': 'Un bilan existe déjà pour cet examen',
                'report_id': existing.id,
                'generated_at': existing.generated_at,
                'status': 'ALREADY_EXISTS'
            }, status=status.HTTP_200_OK)

        report = BilanReport.objects.create(
            exam_type=exam_slug,
            scope='ETABLISSEMENT',
            generated_by=request.user,
            status='GENERATING'
        )

        # Use EamBilanOrchestrator for EAM exams, BilanOrchestrator for others
        if 'EAM BLANCHE' in exam_slug:
            orchestrator = EamBilanOrchestrator(exam_slug)
        else:
            orchestrator = BilanOrchestrator(exam_slug)

        try:
            if isinstance(orchestrator, EamBilanOrchestrator):
                generated = orchestrator.generate()
            else:
                generated = orchestrator.generate(request.user)

            report.status = 'DONE'
            report.json_data = generated
            report.llm_model = generated.get("llm_model", "")
            report.rag_collection = generated.get("rag_collection", "")
            report.exam = orchestrator.engine.exam
            report.save()

            return Response({
                'message': 'Bilan généré avec succès',
                'report_id': report.id,
                'generated_at': report.generated_at,
                'status': 'SUCCESS'
            }, status=status.HTTP_201_CREATED)

        except Exception as e:
            logger.exception("generate_bilan orchestration error for report %s", report.id)
            report.status = 'ERROR'
            report.save()
            return Response({
                'message': 'Une erreur s\'est produite pendant la génération du bilan.',
                'report_id': report.id,
                'status': 'ERROR'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    except Exception as e:
        logger.exception("generate_bilan internal error")
        return Response({
            'message': 'Une erreur interne s\'est produite. Veuillez réessayer.',
            'status': 'ERROR'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated, IsAdminOrTeacher])
def list_bilans(request):
    """
    Liste tous les bilans disponibles.

    GET /api/bilan/
    """
    try:
        # List all bilans (DONE/GENERATING/ERROR) so users can track progress/errors.
        bilans = BilanReport.objects.all().order_by('-generated_at')

        data = []
        for bilan in bilans:
            data.append({
                'id': bilan.id,
                'exam_type': bilan.exam_type,
                'scope': bilan.scope,
                'status': bilan.status,
                'generated_at': bilan.generated_at,
                'generated_by': (
                    bilan.generated_by.get_full_name() or bilan.generated_by.username
                    if bilan.generated_by else ''
                ),
                'n_copies': bilan.json_data.get('metadata', {}).get('n_copies', 0) if bilan.json_data else 0,
                'llm_model': bilan.llm_model,
                'rag_collection': bilan.rag_collection,
                'generation_time_seconds': bilan.generation_time.total_seconds() if bilan.generation_time else 0,
                'pdf_available': bool(bilan.pdf_file),
            })

        return Response({
            'bilans': data,
            'count': len(data)
        }, status=status.HTTP_200_OK)

    except Exception as e:
        logger.exception("list_bilans internal error")
        return Response({
            'message': 'Une erreur interne s\'est produite. Veuillez réessayer.',
            'status': 'ERROR'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET', 'DELETE'])
@permission_classes([IsAuthenticated, IsAdminOrTeacher])
def bilan_detail(request, pk):
    """
    GET  /api/bilan/{pk}/  — Récupère un bilan.
    DELETE /api/bilan/{pk}/  — Supprime un bilan (admin uniquement).
    """
    report = get_object_or_404(BilanReport, pk=pk)

    if request.method == 'DELETE':
        if not request.user.is_staff and not request.user.groups.filter(name='admin').exists():
            return Response({
                'message': 'Seuls les administrateurs peuvent supprimer des bilans',
                'status': 'PERMISSION_DENIED'
            }, status=status.HTTP_403_FORBIDDEN)

        if report.pdf_file:
            report.pdf_file.delete()
        report.delete()

        return Response({
            'message': 'Bilan supprimé avec succès',
            'status': 'SUCCESS'
        }, status=status.HTTP_200_OK)

    # GET
    try:
        if not report.can_view(request.user):
            return Response({
                'message': "Vous n'avez pas la permission de voir ce bilan",
                'status': 'PERMISSION_DENIED'
            }, status=status.HTTP_403_FORBIDDEN)

        data = report.json_data.copy() if report.json_data else {}

        # Section 5 (inter-correcteurs) : admin uniquement
        if not request.user.is_staff and not request.user.groups.filter(name='admin').exists():
            data.pop('s5_correctors', None)

        return Response({
            'report': {
                'id': report.id,
                'exam_type': report.exam_type,
                'scope': report.scope,
                'generated_at': report.generated_at,
                'generated_by': report.generated_by.get_full_name() or report.generated_by.username if report.generated_by else '',
                'status': report.status,
                'llm_model': report.llm_model,
                'rag_collection': report.rag_collection,
                'generation_time_seconds': report.generation_time.total_seconds() if report.generation_time else 0,
                'pdf_available': bool(report.pdf_file),
            },
            'data': data
        }, status=status.HTTP_200_OK)

    except Exception as e:
        logger.exception("bilan_detail internal error for pk=%s", pk)
        return Response({
            'message': 'Une erreur interne s\'est produite. Veuillez réessayer.',
            'status': 'ERROR'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated, IsAdminOrTeacher])
def download_bilan_pdf(request, pk):
    """
    Télécharge le PDF d'un bilan.

    GET /api/bilan/{pk}/pdf/
    """
    try:
        report = get_object_or_404(BilanReport, pk=pk)

        if not report.can_view(request.user):
            return Response({
                'message': "Vous n'avez pas la permission de voir ce bilan",
                'status': 'PERMISSION_DENIED'
            }, status=status.HTTP_403_FORBIDDEN)

        if not report.pdf_file:
            return Response({
                'message': 'PDF non disponible pour ce bilan',
                'status': 'PDF_NOT_AVAILABLE'
            }, status=status.HTTP_404_NOT_FOUND)

        response = HttpResponse(report.pdf_file.read(), content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="bilan_{report.exam_type}_{report.id}.pdf"'
        return response

    except Exception as e:
        return Response({
            'message': f'Erreur serveur: {str(e)}',
            'status': 'ERROR'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated, IsAdminOrTeacher])
def bilan_stats(request):
    """
    Statistiques système sur les bilans.

    GET /api/bilan/stats/
    """
    try:
        total_bilans = BilanReport.objects.filter(status='DONE').count()
        latest_bilan = BilanReport.objects.filter(status='DONE').order_by('-generated_at').first()

        return Response({
            'total_bilans': total_bilans,
            'latest_bilan': {
                'id': latest_bilan.id,
                'exam_type': latest_bilan.exam_type,
                'generated_at': latest_bilan.generated_at,
                'n_copies': latest_bilan.json_data.get('metadata', {}).get('n_copies', 0) if latest_bilan.json_data else 0,
            } if latest_bilan else None,
            'rag_collection_status': 'ACTIVE',
            'llm_status': 'ACTIVE',
        }, status=status.HTTP_200_OK)

    except Exception as e:
        return Response({
            'message': f'Erreur serveur: {str(e)}',
            'status': 'ERROR'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
