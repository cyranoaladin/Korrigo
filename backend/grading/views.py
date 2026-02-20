from rest_framework import generics, status
from rest_framework import renderers
from rest_framework.response import Response
from rest_framework.views import APIView
from django.http import FileResponse
from rest_framework.permissions import IsAuthenticated
from .models import Annotation, GradingEvent, QuestionRemark, Score
from exams.models import Copy, Exam
from .serializers import AnnotationSerializer, GradingEventSerializer, QuestionRemarkSerializer
from exams.permissions import IsTeacherOrAdmin
from .permissions import IsLockedByOwnerOrReadOnly
from django.shortcuts import get_object_or_404
from grading.services import AnnotationService, GradingService, LockConflictError
from core.auth import UserRole
from django.db.models import Avg, StdDev, Min, Max, Count
import statistics
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
        {"detail": "Une erreur inattendue s'est produite. Veuillez contacter le support."},
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
            return Response({"detail": "Copie déjà corrigée."}, status=status.HTTP_400_BAD_REQUEST)
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
    
    Conformité: docs/security/MANUEL_SECURITE.md — Accès PDF Final
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
        response["Cache-Control"] = "private, no-store, no-cache, must-revalidate, max-age=0"
        response["Pragma"] = "no-cache"
        response["Expires"] = "0"
        response["X-Content-Type-Options"] = "nosniff"
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


class CopyScoresView(APIView):
    """
    GET/PUT /api/grading/copies/<uuid>/scores/
    Save and retrieve per-question scores for a copy.
    scores_data format: {"question_id": score_value, ...}
    """
    permission_classes = [IsTeacherOrAdmin]

    def get(self, request, copy_id):
        copy = get_object_or_404(Copy, id=copy_id)
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

        if copy.status == Copy.Status.GRADED:
            return Response(
                {"detail": "Cannot modify scores of a graded copy."},
                status=status.HTTP_400_BAD_REQUEST
            )

        scores_data = request.data.get('scores_data', {})
        final_comment = request.data.get('final_comment', '')

        if not isinstance(scores_data, dict):
            return Response(
                {"detail": "scores_data must be a dict."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Validate score values are numeric
        for qid, val in scores_data.items():
            if val is not None and val != '':
                try:
                    float(val)
                except (TypeError, ValueError):
                    return Response(
                        {"detail": f"La note pour '{qid}' doit être numérique, reçu '{val}'."},
                        status=status.HTTP_400_BAD_REQUEST
                    )

        score, created = Score.objects.update_or_create(
            copy=copy,
            defaults={
                'scores_data': scores_data,
                'final_comment': final_comment,
            }
        )

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
    permission_classes = [IsAuthenticated]

    def get(self, request, exam_id):
        exam = get_object_or_404(Exam, id=exam_id)

        # Determine if current user is a corrector for this exam
        is_corrector = exam.correctors.filter(id=request.user.id).exists()
        is_admin = request.user.is_superuser or request.user.groups.filter(name=UserRole.ADMIN).exists()

        if not is_corrector and not is_admin:
            return Response(
                {"detail": "Non autorisé pour cet examen."},
                status=status.HTTP_403_FORBIDDEN
            )

        # Get all graded copies for this exam
        all_graded = Copy.objects.filter(
            exam=exam, status=Copy.Status.GRADED
        ).select_related('assigned_corrector')

        # Get all copies for this exam
        total_copies = Copy.objects.filter(exam=exam).count()
        graded_count = all_graded.count()

        # Calculate global scores
        global_scores = self._get_scores_for_copies(all_graded)

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
            lot_graded = all_graded.filter(assigned_corrector=request.user)
            lot_total = Copy.objects.filter(
                exam=exam, assigned_corrector=request.user
            ).count()
            lot_scores = self._get_scores_for_copies(lot_graded)

            result['lot_stats'] = {
                'total': lot_total,
                'graded': lot_graded.count(),
                'all_graded': lot_graded.count() == lot_total and lot_total > 0,
                **self._compute_stats(lot_scores),
            }
            result['lot_distribution'] = self._compute_distribution(lot_scores)

        return Response(result)

    def _get_scores_for_copies(self, copies_qs):
        """Extract total scores from Score objects for given copies."""
        scores = []
        for copy in copies_qs:
            score_obj = Score.objects.filter(copy=copy).first()
            if score_obj and score_obj.scores_data:
                total = 0
                for val in score_obj.scores_data.values():
                    try:
                        total += float(val) if val is not None and val != '' else 0
                    except (TypeError, ValueError):
                        pass
                scores.append(total)
        return scores

    def _compute_stats(self, scores):
        """Compute statistical indicators."""
        if not scores:
            return {
                'mean': None, 'median': None, 'std_dev': None,
                'min': None, 'max': None, 'count': 0,
            }
        return {
            'mean': round(statistics.mean(scores), 2),
            'median': round(statistics.median(scores), 2),
            'std_dev': round(statistics.stdev(scores), 2) if len(scores) > 1 else 0,
            'min': round(min(scores), 2),
            'max': round(max(scores), 2),
            'count': len(scores),
        }

    def _compute_distribution(self, scores):
        """Compute histogram distribution (bins of 2 points)."""
        if not scores:
            return []
        max_score = max(scores) if scores else 20
        bin_size = 2
        bins = []
        for start in range(0, int(max_score) + bin_size, bin_size):
            end = start + bin_size
            count = sum(1 for s in scores if start <= s < end)
            bins.append({
                'range': f"{start}-{end}",
                'start': start,
                'end': end,
                'count': count,
            })
        return bins


class ExamReleaseResultsView(APIView):
    """
    POST /api/exams/<uuid>/release-results/
    Mark exam results as released (students can see their grades).
    """
    permission_classes = [IsTeacherOrAdmin]

    def post(self, request, exam_id):
        exam = get_object_or_404(Exam, id=exam_id)

        if exam.results_released_at:
            return Response({
                'message': 'Résultats déjà publiés.',
                'released_at': exam.results_released_at.isoformat(),
            })

        from django.utils import timezone
        exam.results_released_at = timezone.now()
        exam.save(update_fields=['results_released_at'])

        return Response({
            'message': 'Résultats publiés avec succès.',
            'released_at': exam.results_released_at.isoformat(),
        })


class ExamUnreleaseResultsView(APIView):
    """
    POST /api/exams/<uuid>/unrelease-results/
    Revoke result visibility for students.
    """
    permission_classes = [IsTeacherOrAdmin]

    def post(self, request, exam_id):
        exam = get_object_or_404(Exam, id=exam_id)
        exam.results_released_at = None
        exam.save(update_fields=['results_released_at'])

        return Response({'message': 'Publication des résultats annulée.'})


class ExamLLMSummaryView(APIView):
    """
    POST /api/grading/exams/<uuid>/generate-summaries/
    Génère les bilans LLM pour toutes les copies GRADED d'un examen.
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
                {'detail': f'Erreur lors de la génération des bilans: {str(e)[:300]}'},
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
    Génère le bilan LLM pour une seule copie GRADED.
    """
    permission_classes = [IsTeacherOrAdmin]

    def post(self, request, copy_id):
        copy = get_object_or_404(Copy, id=copy_id)

        if copy.status != Copy.Status.GRADED:
            return Response(
                {'detail': 'Seules les copies finalisées (GRADED) peuvent avoir un bilan LLM.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        from processing.services.llm_summary import LLMSummaryService
        try:
            summary = LLMSummaryService.generate_summary(copy)
        except Exception as e:
            return Response(
                {'detail': f'Erreur LLM: {str(e)[:300]}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        return Response({
            'copy_id': str(copy.id),
            'anonymous_id': copy.anonymous_id,
            'llm_summary': summary,
        })
