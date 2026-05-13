from rest_framework import generics, status
from rest_framework import renderers
from rest_framework.response import Response
from rest_framework.views import APIView
from django.http import HttpResponse
from rest_framework.permissions import IsAuthenticated
from .models import Annotation, CopyLock, GradingEvent, QuestionRemark, Score
from exams.models import Copy, Exam
from .serializers import AnnotationSerializer, GradingEventSerializer, QuestionRemarkSerializer
from exams.permissions import IsTeacherOrAdmin
from typing import cast as _cast
from django.shortcuts import get_object_or_404
from grading.services import AnnotationService, GradingService, LockConflictError
from core.utils.audit import log_audit
from core.auth import UserRole, IsKorrigoAdmin
from django.db.models import Count
import statistics
import json
import logging
from io import BytesIO
from zipfile import ZipFile, ZIP_DEFLATED
from exams.score_constraints import Q_MAX_BY_EXAM

logger = logging.getLogger(__name__)


def _trunc(s: str, n: int = 300) -> str:
    """Truncate a string to n characters (Pyre2-safe alternative to s[:n])."""
    return s[:n]  # type: ignore[return-value]


class PassthroughRenderer(renderers.BaseRenderer):
    """
    Renderer minimal pour forcer DRF à accepter application/pdf (évite 406 Not Acceptable).
    On ne sérialise rien : on laisse FileResponse fournir le flux binaire.
    """
    media_type = "application/pdf"
    format = "pdf"
    def render(self, data, accepted_media_type=None, renderer_context=None):
        return data


class ZipPassthroughRenderer(renderers.BaseRenderer):
    media_type = "application/zip"
    format = "zip"

    def render(self, data, accepted_media_type=None, renderer_context=None):
        return data



def _can_write_copy(user, copy: Copy) -> bool:
    """
    LOT 5: Check if user is allowed to write to this copy.
    Admins/superusers always pass. Teachers must be the assigned_corrector.
    """
    if user.is_superuser:
        return True
    if user.groups.filter(name__iexact=UserRole.ADMIN).exists():
        return True
    return copy.assigned_corrector_id == user.id


def _can_read_copy_scores(user, copy: Copy) -> bool:
    """
    P0.1: Check if user is allowed to READ the scores of a copy.
    Only admins/superusers and the assigned corrector may access raw scores.
    Students and unrelated teachers are denied.
    """
    if user.is_superuser:
        return True
    if user.groups.filter(name__iexact=UserRole.ADMIN).exists():
        return True
    # Teacher must be the assigned corrector for this copy
    if user.groups.filter(name__iexact=UserRole.TEACHER).exists():
        return copy.assigned_corrector_id == user.id
    return False


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
        {"detail": "Une erreur inattendue s'est produite. Veuillez contacter le support."},
        status=status.HTTP_500_INTERNAL_SERVER_ERROR
    )


def _serialize_copy_export(copy: Copy, include_student_id: bool = False) -> dict[str, object]:
    score = copy.scores.order_by('-updated_at').first()
    remarks = copy.question_remarks.order_by('question_id', 'created_at')
    annotations = copy.annotations.order_by('page_index', 'created_at')

    payload = {
        'copy_id': str(copy.id),
        'anonymous_id': copy.anonymous_id,
        'status': copy.status,
        'assigned_corrector_id': copy.assigned_corrector_id,
        'scores': score.scores_data if score else {},
        'scores_data': score.scores_data if score else {},
        'score_record_id': str(score.id) if score else None,
        'score_final_comment': score.final_comment if score else '',
        'final_comment': score.final_comment if score else '',
        'remarks': [
            {
                'id': str(remark.id),
                'question_id': remark.question_id,
                'remark': remark.remark,
                'created_by_id': remark.created_by_id,
                'created_at': remark.created_at.isoformat(),
                'updated_at': remark.updated_at.isoformat(),
            }
            for remark in remarks
        ],
        'global_appreciation': copy.global_appreciation or '',
        'annotations': [
            {
                'id': str(annotation.id),
                'page_index': annotation.page_index,
                'x': annotation.x,
                'y': annotation.y,
                'w': annotation.w,
                'h': annotation.h,
                'content': annotation.content,
                'type': annotation.type,
                'score_delta': annotation.score_delta,
                'created_by_id': annotation.created_by_id,
                'created_at': annotation.created_at.isoformat(),
                'updated_at': annotation.updated_at.isoformat(),
                'version': annotation.version,
            }
            for annotation in annotations
        ],
    }
    if include_student_id:
        payload['student_id'] = copy.student_id
    return payload


class AnnotationListCreateView(generics.ListCreateAPIView):
    """
    GET: Liste les annotations d'une copie.
    POST: Crée une annotation sur une copie READY.
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

        # LOT 5: Only assigned corrector or admin can create annotations
        if not _can_write_copy(request.user, copy):
            return Response({"detail": "Seul le correcteur assigné peut annoter cette copie."}, status=status.HTTP_403_FORBIDDEN)
        
        try:
            annotation = AnnotationService.add_annotation(
                copy=copy,
                payload=request.data,
                user=request.user,
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

    Permission : IsTeacherOrAdmin (staff only)
    """
    permission_classes = [IsTeacherOrAdmin]
    serializer_class = AnnotationSerializer
    queryset = Annotation.objects.all()

    def update(self, request, *args, **kwargs):
        annotation = self.get_object()
        
        # LOT 5 fix: use _can_write_copy for consistent permission check
        if not _can_write_copy(request.user, annotation.copy):
            return Response({"detail": "Seul le correcteur assigné ou un admin peut modifier cette annotation."}, status=status.HTTP_403_FORBIDDEN)

        try:
            updated = AnnotationService.update_annotation(
                annotation=annotation,
                payload=request.data,
                user=request.user,
            )
            serializer = self.get_serializer(updated)
            return Response(serializer.data)
        except (ValueError, KeyError, PermissionError) as e:
            return _handle_service_error(e, context="AnnotationDetailView.update")
        except Exception as e:
            return _handle_unexpected_error(e, context="AnnotationDetailView.update")

    def destroy(self, request, *args, **kwargs):
        annotation = self.get_object()
        
        # LOT 5 fix: use _can_write_copy for consistent permission check
        if not _can_write_copy(request.user, annotation.copy):
            return Response({"detail": "Seul le correcteur assigné ou un admin peut supprimer cette annotation."}, status=status.HTTP_403_FORBIDDEN)
        
        try:
            AnnotationService.delete_annotation(annotation, request.user)
            return Response(status=status.HTTP_204_NO_CONTENT)
        except (ValueError, KeyError, PermissionError) as e:
            return _handle_service_error(e, context="AnnotationDetailView.destroy")
        except Exception as e:
            return _handle_unexpected_error(e, context="AnnotationDetailView.destroy")


class AnnotationHistoryView(APIView):
    """
    GET /api/grading/annotations/history/
    Retourne l'historique des textes de commentaires distincts utilisés par le correcteur.
    Les doublons sont éliminés en normalisant le texte (trim).
    Les résultats sont triés par fréquence d'utilisation.
    """
    permission_classes = [IsTeacherOrAdmin]

    def get(self, request):
        from django.db.models.functions import Trim

        # Annoter avec le contenu nettoyé (trimé) et compter les occurrences
        texts_with_count = (
            Annotation.objects.filter(
                created_by=request.user,
                type__in=[Annotation.Type.COMMENTAIRE]
            )
            .exclude(content='')
            .exclude(content__isnull=True)
            .annotate(trimmed_content=Trim('content'))
            .exclude(trimmed_content='')
            .values('trimmed_content')
            .annotate(usage_count=Count('id'))
            .order_by('-usage_count')[:100]  # Limiter à 100 commentaires max
        )

        # Dé-duplication finale avec un set (insensible à la casse pour comparaison)
        seen = set()
        unique_results = []
        for item in texts_with_count:
            text = item['trimmed_content']
            normalized = text.strip().lower()
            if normalized not in seen:
                seen.add(normalized)
                unique_results.append({"content": text, "type": "COMMENTAIRE"})

        return Response(unique_results)


class CopyReadyView(APIView):
    permission_classes = [IsTeacherOrAdmin]
    def post(self, request, id):
        copy = get_object_or_404(Copy, id=id)
        # LOT 8 FIX: Ownership check — only assigned corrector or admin
        if not _can_write_copy(request.user, copy):
            return Response(
                {"detail": "Seul le correcteur assigné ou un admin peut valider cette copie."},
                status=status.HTTP_403_FORBIDDEN,
            )
        try:
            result = GradingService.ready_copy(copy, request.user)
            return Response({"status": result.status})
        except (ValueError, PermissionError) as e:
            return _handle_service_error(e)

class CopyFinalizeView(APIView):
    permission_classes = [IsTeacherOrAdmin]
    def post(self, request, id):
        copy = get_object_or_404(Copy, id=id)
        # LOT 8 FIX: Ownership check — only assigned corrector or admin
        if not _can_write_copy(request.user, copy):
            return Response(
                {"detail": "Seul le correcteur assigné ou un admin peut finaliser cette copie."},
                status=status.HTTP_403_FORBIDDEN,
            )
        if copy.status == Copy.Status.FINALIZED:
            return Response({"detail": "Copie déjà finalisée."}, status=status.HTTP_400_BAD_REQUEST)
        # Collect warnings (non-blocking)
        warnings = []
        ann_count = Annotation.objects.filter(copy=copy).count()
        if ann_count == 0:
            warnings.append("Aucune annotation sur cette copie.")
        try:
            finalized = GradingService.finalize_copy(copy, request.user)
            data = {"status": finalized.status}
            if warnings:
                data["warnings"] = warnings
            return Response(data)
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
        - Only FINALIZED copies are accessible
        - Even admins cannot access non-FINALIZED copies
    
    Gate 2 - Permission Check (lines 186-215):
        - Teachers/Admins: Verified via is_superuser/Admin/Teacher group membership
        - Students: Verified via session student_id + ownership check
        - Students can ONLY access THEIR OWN copies
        - 401 if no authentication
        - 403 if wrong student tries to access
    
    Audit Trail: All downloads are logged (line 222)
    
    Conformité: docs/security/MANUEL_SECURITE.md — Accès PDF Final
    Référence Audit: P1 Security Review - 2026-01-24
    """
    from rest_framework.permissions import AllowAny
    permission_classes = [AllowAny]  # JUSTIFIED - See docstring security gates
    renderer_classes = [PassthroughRenderer]
    
    def get(self, request, id):
        copy = get_object_or_404(Copy, id=id)

        # ---- Status gate: Final PDF only available for FINALIZED copies ----
        # Even teachers/admins cannot access PDF for non-FINALIZED copies (403)
        if copy.status != Copy.Status.FINALIZED:
            return Response(
                {"detail": "Final PDF is only available when copy is FINALIZED."},
                status=status.HTTP_403_FORBIDDEN
            )

        # ---- Permission gate: teacher/admin OR owning student session ----
        teacher_or_admin = (
            getattr(request.user, "is_authenticated", False) and (
                getattr(request.user, "is_superuser", False) or
                request.user.groups.filter(name__iexact=UserRole.TEACHER).exists() or
                request.user.groups.filter(name__iexact=UserRole.ADMIN).exists()
            )
        )
        
        if not teacher_or_admin:
            student_id = request.session.get("student_id")
            if not student_id:
                return Response(
                    {"detail": "Authentification requise."},
                    status=status.HTTP_401_UNAUTHORIZED
                )

            # Cast student_id (session can be str)
            try:
                sid = int(student_id)
            except Exception:
                return Response(
                    {"detail": "Session invalide."},
                    status=status.HTTP_401_UNAUTHORIZED
                )

            if not copy.student_id or copy.student_id != sid:
                return Response(
                    {"detail": "Vous n'avez pas la permission de consulter cette copie."},
                    status=status.HTTP_403_FORBIDDEN
                )

            # LOT 8 FIX: Students can only access PDF after results are officially released.
            # Aligned with StudentCopiesView logic:
            #   - results_released_at is NULL → NOT released yet → access denied
            #   - results_released_at is set → must be in the past
            from django.utils import timezone
            if (
                copy.exam
                and (
                    copy.exam.results_released_at is None
                    or copy.exam.results_released_at > timezone.now()
                )
            ):
                return Response(
                    {"detail": "Les résultats ne sont pas encore publiés."},
                    status=status.HTTP_403_FORBIDDEN
                )

        # Check if PDF is pending regeneration after score correction
        if copy.pdf_regeneration_pending:
            return Response(
                {"detail": "Le PDF final est en cours de régénération suite à une correction de note. Veuillez réessayer dans quelques instants."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE
            )

        if not copy.final_pdf:
            return Response({"detail": "PDF final non disponible."}, status=status.HTTP_404_NOT_FOUND)

        # Audit trail: Téléchargement PDF final
        from core.utils.audit import log_data_access
        log_data_access(request, 'Copy', copy.id, action_detail='download')

        # LOT 2: Use X-Accel-Redirect for zero-copy file serving via Nginx
        from django.http import HttpResponse
        response = HttpResponse(content_type="application/pdf")
        response['X-Accel-Redirect'] = f'/internal-media/{copy.final_pdf.name}'
        filename = f'copy_{copy.anonymous_id}_corrected.pdf'
        disposition = 'attachment' if request.query_params.get('download') == '1' else 'inline'
        response["Content-Disposition"] = f'{disposition}; filename="{filename}"'
        response["Cache-Control"] = "private, no-store, no-cache, must-revalidate, max-age=0"
        response["Pragma"] = "no-cache"
        response["Expires"] = "0"
        response["X-Content-Type-Options"] = "nosniff"
        response["X-Frame-Options"] = "SAMEORIGIN"
        response["Content-Security-Policy"] = "frame-ancestors 'self'"
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


class QuestionRemarkListCreateView(generics.ListCreateAPIView):
    """
    GET: Liste les remarques d'une copie.
    POST: Crée ou met à jour une remarque sur une question.
    """
    permission_classes = [IsTeacherOrAdmin]
    serializer_class = QuestionRemarkSerializer

    def get_queryset(self):
        copy_id = self.kwargs['copy_id']
        copy = get_object_or_404(Copy, id=copy_id)
        return QuestionRemark.objects.filter(copy=copy).select_related('created_by').order_by('created_at')

    def create(self, request, *args, **kwargs):
        copy_id = self.kwargs['copy_id']
        copy = get_object_or_404(Copy, id=copy_id)

        # LOT 5: Only assigned corrector or admin can create/update remarks
        if not _can_write_copy(request.user, copy):
            return Response({"detail": "Seul le correcteur assigné peut modifier les remarques de cette copie."}, status=status.HTTP_403_FORBIDDEN)

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

        # Audit trail
        try:
            GradingEvent.objects.create(
                copy=copy,
                actor=request.user,
                action=GradingEvent.Action.REMARK_SAVED,
                metadata={'question_id': question_id, 'created': created},
            )
        except Exception:
            logger.warning("Failed to create GradingEvent for remark save on copy %s", copy_id)

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

        # LOT 5 fix: use _can_write_copy for consistent permission check
        if not _can_write_copy(request.user, remark_obj.copy):
            return Response(
                {"detail": "Seul le correcteur assigné ou un admin peut modifier cette remarque."},
                status=status.HTTP_403_FORBIDDEN
            )

        partial = kwargs.pop('partial', False)
        serializer = self.get_serializer(remark_obj, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(serializer.data)

    def destroy(self, request, *args, **kwargs):
        remark_obj = self.get_object()

        # LOT 5 fix: use _can_write_copy for consistent permission check
        if not _can_write_copy(request.user, remark_obj.copy):
            return Response(
                {"detail": "Seul le correcteur assigné ou un admin peut supprimer cette remarque."},
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

        # LOT 5: Only assigned corrector or admin can update appreciation
        if not _can_write_copy(request.user, copy):
            return Response({"detail": "Seul le correcteur assigné peut modifier l'appréciation de cette copie."}, status=status.HTTP_403_FORBIDDEN)

        global_appreciation = request.data.get('global_appreciation', '')

        update_fields = ['global_appreciation']
        if copy.status == Copy.Status.READY:
            copy.status = Copy.Status.IN_PROGRESS
            update_fields.append('status')
        copy.global_appreciation = global_appreciation
        copy.save(update_fields=update_fields)

        # Audit trail
        try:
            GradingEvent.objects.create(
                copy=copy,
                actor=request.user,
                action=GradingEvent.Action.SAVE_APPRECIATION,
                metadata={'length': len(global_appreciation)},
            )
        except Exception:
            logger.warning("Failed to create GradingEvent for appreciation save on copy %s", copy_id)

        return Response({
            'copy_id': str(copy.id),
            'global_appreciation': copy.global_appreciation or ''
        })


class CopyScoresView(APIView):
    """
    GET/PUT /api/grading/copies/<uuid>/scores/
    Save and retrieve per-question scores for a copy.
    scores_data format: {"question_id": score_value, ...}

    GET requires teacher/admin AND assigned-corrector ownership (P0.1).
    PUT requires IsTeacherOrAdmin + assigned corrector ownership.
    """
    permission_classes = [IsTeacherOrAdmin]

    def get(self, request, copy_id):
        copy = get_object_or_404(Copy, id=copy_id)

        # P0.1: Only assigned corrector or admin may read raw scores
        if not _can_read_copy_scores(request.user, copy):
            return Response(
                {"detail": "Vous n'êtes pas autorisé à consulter les notes de cette copie."},
                status=status.HTTP_403_FORBIDDEN,
            )

        score = Score.objects.filter(copy=copy).first()
        if not score:
            return Response({
                'copy_id': str(copy.id),
                'scores_data': {},
                'final_comment': '',
            })
        return Response({
            'copy_id': str(copy.id),
            'scores_data': score.scores_data or {},
            'final_comment': score.final_comment or '',
        })

    def put(self, request, copy_id):
        copy = get_object_or_404(Copy, id=copy_id)

        # LOT 5: Only assigned corrector or admin can save scores
        if not _can_write_copy(request.user, copy):
            return Response({"detail": "Seul le correcteur assigné peut modifier les notes de cette copie."}, status=status.HTTP_403_FORBIDDEN)

        if copy.status == Copy.Status.FINALIZED and not request.user.is_superuser:
            return Response(
                {"detail": "Impossible de modifier les notes d'une copie déjà finalisée."},
                status=status.HTTP_400_BAD_REQUEST
            )
        if copy.status == Copy.Status.FINALIZED and request.user.is_superuser:
            logger.info("Admin %s overriding FINALIZED status for copy %s", request.user.username, copy_id)

        scores_data = request.data.get('scores_data', {})
        final_comment = request.data.get('final_comment', '')

        if not isinstance(scores_data, dict):
            return Response(
                {"detail": "scores_data must be a dict."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Validate score values are numeric + non-negative + within max
        q_max = Q_MAX_BY_EXAM.get(copy.exam.name, {})
        # Try to build q_max from grading_structure (newer exams with UUID keys)
        if not q_max and copy.exam.grading_structure:
            from exams.grading_utils import build_q_max as _bq; q_max = _bq(copy.exam.grading_structure)
        for qid, val in scores_data.items():
            if val is not None and val != '':
                try:
                    fval = float(val)
                except (TypeError, ValueError):
                    return Response(
                        {"detail": f"La note pour '{qid}' doit être numérique, reçu '{val}'."},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                if fval < 0:
                    return Response(
                        {"detail": f"La note pour '{qid}' ne peut pas être négative."},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                # Validate against max score if defined
                if q_max and qid in q_max:
                    max_score = float(q_max[qid])
                    if fval > max_score + 0.01:  # 0.01 epsilon for float precision
                        return Response(
                            {"detail": f"La note pour '{qid}' dépasse le maximum autorisé ({max_score} pts)."},
                            status=status.HTTP_400_BAD_REQUEST
                        )
                if fval < 0:
                    return Response(
                        {"detail": f"La note pour '{qid}' ne peut pas être négative ({fval})."},
                        status=status.HTTP_400_BAD_REQUEST
                    )

        # LOT 6: Validate individual scores against barème max
        # First try grading_structure (handles both UUID and positional IDs)
        from exams.grading_utils import build_q_max as _build_q_max_gs
        q_max = _build_q_max_gs(copy.exam.grading_structure) if copy.exam else {}
        # Fallback to hardcoded constraints (DEPRECATED: prefer grading_structure)
        if not q_max:
            pass  # Q_MAX_BY_EXAM imported at module level
            q_max = Q_MAX_BY_EXAM.get(copy.exam.name, {})
            if q_max:
                logger.warning(f"DEPRECATED: Using hardcoded Q_MAX_BY_EXAM fallback for {copy.exam.name}. Update grading_structure!")
        if q_max:
            overflow_warnings: list[str] = []
            for qid, val in scores_data.items():
                if val is not None and val != '' and qid in q_max:
                    fval = float(val)
                    max_val = float(q_max[qid])
                    if fval > max_val:
                        overflow_warnings.append(str(f"'{qid}': {fval} > max {max_val}"))
            if overflow_warnings:
                return Response(
                    {"detail": f"Score(s) dépassant le barème: {'; '.join(overflow_warnings)}"},
                    status=status.HTTP_400_BAD_REQUEST
                )

        # Validate total score does not exceed exam max
        total_score = sum(float(v) for v in scores_data.values() if v is not None and v != '')
        from exams.grading_utils import extract_leaf_questions
        _leaves = extract_leaf_questions(copy.exam.grading_structure) if copy.exam else []
        _max_total = sum(float(q['points']) for q in _leaves) if _leaves else 20.0
        if total_score > _max_total + 0.01:
            return Response(
                {"detail": f"Le total des notes ({total_score}) dépasse le maximum autorisé ({_max_total} pts)."},
                status=status.HTTP_400_BAD_REQUEST
            )

        from django.db import transaction
        with transaction.atomic():
            locked_copy = Copy.objects.select_for_update().filter(id=copy.id).first()
            if locked_copy and locked_copy.status == Copy.Status.READY:
                locked_copy.status = Copy.Status.IN_PROGRESS
                locked_copy.save(update_fields=['status'])
                copy.status = locked_copy.status

            score, created = Score.objects.update_or_create(
                copy=copy,
                defaults={
                    'scores_data': scores_data,
                    'final_comment': final_comment,
                }
            )

            # Audit trail: log every score save for traceability
            try:
                nq = len([v for v in scores_data.values() if v is not None and v != ''])
                total: float = sum(float(v) for v in scores_data.values() if v is not None and v != '')
                GradingEvent.objects.create(
                    copy=copy,
                    actor=request.user,
                    action=GradingEvent.Action.SCORES_SAVED,
                metadata={'nq': nq, 'total': float(round(total, 2)), 'created': created},  # type: ignore[call-overload]
                )
            except Exception:
                logger.warning("Failed to create GradingEvent for score save on copy %s", copy_id)

        return Response({
            'copy_id': str(copy.id),
            'scores_data': score.scores_data,
            'final_comment': score.final_comment or '',
            'updated': True,
        })


class CorrectorStatsView(APIView):
    """
    GET /api/grading/exams/<uuid>/stats/
    Returns grading statistics for the corrector's lot and the global exam.
    """
    permission_classes = [IsTeacherOrAdmin]

    def get(self, request, exam_id):
        exam = get_object_or_404(Exam, id=exam_id)

        # Determine if current user is a corrector for this exam
        is_corrector = exam.correctors.filter(id=request.user.id).exists()
        is_admin = request.user.is_superuser or request.user.groups.filter(name__iexact=UserRole.ADMIN).exists()

        if not is_corrector and not is_admin:
            return Response(
                {"detail": "Non autorisé pour cet examen."},
                status=status.HTTP_403_FORBIDDEN
            )

        # Get all copies with scores (FINALIZED or IN_PROGRESS with scores_data)
        all_with_scores = Copy.objects.filter(
            exam=exam, status__in=[Copy.Status.FINALIZED, Copy.Status.IN_PROGRESS]
        ).select_related('assigned_corrector', 'student')

        # LOT 7: Prefetch all scores in one query to avoid N+1
        copy_ids = list(all_with_scores.values_list('id', flat=True))
        scores_by_copy = {}
        for s in Score.objects.filter(copy_id__in=copy_ids):
            scores_by_copy[s.copy_id] = s

        # Get all copies for this exam
        total_copies = Copy.objects.filter(exam=exam).count()
        graded_count = len(copy_ids)

        # Calculate global scores
        global_scores = self._get_scores_for_copies(all_with_scores, scores_by_copy)

        result = {
            'exam_id': str(exam.id),
            'exam_name': exam.name,
            'total_copies': total_copies,
            'graded_copies': graded_count,
            'all_graded': graded_count == total_copies and total_copies > 0,
            'global_stats': self._compute_stats(global_scores),
            'global_distribution': self._compute_distribution(global_scores),
        }

        # If corrector, add lot-specific stats
        if is_corrector:
            lot_graded = all_with_scores.filter(assigned_corrector=request.user)
            lot_total = Copy.objects.filter(
                exam=exam, assigned_corrector=request.user
            ).count()
            lot_scores = self._get_scores_for_copies(lot_graded, scores_by_copy)

            result['lot_stats'] = {
                'total': lot_total,
                'graded': lot_graded.count(),
                'all_graded': lot_graded.count() == lot_total and lot_total > 0,
                **self._compute_stats(lot_scores),
            }
            result['lot_distribution'] = self._compute_distribution(lot_scores)

        # Group-level stats
        group_stats = self._compute_group_stats(all_with_scores, global_scores, scores_by_copy)
        result['group_stats'] = group_stats

        return Response(result)

    def _compute_group_stats(self, copies_qs, global_scores, scores_by_copy=None):
        """Compute stats per student group or class."""
        # Try groups first
        use_class = False
        if not any(c.student and c.student.groupe for c in copies_qs):
            use_class = True
            if not any(c.student and c.student.class_name for c in copies_qs):
                return []

        from collections import defaultdict
        group_scores = defaultdict(list)
        for copy in copies_qs:
            if not copy.student:
                continue
            
            if use_class:
                label = copy.student.class_name or 'Non assignée'
            else:
                label = copy.student.groupe or 'Non assigné'

            score_obj = scores_by_copy.get(copy.id) if scores_by_copy else Score.objects.filter(copy=copy).first()
            if score_obj and score_obj.scores_data:
                _sd_g: dict[str, object] = _cast(dict, score_obj.scores_data)
                total: float = 0.0
                for val in _sd_g.values():
                    try:
                        total += float(val) if val is not None and val != '' else 0.0  # type: ignore[arg-type]
                    except (TypeError, ValueError):
                        pass
                _gs: list = group_scores[label]  # type: ignore[assignment]
                _gs.append(total)

        global_mean: float = float(statistics.mean(global_scores)) if global_scores else 0.0
        result: list[dict[str, object]] = []
        for label in sorted(group_scores.keys()):
            scores = group_scores[label]
            stats: dict[str, object] = dict(self._compute_stats(scores))
            stats['groupe'] = label # Keep key as 'groupe' for frontend compat
            stats['type'] = 'classe' if use_class else 'groupe'
            stats['above_mean'] = sum(1 for s in scores if s >= global_mean)
            stats['below_mean'] = sum(1 for s in scores if s < global_mean)
            stats['distribution'] = self._compute_distribution(scores)
            result.append(stats)
        return result

    def _get_scores_for_copies(self, copies_qs, scores_by_copy=None):
        """Extract total scores from Score objects for given copies."""
        scores = []
        for copy in copies_qs:
            # LOT 7: Use prefetched scores dict instead of per-copy query
            score_obj = scores_by_copy.get(copy.id) if scores_by_copy else Score.objects.filter(copy=copy).first()
            if score_obj and score_obj.scores_data:
                _sd_s: dict[str, object] = _cast(dict, score_obj.scores_data)
                total: float = 0.0
                for val in _sd_s.values():
                    try:
                        total += float(val) if val is not None and val != '' else 0.0  # type: ignore[arg-type]
                    except (TypeError, ValueError):
                        pass
                scores.append(total)
        return scores

    def _compute_stats(self, scores: list) -> dict[str, object]:
        """Compute statistical indicators."""
        if not scores:
            return {
                'mean': None, 'median': None, 'std_dev': None,
                'min': None, 'max': None, 'count': 0,
            }
        return {
            'mean': float(round(statistics.mean(scores), 2)),
            'median': float(round(statistics.median(scores), 2)),
            'std_dev': float(round(statistics.stdev(scores), 2)) if len(scores) > 1 else 0.0,
            'min': float(round(min(scores), 2)),
            'max': float(round(max(scores), 2)),
            'count': len(scores),
        }

    def _compute_distribution(self, scores):
        """Compute histogram distribution (1-point bins from 0 to max(20, ceil(max_score)))."""
        if not scores:
            return []
        import math
        upper = max(20, int(math.ceil(max(scores))))
        bins = []
        for note in range(upper + 1):
            def _safe_round_note(score: float) -> float:
                return float(round(score, 1))  # type: ignore[call-overload]
            count = sum(1 for s in scores if note <= _safe_round_note(float(s)) < note + 1)
            bins.append({
                'range': str(note),
                'start': note,
                'end': note + 1,
                'count': count,
            })
        return bins


class ExamReleaseResultsView(APIView):
    """
    POST /api/exams/<uuid>/release-results/
    Mark exam results as released (students can see their grades).
    Restricted to admin only via permission class.
    """
    permission_classes = [IsKorrigoAdmin]

    def post(self, request, exam_id):
        from django.db import transaction
        from django.utils import timezone
        from grading.tasks import notify_students_results_released
        with transaction.atomic():
            exam = Exam.objects.select_for_update().get(id=exam_id)
            if exam.results_released_at:
                return Response({
                    'message': 'Résultats déjà publiés.',
                    'released_at': exam.results_released_at.isoformat(),
                    'notification_task': 'skipped',
                })
            exam.results_released_at = timezone.now()
            exam.save(update_fields=['results_released_at'])
        task = notify_students_results_released.delay(str(exam.id))
        log_audit(
            request,
            'exam.results_released',
            'Exam',
            exam.id,
            {'released_at': exam.results_released_at.isoformat(), 'notification_task_id': str(task.id)},
        )
        return Response({
            'message': 'Résultats publiés avec succès.',
            'released_at': exam.results_released_at.isoformat(),
            'notification_task': 'queued',
            'notification_queued': True,
            'task_id': str(task.id),
        })


class ExamUnreleaseResultsView(APIView):
    """
    POST /api/exams/<uuid>/unrelease-results/
    Revoke result visibility for students.
    Restricted to admin only via permission class.
    """
    permission_classes = [IsKorrigoAdmin]

    def post(self, request, exam_id):
        exam = get_object_or_404(Exam, id=exam_id)
        exam.results_released_at = None
        exam.save(update_fields=['results_released_at'])
        return Response({'message': 'Publication des résultats annulée.'})


class ExamLLMSummaryView(APIView):
    """
    POST /api/grading/exams/<uuid>/generate-summaries/
    Génère les bilans LLM pour toutes les copies FINALIZED d'un examen.
    Query param ?force=true pour régénérer les bilans existants.
    """
    permission_classes = [IsTeacherOrAdmin]

    def post(self, request, exam_id):
        exam = get_object_or_404(Exam, id=exam_id)
        force = request.query_params.get('force', 'false').lower() == 'true'

        from processing.services.llm_summary import LLMSummaryService
        try:
            stats = LLMSummaryService.generate_batch(str(exam.id), force=force)
        except Exception as e:
            return Response(
                {'detail': f'Erreur lors de la génération des bilans: {_trunc(str(e))}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        return Response({
            'exam_id': str(exam.id),
            'exam_name': exam.name,
            'success': stats['success'],
            'skipped': stats['skipped'],
            'errors': stats['errors'],
            'details': stats['details'],
        })


class CopyLLMSummaryView(APIView):
    """
    POST /api/grading/copies/<uuid>/generate-summary/
    Génère le bilan LLM pour une seule copie FINALIZED.
    """
    permission_classes = [IsTeacherOrAdmin]

    def post(self, request, copy_id):
        copy = get_object_or_404(Copy, id=copy_id)

        if copy.status != Copy.Status.FINALIZED:
            return Response(
                {'detail': 'Seules les copies finalisées peuvent avoir un bilan LLM.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        from processing.services.llm_summary import LLMSummaryService
        try:
            summary = LLMSummaryService.generate_summary(copy)
        except Exception as e:
            return Response(
                {'detail': f'Erreur LLM: {_trunc(str(e))}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        return Response({
            'copy_id': str(copy.id),
            'anonymous_id': copy.anonymous_id,
            'llm_summary': summary,
        })


class AdminForceUnlockView(APIView):
    """
    POST /api/grading/copies/<uuid>/force-unlock/
    Force-deletes the CopyLock for the given copy.
    If the copy is FINALIZED, it is also reopened to READY so the admin can edit it
    without changing the corrector assignment.
    Admin-only (superuser or staff).
    """
    permission_classes = [IsKorrigoAdmin]

    def post(self, request, copy_id):
        copy = get_object_or_404(Copy, id=copy_id)
        previous_status = copy.status
        reopened_from_finalized = False

        if copy.status == Copy.Status.FINALIZED:
            copy.status = Copy.Status.READY
            copy.final_pdf = None
            copy.graded_at = None
            copy.grading_retries = 0
            copy.save(update_fields=['status', 'final_pdf', 'graded_at', 'grading_retries'])
            reopened_from_finalized = True

        # If reopened from FINALIZED, log a dedicated REOPEN event for audit trail
        if reopened_from_finalized:
            GradingEvent.objects.create(
                copy=copy,
                actor=request.user,
                action=GradingEvent.Action.REOPEN,
                metadata={
                    'previous_status': previous_status,
                    'previous_final_pdf': str(copy.final_pdf) if copy.final_pdf else None,
                    'previous_graded_at': None,
                    'via': 'admin_force_unlock',
                },
            )

        try:
            lock = CopyLock.objects.get(copy=copy)
            lock_owner = lock.owner.username
            lock.delete()
        except CopyLock.DoesNotExist:
            # No lock exists. If we reopened a FINALIZED copy, still return 200 so
            # the caller knows the copy is editable again.
            GradingEvent.objects.create(
                copy=copy,
                actor=request.user,
                action=GradingEvent.Action.UNLOCK,
                metadata={
                    'admin_force': True,
                    'had_lock': False,
                    'previous_status': previous_status,
                    'reopened_from_finalized': reopened_from_finalized,
                },
            )
            if reopened_from_finalized:
                return Response({
                    'message': 'Copie rouverte avec succès et prête à être corrigée.',
                    'copy_id': str(copy.id),
                })
            return Response(status=status.HTTP_204_NO_CONTENT)

        GradingEvent.objects.create(
            copy=copy,
            actor=request.user,
            action=GradingEvent.Action.UNLOCK,
            metadata={
                'admin_force': True,
                'had_lock': True,
                'previous_lock_owner': lock_owner,
                'previous_status': previous_status,
                'reopened_from_finalized': reopened_from_finalized,
            },
        )

        if reopened_from_finalized:
            return Response({
                'message': f'Verrou supprimé et copie rouverte avec succès (ancien propriétaire: {lock_owner}).',
                'copy_id': str(copy.id),
            })

        return Response({
            'message': f'Verrou supprimé avec succès (ancien propriétaire: {lock_owner}).',
            'copy_id': str(copy.id),
        })


class CopyReopenView(APIView):
    """
    POST /api/grading/copies/<uuid>/reopen/
    Reopen a FINALIZED copy back to READY status.
    Admin-only (superuser).
    """
    permission_classes = [IsKorrigoAdmin]

    def post(self, request, copy_id):
        copy = get_object_or_404(Copy, id=copy_id)

        if copy.status != Copy.Status.FINALIZED:
            return Response(
                {"detail": f"La copie doit être en statut FINALIZED pour être rouverte (statut actuel: {copy.status})."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        previous_status = copy.status
        previous_final_pdf = str(copy.final_pdf) if copy.final_pdf else None
        previous_graded_at = copy.graded_at.isoformat() if copy.graded_at else None

        copy.status = Copy.Status.READY
        copy.final_pdf = None
        copy.graded_at = None
        copy.grading_retries = 0
        copy.save(update_fields=['status', 'final_pdf', 'graded_at', 'grading_retries'])

        GradingEvent.objects.create(
            copy=copy,
            actor=request.user,
            action=GradingEvent.Action.REOPEN,
            metadata={
                'previous_status': previous_status,
                'previous_final_pdf': previous_final_pdf,
                'previous_graded_at': previous_graded_at,
            },
        )

        return Response({
            'message': 'Copie rouverte avec succès.',
            'copy_id': str(copy.id),
            'anonymous_id': copy.anonymous_id,
            'status': copy.status,
        })


class CopyAnnotationsExportView(APIView):
    """
    GET /api/grading/copies/<uuid>/export-annotations/
    Export complet des données de correction d'une copie.
    """
    permission_classes = [IsTeacherOrAdmin]

    def get(self, request, copy_id):
        from django.utils import timezone

        copy = get_object_or_404(
            Copy.objects.select_related('student', 'assigned_corrector').prefetch_related(
                'annotations', 'question_remarks', 'scores'
            ),
            id=copy_id,
        )
        if not _can_write_copy(request.user, copy):
            return Response(
                {'detail': 'Non autorisé pour cette copie.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        is_admin = (
            request.user.is_superuser
            or request.user.groups.filter(name__iexact=UserRole.ADMIN).exists()
        )
        payload = {
            **_serialize_copy_export(copy, include_student_id=is_admin),
            'exported_at': timezone.now().isoformat(),
            'exported_by': request.user.username,
        }
        log_audit(request, 'copy.annotations_export', 'Copy', copy.id, {'format': 'json'})
        return Response(payload)


class ExamAnnotationsExportView(APIView):
    """
    GET /api/grading/exams/<uuid>/export-all-annotations/
    Export batch des annotations d'un examen.
    """
    permission_classes = [IsKorrigoAdmin]
    renderer_classes = [renderers.JSONRenderer, ZipPassthroughRenderer]

    def get(self, request, exam_id):
        from django.utils import timezone

        exam = get_object_or_404(Exam, id=exam_id)
        export_format = request.query_params.get('format', 'json').lower()
        if export_format not in {'json', 'zip'}:
            return Response(
                {'detail': 'Format d’export invalide. Utilisez json ou zip.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        copies = list(
            Copy.objects.filter(exam=exam, status=Copy.Status.FINALIZED)
            .select_related('student', 'assigned_corrector')
            .prefetch_related('annotations', 'question_remarks', 'scores')
            .order_by('anonymous_id')
        )

        exported_at = timezone.now().isoformat()
        payload = {
            'exam_id': str(exam.id),
            'exam_name': exam.name,
            'copies_count': len(copies),
            'exported_at': exported_at,
            'copies': [_serialize_copy_export(copy, include_student_id=True) for copy in copies],
        }
        log_audit(request, 'exam.annotations_export', 'Exam', exam.id, {'format': export_format})

        if export_format == 'json':
            return Response(payload)

        buffer = BytesIO()
        with ZipFile(buffer, 'w', ZIP_DEFLATED) as zip_file:
            zip_file.writestr(
                'meta.json',
                json.dumps(
                    {
                        'exam_id': str(exam.id),
                        'exam_name': exam.name,
                        'copies_count': len(copies),
                        'exported_at': exported_at,
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
            )
            for copy in copies:
                zip_file.writestr(
                    f"copies/{copy.anonymous_id}.json",
                    json.dumps(
                        _serialize_copy_export(copy, include_student_id=True),
                        ensure_ascii=False,
                        indent=2,
                    ),
                )
        buffer.seek(0)

        response = HttpResponse(buffer.getvalue(), content_type='application/zip')
        response['Content-Disposition'] = f'attachment; filename="exam-{exam.id}-annotations.zip"'
        return response


class CopyScoreCorrectionView(APIView):
    """
    POST /api/grading/copies/<uuid:copy_id>/score-correction/
    Allow authorized users to correct scores on FINALIZED copies with mandatory justification.
    
    Permissions:
    - Admin: can correct directly
    - Assigned corrector: can correct directly
    - Assigned teacher (via TeacherGroupAssignment): can correct directly
    
    Requirements:
    - Copy must be FINALIZED
    - 'reason' field is mandatory (justification for correction)
    - Scores must respect the barème (same validation as CopyScoresView)
    - Creates GradingEvent SCORE_CORRECTED with old/new totals
    - Invalidates final_pdf (sets to None) to force regeneration
    """
    permission_classes = [IsAuthenticated]

    def _can_correct_copy(self, user, copy: Copy) -> tuple[bool, str]:
        """
        Check if user is allowed to correct this FINALIZED copy.
        Returns (allowed, error_message).

        Rules:
        - Admin/superuser: can correct directly
        - Assigned corrector: can correct directly
        - Teacher assigned to student's group but not corrector: NOT allowed (403)
        - Unrelated teacher: NOT allowed (403)
        """
        if user.is_superuser:
            return True, ""
        if user.groups.filter(name__iexact=UserRole.ADMIN).exists():
            return True, ""
        
        # Only assigned corrector can correct
        if copy.assigned_corrector_id == user.id:
            return True, ""
        
        # All other users (including teachers assigned to student's group) are denied
        return False, "Vous n'êtes pas autorisé à corriger cette copie."

    def post(self, request, copy_id):
        copy = get_object_or_404(Copy, id=copy_id)

        # Check copy status
        if copy.status != Copy.Status.FINALIZED:
            return Response(
                {"detail": "Seules les copies finalisées peuvent être corrigées via ce endpoint."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Check permissions
        allowed, error_msg = self._can_correct_copy(request.user, copy)
        if not allowed:
            return Response({"detail": error_msg}, status=status.HTTP_403_FORBIDDEN)

        # Validate mandatory reason
        reason = request.data.get('reason', '').strip()
        if not reason:
            return Response(
                {"detail": "La justification (reason) est obligatoire pour toute correction de note."},
                status=status.HTTP_400_BAD_REQUEST
            )

        scores_data = request.data.get('scores_data', {})
        final_comment = request.data.get('final_comment', '')

        if not isinstance(scores_data, dict):
            return Response(
                {"detail": "scores_data must be a dict."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Validate score values (reuse CopyScoresView logic)
        from exams.grading_utils import build_q_max, extract_leaf_questions

        # Build q_max from grading_structure
        q_max = build_q_max(copy.exam.grading_structure) if copy.exam and copy.exam.grading_structure else {}
        # Fallback to hardcoded constraints
        if not q_max:
            q_max = Q_MAX_BY_EXAM.get(copy.exam.name, {}) if copy.exam else {}

        for qid, val in scores_data.items():
            if val is not None and val != '':
                try:
                    fval = float(val)
                except (TypeError, ValueError):
                    return Response(
                        {"detail": f"La note pour '{qid}' doit être numérique, reçu '{val}'."},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                if fval < 0:
                    return Response(
                        {"detail": f"La note pour '{qid}' ne peut pas être négative."},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                # Validate against max score if defined
                if q_max and qid in q_max:
                    max_score = float(q_max[qid])
                    if fval > max_score + 0.01:
                        return Response(
                            {"detail": f"La note pour '{qid}' dépasse le maximum autorisé ({max_score} pts)."},
                            status=status.HTTP_400_BAD_REQUEST
                        )

        # Validate total score does not exceed exam max
        total_score = sum(float(v) for v in scores_data.values() if v is not None and v != '')
        leaves = extract_leaf_questions(copy.exam.grading_structure) if copy.exam else []
        max_total = sum(float(q['points']) for q in leaves) if leaves else 20.0
        if total_score > max_total + 0.01:
            return Response(
                {"detail": f"Le total des notes ({total_score}) dépasse le maximum autorisé ({max_total} pts)."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Get old total for audit
        old_score = Score.objects.filter(copy=copy).first()
        old_total = 0.0
        if old_score and old_score.scores_data:
            old_total = sum(float(v) for v in old_score.scores_data.values() if v is not None and v != '')

        from django.db import transaction
        with transaction.atomic():
            # Update or create score
            score, created = Score.objects.update_or_create(
                copy=copy,
                defaults={
                    'scores_data': scores_data,
                    'final_comment': final_comment,
                }
            )

            # Mark PDF for regeneration instead of deleting it
            copy.pdf_regeneration_pending = True
            copy.save(update_fields=['pdf_regeneration_pending'])

            # Audit trail: log correction with old/new scores and totals
            try:
                nq = len([v for v in scores_data.values() if v is not None and v != ''])
                new_total = float(round(total_score, 2))
                GradingEvent.objects.create(
                    copy=copy,
                    actor=request.user,
                    action=GradingEvent.Action.SCORE_CORRECTED,
                    metadata={
                        'old_scores_data': old_score.scores_data if old_score else {},
                        'new_scores_data': scores_data,
                        'old_total': float(round(old_total, 2)),
                        'new_total': new_total,
                        'reason': reason[:500],  # Truncate to 500 chars
                        'nq': nq,
                    }
                )
            except Exception:
                logger.warning("Failed to create GradingEvent for score correction on copy %s", copy_id)

        return Response({
            'copy_id': str(copy.id),
            'scores_data': score.scores_data,
            'final_comment': score.final_comment or '',
            'old_total': float(round(old_total, 2)),
            'new_total': float(round(total_score, 2)),
            'pdf_regeneration_pending': copy.pdf_regeneration_pending,
        })


class CopyPdfRegenerationView(APIView):
    """
    POST /api/grading/copies/<uuid:copy_id>/regenerate-final-pdf/

    Admin-only endpoint to regenerate the final PDF for a copy after score correction.

    This endpoint:
    - Is restricted to admin/superuser only
    - Verifies that pdf_regeneration_pending=True
    - Regenerates the final PDF using PDFFlattener
    - Sets pdf_regeneration_pending=False after success
    - Updates final_pdf
    - Creates a GradingEvent with action PDF_REGENERATED

    Security: Only admin/superuser can access this endpoint.
    """
    from rest_framework.permissions import IsAuthenticated
    from core.auth import IsKorrigoAdmin
    permission_classes = [IsAuthenticated, IsKorrigoAdmin]

    def post(self, request, copy_id):
        from django.core.files.base import ContentFile
        from django.utils import timezone
        from processing.services.pdf_flattener import PDFFlattener

        copy = get_object_or_404(Copy, id=copy_id)

        # Check copy status
        if copy.status != Copy.Status.FINALIZED:
            return Response(
                {"detail": "Seules les copies finalisées peuvent avoir leur PDF régénéré."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Check if PDF regeneration is pending
        if not copy.pdf_regeneration_pending:
            return Response(
                {"detail": "Aucune régénération de PDF en attente pour cette copie."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Regenerate PDF using PDFFlattener (same service used in finalization)
        flattener = PDFFlattener()
        try:
            pdf_bytes = flattener.flatten_copy(copy)
            if pdf_bytes is None:
                pdf_bytes = b""
            output_filename = f"copy_{copy.id}_corrected.pdf"
            copy.final_pdf.save(output_filename, ContentFile(pdf_bytes), save=False)
            copy.pdf_regeneration_pending = False
            copy.save(update_fields=["final_pdf", "pdf_regeneration_pending"])

            # Audit trail: log PDF regeneration
            GradingEvent.objects.create(
                copy=copy,
                actor=request.user,
                action=GradingEvent.Action.PDF_REGENERATED,
                metadata={'regenerated_at': timezone.now().isoformat()}
            )

            return Response({
                'copy_id': str(copy.id),
                'status': 'success',
                'pdf_regenerated': True,
            })

        except Exception as exc:
            logger.error(f"PDF regeneration failed for copy {copy_id}: {exc}", exc_info=True)
            return Response(
                {"detail": f"Échec de la régénération du PDF : {str(exc)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
