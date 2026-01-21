from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from .models import Annotation, GradingEvent
from exams.models import Copy
from .serializers import AnnotationSerializer, GradingEventSerializer
from exams.permissions import IsTeacherOrAdmin
from django.shortcuts import get_object_or_404
from grading.services import GradingService, AnnotationService
import logging

logger = logging.getLogger(__name__)


def _handle_service_error(e, context="API"):
    """
    Formate les erreurs du service layer (ValueError, etc.) en réponses HTTP 400.
    """
    logger.warning(f"{context} Service Error: {e}")
    return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

def _handle_unexpected_error(e, context="API"):
    """
    Formate les erreurs inattendues en réponses HTTP 500 et log.
    """
    logger.error(f"{context} Unexpected Error: {e}", exc_info=True)
    return Response(
        {"detail": "An unexpected error occurred. Please contact support."},
        status=status.HTTP_500_INTERNAL_SERVER_ERROR
    )


class AnnotationListCreateView(generics.ListCreateAPIView):
    """
    GET: Liste les annotations d'une copie.
    POST: Crée une annotation sur une copie (si READY).
    Permission: IsTeacherOrAdmin
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
        except (ValueError, KeyError) as e:
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
        # Not using kwargs.pop('partial') because we pass payload directly
        
        # Check permissions logic (Owner or Admin for non-admins)?
        # For P0.2: Teacher ne peut pas DELETE annotation d’un autre.
        # But here we are in update.
        if not request.user.is_superuser and getattr(request.user, 'role', '') != 'Admin':
             if annotation.created_by != request.user:
                 return Response({"detail": "You do not have permission to edit this annotation."}, status=status.HTTP_403_FORBIDDEN)

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
        
        # Permission check: Teacher cannot delete others' annotations
        if not request.user.is_superuser and getattr(request.user, 'role', '') != 'Admin':
             if annotation.created_by != request.user:
                 return Response({"detail": "You do not have permission to delete this annotation."}, status=status.HTTP_403_FORBIDDEN)
        
        try:
            AnnotationService.delete_annotation(annotation, request.user)
            # 204 No Content is standard
            return Response(status=status.HTTP_204_NO_CONTENT)
        except (ValueError, KeyError, PermissionError) as e:
            return _handle_service_error(e, context="AnnotationDetailView.destroy")
        except Exception as e:
            return _handle_unexpected_error(e, context="AnnotationDetailView.destroy")


class CopyReadyView(APIView):
    permission_classes = [IsTeacherOrAdmin]
    def post(self, request, id):
        copy = get_object_or_404(Copy, id=id)
        try:
            GradingService.ready_copy(copy, request.user)
            return Response({"status": copy.status})
        except ValueError as e:
            return _handle_service_error(e)

class CopyLockView(APIView):
    permission_classes = [IsTeacherOrAdmin]
    def post(self, request, id):
        copy = get_object_or_404(Copy, id=id)
        # Check if already locked by someone else?
        # Service handles status check. Assuming concurrent locking is rare or last-write-wins is acceptable for MVP.
        # Ideally check if locked_by is None.
        try:
            GradingService.lock_copy(copy, request.user)
            return Response({"status": copy.status})
        except ValueError as e:
            return _handle_service_error(e)

class CopyUnlockView(APIView):
    permission_classes = [IsTeacherOrAdmin]
    def post(self, request, id):
        copy = get_object_or_404(Copy, id=id)
        # Check permissions: Can only unlock if you locked it OR you are admin?
        # P0.2 Requirement: "Teacher ne peut pas unlock si non autorisé."
        # If I locked it, I can unlock it. If I'm admin, I can unlock anyone.
        if not request.user.is_superuser and getattr(request.user, 'role', '') != 'Admin':
             if copy.locked_by and copy.locked_by != request.user:
                 return Response({"detail": "Locked by another user."}, status=status.HTTP_403_FORBIDDEN)
                 
        try:
            GradingService.unlock_copy(copy, request.user)
            return Response({"status": copy.status})
        except ValueError as e:
            return _handle_service_error(e)

class CopyFinalizeView(APIView):
    permission_classes = [IsTeacherOrAdmin]
    def post(self, request, id):
        copy = get_object_or_404(Copy, id=id)
        try:
            GradingService.finalize_copy(copy, request.user)
            return Response({"status": copy.status})
        except ValueError as e:
            return _handle_service_error(e)


class CopyFinalPdfView(APIView):
    permission_classes = [IsTeacherOrAdmin]
    
    def get(self, request, id):
        copy = get_object_or_404(Copy, id=id)

        # SECURITY: Ensure copy is GRADED or user is Admin
        if copy.status != Copy.Status.GRADED:
             # Check if Admin (assuming 'role' field or is_superuser)
             is_admin = request.user.is_superuser or getattr(request.user, 'role', '') == 'Admin'
             if not is_admin:
                 return Response(
                     {'detail': 'Final PDF is only available when copy is GRADED.'},
                     status=status.HTTP_403_FORBIDDEN
                 )
        if not copy.final_pdf:
            return Response({"detail": "No final PDF available."}, status=status.HTTP_404_NOT_FOUND)
            
        from django.http import FileResponse
        response = FileResponse(copy.final_pdf.open('rb'), content_type='application/pdf')
        filename = f"copy_{copy.anonymous_id}_corrected.pdf"
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response


class CopyAuditView(generics.ListAPIView):
    """
    GET /api/copies/<uuid>/audit/
    Retourne l'historique des actions (GradingEvents).
    """
    permission_classes = [IsTeacherOrAdmin]
    serializer_class = GradingEventSerializer

    def get_queryset(self):
        copy_id = self.kwargs['id']
        # Verify copy exists
        get_object_or_404(Copy, id=copy_id)
        return GradingEvent.objects.filter(copy_id=copy_id).select_related('actor').order_by('-timestamp')
