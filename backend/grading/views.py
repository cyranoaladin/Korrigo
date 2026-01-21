"""
Views pour l'app grading.
Tous les endpoints sont protégés par IsTeacherOrAdmin (staff only).
"""
import logging
from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.http import FileResponse

from exams.permissions import IsTeacherOrAdmin
from grading.models import Annotation
from grading.serializers import AnnotationSerializer
from grading.services import AnnotationService, GradingService
from exams.models import Copy

logger = logging.getLogger(__name__)


def _handle_service_error(e: Exception, context: str = "unknown") -> Response:
    """
    Convertit une exception métier en Response HTTP standardisée.
    - ValueError → 400 avec {"detail": "<message>"}
    - KeyError → 400 avec {"detail": "Missing required field: <field>"}
    - PermissionError → 403 avec {"detail": "<message>"}
    - Autre exception → relance (raise) pour traitement par _handle_unexpected_error
    """
    if isinstance(e, ValueError):
        logger.warning("Service error (%s): %s", context, str(e))
        return Response(
            {'detail': str(e)},
            status=status.HTTP_400_BAD_REQUEST
        )
    elif isinstance(e, KeyError):
        field = e.args[0] if e.args else str(e)
        logger.info("Missing field (%s): %s", context, field)
        return Response(
            {'detail': f'Missing required field: {field}'},
            status=status.HTTP_400_BAD_REQUEST
        )
    elif isinstance(e, PermissionError):
        logger.warning("Permission denied (%s): %s", context, str(e))
        return Response(
            {'detail': str(e)},
            status=status.HTTP_403_FORBIDDEN
        )
    else:
        # Ne gère pas les exceptions inattendues : relance
        raise


def _handle_unexpected_error(e: Exception, context: str = "unknown") -> Response:
    """
    Gère une exception inattendue (non métier).
    Log complet côté serveur + message générique au client.
    """
    logger.exception("Unexpected error (%s)", context)
    return Response(
        {'detail': 'Internal server error'},
        status=status.HTTP_500_INTERNAL_SERVER_ERROR
    )


class AnnotationListCreateView(generics.ListCreateAPIView):
    """
    GET  /api/copies/<copy_id>/annotations/ - Liste les annotations d'une copie
    POST /api/copies/<copy_id>/annotations/ - Crée une annotation (si READY)

    Permission : IsTeacherOrAdmin (staff only)
    """
    permission_classes = [IsTeacherOrAdmin]
    serializer_class = AnnotationSerializer

    def get_queryset(self):
        copy_id = self.kwargs['copy_id']
        copy = get_object_or_404(Copy, id=copy_id)
        return AnnotationService.list_annotations(copy)

    def create(self, request, *args, **kwargs):
        copy_id = self.kwargs['copy_id']
        copy = get_object_or_404(Copy, id=copy_id)

        try:
            annotation = AnnotationService.add_annotation(
                copy=copy,
                payload=request.data,
                user=request.user
            )
            serializer = self.get_serializer(annotation)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except (ValueError, KeyError, PermissionError) as e:
            return _handle_service_error(e, context="AnnotationListCreateView.create")
        except Exception as e:
            return _handle_unexpected_error(e, context="AnnotationListCreateView.create")


class AnnotationDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    GET    /api/annotations/<id>/ - Récupère une annotation
    PATCH  /api/annotations/<id>/ - Modifie une annotation (si READY)
    DELETE /api/annotations/<id>/ - Supprime une annotation (si READY)

    Permission : IsTeacherOrAdmin (staff only)
    """
    permission_classes = [IsTeacherOrAdmin]
    serializer_class = AnnotationSerializer
    queryset = Annotation.objects.all()

    def update(self, request, *args, **kwargs):
        annotation = self.get_object()
        partial = kwargs.pop('partial', True)  # PATCH par défaut

        try:
            updated = AnnotationService.update_annotation(
                annotation=annotation,
                payload=request.data,
                user=request.user
            )
            serializer = self.get_serializer(updated)
            return Response(serializer.data)
        except (ValueError, KeyError, PermissionError) as e:
            return _handle_service_error(e, context="AnnotationDetailView.update")
        except Exception as e:
            return _handle_unexpected_error(e, context="AnnotationDetailView.update")

    def destroy(self, request, *args, **kwargs):
        annotation = self.get_object()
        try:
            AnnotationService.delete_annotation(annotation, request.user)
            return Response(status=status.HTTP_204_NO_CONTENT)
        except (ValueError, KeyError, PermissionError) as e:
            return _handle_service_error(e, context="AnnotationDetailView.destroy")
        except Exception as e:
            return _handle_unexpected_error(e, context="AnnotationDetailView.destroy")


class CopyLockView(APIView):
    """
    POST /api/copies/<id>/lock/

    Verrouille une copie pour correction (READY → LOCKED).
    Permission : IsTeacherOrAdmin (staff only)
    """
    permission_classes = [IsTeacherOrAdmin]

    def post(self, request, id):
        copy = get_object_or_404(Copy, id=id)
        try:
            GradingService.lock_copy(copy, request.user)
            return Response(
                {
                    'message': 'Copy locked successfully',
                    'copy_id': str(copy.id),
                    'status': copy.status,
                    'locked_by': request.user.username
                },
                status=status.HTTP_200_OK
            )
        except (ValueError, KeyError, PermissionError) as e:
            return _handle_service_error(e, context="CopyLockView.post")
        except Exception as e:
            return _handle_unexpected_error(e, context="CopyLockView.post")


class CopyUnlockView(APIView):
    """
    POST /api/copies/<id>/unlock/

    Déverrouille une copie (LOCKED → READY).
    Permission : IsTeacherOrAdmin (staff only)
    """
    permission_classes = [IsTeacherOrAdmin]

    def post(self, request, id):
        copy = get_object_or_404(Copy, id=id)
        try:
            GradingService.unlock_copy(copy, request.user)
            return Response(
                {
                    'message': 'Copy unlocked successfully',
                    'copy_id': str(copy.id),
                    'status': copy.status
                },
                status=status.HTTP_200_OK
            )
        except (ValueError, KeyError, PermissionError) as e:
            return _handle_service_error(e, context="CopyUnlockView.post")
        except Exception as e:
            return _handle_unexpected_error(e, context="CopyUnlockView.post")


class CopyFinalizeView(APIView):
    """
    POST /api/copies/<id>/finalize/

    Finalise la correction d'une copie (LOCKED → GRADED).
    Génère le PDF final avec annotations.
    Permission : IsTeacherOrAdmin (staff only)
    """
    permission_classes = [IsTeacherOrAdmin]

    def post(self, request, id):
        copy = get_object_or_404(Copy, id=id)
        try:
            GradingService.finalize_copy(copy, request.user)

            # Calcul score final pour la réponse (protégé dans le try)
            final_score = GradingService.compute_score(copy)

            return Response(
                {
                    'message': 'Copy finalized successfully',
                    'copy_id': str(copy.id),
                    'status': copy.status,
                    'final_score': final_score,
                    'final_pdf': copy.final_pdf.url if copy.final_pdf else None
                },
                status=status.HTTP_200_OK
            )
        except (ValueError, KeyError, PermissionError) as e:
            return _handle_service_error(e, context="CopyFinalizeView.post")
        except Exception as e:
            return _handle_unexpected_error(e, context="CopyFinalizeView.post")


class CopyReadyView(APIView):
    """
    POST /api/copies/<id>/ready/

    Valide une copie et la rend prête à corriger (STAGING → READY).
    Permission : IsTeacherOrAdmin (staff only)
    """
    permission_classes = [IsTeacherOrAdmin]

    def post(self, request, id):
        copy = get_object_or_404(Copy, id=id)
        try:
            GradingService.ready_copy(copy, request.user)
            return Response(
                {
                    'message': 'Copy marked as ready successfully',
                    'copy_id': str(copy.id),
                    'status': copy.status
                },
                status=status.HTTP_200_OK
            )
        except (ValueError, KeyError, PermissionError) as e:
            return _handle_service_error(e, context="CopyReadyView.post")
        except Exception as e:
            return _handle_unexpected_error(e, context="CopyReadyView.post")


class CopyFinalPdfView(APIView):
    """
    GET /api/copies/<id>/final-pdf/

    Télécharge le PDF corrigé final.
    Permission : IsTeacherOrAdmin (staff only)
    """
    permission_classes = [IsTeacherOrAdmin]

    def get(self, request, id):
        copy = get_object_or_404(Copy, id=id)

        if not copy.final_pdf:
            return Response(
                {'detail': 'Final PDF not available for this copy'},
                status=status.HTTP_404_NOT_FOUND
            )

        try:
            # Open the file from Django storage (works with S3/local)
            pdf_file = copy.final_pdf.open('rb')
            response = FileResponse(pdf_file, content_type='application/pdf')
            response['Content-Disposition'] = f'attachment; filename="copy_{copy.id}_corrected.pdf"'
            return response
        except FileNotFoundError:
            logger.warning("Final PDF file not found for copy %s", copy.id)
            return Response(
                {'detail': 'Final PDF file not found on storage'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return _handle_unexpected_error(e, context="CopyFinalPdfView.get")
