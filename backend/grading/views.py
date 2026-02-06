from rest_framework import generics, status
from rest_framework import renderers
from rest_framework.response import Response
from rest_framework.views import APIView
from django.http import FileResponse
from rest_framework.permissions import IsAuthenticated
from .models import Annotation, GradingEvent, QuestionRemark, QuestionScore
from exams.models import Copy
from .serializers import AnnotationSerializer, GradingEventSerializer, QuestionRemarkSerializer, QuestionScoreSerializer
from exams.permissions import IsTeacherOrAdmin
from .permissions import IsLockedByOwnerOrReadOnly
from django.shortcuts import get_object_or_404
from grading.services import AnnotationService, GradingService, LockConflictError
from core.auth import UserRole
import logging

logger = logging.getLogger(__name__)


def _get_lock_token(request):
    return request.META.get("HTTP_X_LOCK_TOKEN")

class PassthroughRenderer(renderers.BaseRenderer):
    """
    Renderer minimal pour forcer DRF à accepter application/pdf (évite 406 Not Acceptable).
    On ne sérialise rien : on laisse FileResponse fournir le flux binaire.
    """
    media_type = "application/pdf"
    format = "pdf"
    def render(self, data, accepted_media_type=None, renderer_context=None):
        return data



def _handle_service_error(e, context="API"):
    """
    Formate les erreurs du service layer (ValueError, PermissionError, etc.) en réponses HTTP.
    PermissionError -> 403 Forbidden
    Autres erreurs -> 400 Bad Request
    Always returns specific error messages for better debugging
    """
    logger.warning(f"{context} Service Error: {e}")
    
    if isinstance(e, PermissionError):
        return Response({"detail": str(e)}, status=status.HTTP_403_FORBIDDEN)
    
    # Always return specific error messages, not generic ones
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
    POST: Crée une annotation sur une copie (si READY et LOCK détenu).
    Permission: IsTeacherOrAdmin + IsLockedByOwnerOrReadOnly
    """
    permission_classes = [IsTeacherOrAdmin, IsLockedByOwnerOrReadOnly]
    serializer_class = AnnotationSerializer
    pagination_class = None  # Per-copy annotations, no pagination needed

    def get_queryset(self):
        copy_id = self.kwargs['copy_id']
        copy = get_object_or_404(Copy, id=copy_id)
        return AnnotationService.list_annotations(copy)

    def create(self, request, *args, **kwargs):
        copy_id = self.kwargs['copy_id']
        copy = get_object_or_404(Copy, id=copy_id)
        lock_token = _get_lock_token(request)
        
        try:
            annotation = AnnotationService.add_annotation(
                copy=copy,
                payload=request.data,
                user=request.user,
                lock_token=lock_token,
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
    PATCH  /api/annotations/<id>/ - Modifie une annotation (si LOCK détenu)
    DELETE /api/annotations/<id>/ - Supprime une annotation (si LOCK détenu)

    Permission : IsTeacherOrAdmin (staff only) + IsLockedByOwnerOrReadOnly
    """
    permission_classes = [IsTeacherOrAdmin, IsLockedByOwnerOrReadOnly]
    serializer_class = AnnotationSerializer
    queryset = Annotation.objects.all()

    def update(self, request, *args, **kwargs):
        annotation = self.get_object()
        lock_token = _get_lock_token(request)
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
                user=request.user,
                lock_token=lock_token,
            )
            serializer = self.get_serializer(updated)
            return Response(serializer.data)
        except (ValueError, KeyError, PermissionError) as e:
            return _handle_service_error(e, context="AnnotationDetailView.update")
        except Exception as e:
            return _handle_unexpected_error(e, context="AnnotationDetailView.update")

    def destroy(self, request, *args, **kwargs):
        annotation = self.get_object()
        lock_token = _get_lock_token(request)
        
        # Permission check: Teacher cannot delete others' annotations
        if not request.user.is_superuser and getattr(request.user, 'role', '') != 'Admin':
             if annotation.created_by != request.user:
                 return Response({"detail": "You do not have permission to delete this annotation."}, status=status.HTTP_403_FORBIDDEN)
        
        try:
            AnnotationService.delete_annotation(annotation, request.user, lock_token=lock_token)
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
        except (ValueError, PermissionError) as e:
            return _handle_service_error(e)

# CopyLockView and CopyUnlockView replaced by views_lock.py logic
# Keeping Ready and Finalize views here



class CopyFinalizeView(APIView):
    permission_classes = [IsTeacherOrAdmin]
    def post(self, request, id):
        copy = get_object_or_404(Copy, id=id)
        if copy.status == Copy.Status.GRADED:
            return Response({"detail": "Copy already graded."}, status=status.HTTP_400_BAD_REQUEST)
        lock_token = _get_lock_token(request)
        try:
            finalized = GradingService.finalize_copy(copy, request.user, lock_token=lock_token)
            return Response({"status": finalized.status})
        except LockConflictError as e:
            return Response({"detail": str(e)}, status=status.HTTP_409_CONFLICT)
        except (ValueError, PermissionError) as e:
            return _handle_service_error(e)


class CopyFinalPdfView(APIView):
    """
    GET /api/copies/<uuid>/final-pdf/
    
    Serves the final graded PDF for a copy.
    
    SECURITY JUSTIFICATION - AllowAny:
    ====================================
    This endpoint uses AllowAny permission class because it implements
    a DUAL authentication system:
    
    1. Teachers/Admins: Standard Django authentication (request.user)
    2. Students: Session-based authentication (request.session['student_id'])
    
    SECURITY GATES (enforced in view logic):
    -----------------------------------------
    Gate 1 - Status Check (line 179):
        - Only GRADED copies are accessible
        - Even admins cannot access non-GRADED copies
    
    Gate 2 - Permission Check (lines 186-215):
        - Teachers/Admins: Verified via is_staff/is_superuser/Teachers group
        - Students: Verified via session student_id + ownership check
        - Students can ONLY access THEIR OWN copies
        - 401 if no authentication
        - 403 if wrong student tries to access
    
    Audit Trail: All downloads are logged (line 222)
    
    Conformité: .antigravity/rules/01_security_rules.md § 2.2
    Référence Audit: P1 Security Review - 2026-01-24
    """
    from rest_framework.permissions import AllowAny
    permission_classes = [AllowAny]  # JUSTIFIED - See docstring security gates
    renderer_classes = [PassthroughRenderer]
    
    def get(self, request, id):
        copy = get_object_or_404(Copy, id=id)

        # ---- Status gate: Final PDF only available for GRADED copies ----
        # Even teachers/admins cannot access PDF for non-GRADED copies (403)
        if copy.status != Copy.Status.GRADED:
            return Response(
                {"detail": "Final PDF is only available when copy is GRADED."},
                status=status.HTTP_403_FORBIDDEN
            )

        # ---- Permission gate: teacher/admin OR owning student session ----
        teacher_or_admin = (
            getattr(request.user, "is_authenticated", False) and (
                getattr(request.user, "is_staff", False) or
                getattr(request.user, "is_superuser", False) or
                request.user.groups.filter(name=UserRole.TEACHER).exists()
            )
        )
        
        if not teacher_or_admin:
            student_id = request.session.get("student_id")
            if not student_id:
                return Response(
                    {"detail": "Authentication required."},
                    status=status.HTTP_401_UNAUTHORIZED
                )

            # Cast student_id (session can be str)
            try:
                sid = int(student_id)
            except Exception:
                return Response(
                    {"detail": "Invalid session."},
                    status=status.HTTP_401_UNAUTHORIZED
                )

            if not copy.student_id or copy.student_id != sid:
                return Response(
                    {"detail": "You do not have permission to view this copy."},
                    status=status.HTTP_403_FORBIDDEN
                )

        if not copy.final_pdf:
            return Response({"detail": "No final PDF available."}, status=status.HTTP_404_NOT_FOUND)

        # Audit trail: Téléchargement PDF final
        from core.utils.audit import log_data_access
        log_data_access(request, 'Copy', copy.id, action_detail='download')

        response = FileResponse(copy.final_pdf.open("rb"), content_type="application/pdf")
        filename = f'copy_{copy.anonymous_id}_corrected.pdf'
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        # Hardening Headers
        response["Cache-Control"] = "no-store, private"
        response["Pragma"] = "no-cache"
        response["X-Content-Type-Options"] = "nosniff"
        return response


class CopyAuditView(generics.ListAPIView):
    """
    GET /api/copies/<uuid>/audit/
    Retourne l'historique des actions (GradingEvents).
    """
    permission_classes = [IsTeacherOrAdmin]
    serializer_class = GradingEventSerializer
    pagination_class = None  # Per-copy audit log, no pagination needed

    def get_queryset(self):
        copy_id = self.kwargs['id']
        # Verify copy exists
        get_object_or_404(Copy, id=copy_id)
        return GradingEvent.objects.filter(copy_id=copy_id).select_related('actor').order_by('-timestamp')


class QuestionRemarkListCreateView(generics.ListCreateAPIView):
    """
    GET: Liste les remarques d'une copie.
    POST: Crée ou met à jour une remarque sur une question.
    """
    permission_classes = [IsTeacherOrAdmin]
    serializer_class = QuestionRemarkSerializer
    pagination_class = None  # Per-copy remarks are always small, no pagination needed

    def get_queryset(self):
        copy_id = self.kwargs['copy_id']
        copy = get_object_or_404(Copy, id=copy_id)
        return QuestionRemark.objects.filter(copy=copy).select_related('created_by').order_by('created_at')

    def create(self, request, *args, **kwargs):
        copy_id = self.kwargs['copy_id']
        copy = get_object_or_404(Copy, id=copy_id)
        question_id = request.data.get('question_id')
        remark = request.data.get('remark', '')

        if not question_id:
            return Response(
                {"detail": "question_id is required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Update or create
        obj, created = QuestionRemark.objects.update_or_create(
            copy=copy,
            question_id=question_id,
            defaults={
                'remark': remark,
                'created_by': request.user
            }
        )

        serializer = self.get_serializer(obj)
        return Response(
            serializer.data,
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK
        )


class QuestionRemarkDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    GET    /api/remarks/<id>/ - Récupère une remarque
    PATCH  /api/remarks/<id>/ - Modifie une remarque
    DELETE /api/remarks/<id>/ - Supprime une remarque
    """
    permission_classes = [IsTeacherOrAdmin]
    serializer_class = QuestionRemarkSerializer
    queryset = QuestionRemark.objects.all()

    def update(self, request, *args, **kwargs):
        remark_obj = self.get_object()

        # Permission check: only creator or admin can update
        if not request.user.is_superuser and getattr(request.user, 'role', '') != 'Admin':
            if remark_obj.created_by != request.user:
                return Response(
                    {"detail": "You do not have permission to edit this remark."},
                    status=status.HTTP_403_FORBIDDEN
                )

        partial = kwargs.pop('partial', False)
        serializer = self.get_serializer(remark_obj, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(serializer.data)

    def destroy(self, request, *args, **kwargs):
        remark_obj = self.get_object()

        # Permission check: only creator or admin can delete
        if not request.user.is_superuser and getattr(request.user, 'role', '') != 'Admin':
            if remark_obj.created_by != request.user:
                return Response(
                    {"detail": "You do not have permission to delete this remark."},
                    status=status.HTTP_403_FORBIDDEN
                )

        remark_obj.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class CopyGlobalAppreciationView(APIView):
    """
    GET/PUT/PATCH /api/copies/<uuid>/global-appreciation/
    Gère l'appréciation globale d'une copie.
    """
    permission_classes = [IsTeacherOrAdmin]

    def get(self, request, copy_id):
        copy = get_object_or_404(Copy, id=copy_id)
        return Response({
            'copy_id': str(copy.id),
            'global_appreciation': copy.global_appreciation or ''
        })

    def put(self, request, copy_id):
        return self._update(request, copy_id)

    def patch(self, request, copy_id):
        return self._update(request, copy_id)

    def _update(self, request, copy_id):
        copy = get_object_or_404(Copy, id=copy_id)
        global_appreciation = request.data.get('global_appreciation', '')
        
        copy.global_appreciation = global_appreciation
        copy.save(update_fields=['global_appreciation'])

        return Response({
            'copy_id': str(copy.id),
            'global_appreciation': copy.global_appreciation or ''
        })


class QuestionScoreListCreateView(generics.ListCreateAPIView):
    """
    GET: Liste les notes d'une copie.
    POST: Crée ou met à jour une note sur une question.
    """
    permission_classes = [IsTeacherOrAdmin]
    serializer_class = QuestionScoreSerializer
    pagination_class = None  # Per-copy scores are always small, no pagination needed

    def get_queryset(self):
        copy_id = self.kwargs['copy_id']
        copy = get_object_or_404(Copy, id=copy_id)
        return QuestionScore.objects.filter(copy=copy).select_related('created_by').order_by('created_at')

    def create(self, request, *args, **kwargs):
        copy_id = self.kwargs['copy_id']
        copy = get_object_or_404(Copy, id=copy_id)
        question_id = request.data.get('question_id')
        score = request.data.get('score')

        if not question_id:
            return Response(
                {"detail": "question_id is required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        if score is None:
            return Response(
                {"detail": "score is required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            score = float(score)
        except (ValueError, TypeError):
            return Response(
                {"detail": "score must be a number."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Update or create
        obj, created = QuestionScore.objects.update_or_create(
            copy=copy,
            question_id=question_id,
            defaults={
                'score': score,
                'created_by': request.user
            }
        )

        serializer = self.get_serializer(obj)
        return Response(
            serializer.data,
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK
        )
