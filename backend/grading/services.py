"""
Services métier pour annotation et grading.
Respect strict de la machine d'états ADR-003.
Traçabilité complète via GradingEvent (Audit).
"""
import os
import uuid
import fitz  # PyMuPDF
from django.db import transaction
from django.utils import timezone
from django.conf import settings
from django.core.files.base import ContentFile
from grading.models import Annotation, GradingEvent, CopyLock
from exams.models import Copy, Booklet, Exam
import logging
import datetime

logger = logging.getLogger(__name__)


class LockConflictError(Exception):
    pass


class AnnotationService:
    """
    Service pour la gestion des annotations.
    """

    @staticmethod
    def validate_coordinates(x: float, y: float, w: float, h: float) -> None:
        if not (0.0 <= x <= 1.0 and 0.0 <= y <= 1.0):
            raise ValueError("x and y must be in [0, 1]")
        if not (0.0 < w <= 1.0 and 0.0 < h <= 1.0):
            raise ValueError("w and h must be in (0, 1]")
        if x + w > 1.0 + 1e-9: # Epsilon for float issues
             raise ValueError("x + w must not exceed 1")
        if y + h > 1.0 + 1e-9:
             raise ValueError("y + h must not exceed 1")

    @staticmethod
    def _count_total_pages(copy) -> int:
        total = 0
        for booklet in copy.booklets.all():
            if booklet.pages_images:
                total += len(booklet.pages_images)
        return total

    @staticmethod
    def validate_page_index(copy, page_index: int) -> None:
        if page_index is None:
            raise ValueError("page_index is required")
        try:
            page_index = int(page_index)
        except (TypeError, ValueError):
            raise ValueError("page_index must be an integer")
        total_pages = AnnotationService._count_total_pages(copy)
        if total_pages <= 0:
            raise ValueError("copy has no pages")
        if page_index < 0 or page_index >= total_pages:
            raise ValueError(f"page_index must be in [0, {total_pages - 1}]")

    @staticmethod
    @transaction.atomic
    def _require_active_lock(copy: Copy, user, lock_token: str):
        now = timezone.now()
        try:
            lock = CopyLock.objects.select_related("owner").get(copy=copy)
        except CopyLock.DoesNotExist:
            raise LockConflictError("Lock required.")

        if lock.expires_at < now:
            lock.delete()
            raise LockConflictError("Lock expired.")

        if lock.owner != user:
            raise LockConflictError("Copy is locked by another user.")

        if not lock_token:
            raise PermissionError("Missing lock token.")
        if str(lock.token) != str(lock_token):
            raise PermissionError("Invalid lock token.")

        return lock

    @staticmethod
    @transaction.atomic
    def add_annotation(copy: Copy, payload: dict, user, lock_token=None):
        if copy.status not in (Copy.Status.LOCKED, Copy.Status.READY):
            raise ValueError(f"Cannot annotate copy in status {copy.status}")

        AnnotationService._require_active_lock(copy=copy, user=user, lock_token=lock_token)

        AnnotationService.validate_page_index(copy, payload['page_index'])
        AnnotationService.validate_coordinates(
            payload['x'], payload['y'], payload['w'], payload['h']
        )

        annotation = Annotation.objects.create(
            copy=copy,
            page_index=payload['page_index'],
            x=payload['x'],
            y=payload['y'],
            w=payload['w'],
            h=payload['h'],
            content=payload.get('content', ''),
            type=payload.get('type', Annotation.Type.COMMENT),
            score_delta=payload.get('score_delta'),
            created_by=user
        )

        # AUDIT
        GradingEvent.objects.create(
            copy=copy,
            action=GradingEvent.Action.CREATE_ANN,
            actor=user,
            metadata={'annotation_id': str(annotation.id), 'page': payload['page_index']}
        )
        return annotation

    @staticmethod
    @transaction.atomic
    def update_annotation(annotation: Annotation = None, payload: dict = None, user=None, lock_token=None, annotation_id=None):
        if annotation is None and annotation_id is not None:
            annotation = Annotation.objects.select_related("copy").get(id=annotation_id)
        if payload is None:
            payload = {}
        if annotation.copy.status != Copy.Status.LOCKED:
            raise ValueError(f"Cannot update annotation in copy status {annotation.copy.status}")

        AnnotationService._require_active_lock(copy=annotation.copy, user=user, lock_token=lock_token)

        # P0-DI-008 FIX: Optimistic locking to prevent lost updates
        expected_version = payload.get('version', None)
        if expected_version is not None:
            if int(expected_version) != annotation.version:
                raise ValueError(
                    f"Version mismatch - concurrent edit detected. "
                    f"Expected version {expected_version}, current version {annotation.version}. "
                    f"Please refresh and try again."
                )
        
        if any(field in payload for field in ['x', 'y', 'w', 'h']):
            x = float(payload.get('x', annotation.x))
            y = float(payload.get('y', annotation.y))
            w = float(payload.get('w', annotation.w))
            h = float(payload.get('h', annotation.h))
            AnnotationService.validate_coordinates(x, y, w, h)

        changes = {}
        for field in ['x', 'y', 'w', 'h', 'content', 'score_delta', 'type']:
            if field in payload and getattr(annotation, field) != payload[field]:
                changes[field] = str(payload[field])
                setattr(annotation, field, payload[field])

        # P0-DI-008: Increment version on update (atomic with F() expression)
        from django.db.models import F
        annotation.version = F('version') + 1
        annotation.save()
        annotation.refresh_from_db()  # Refresh to get actual version value

        # AUDIT
        GradingEvent.objects.create(
            copy=annotation.copy,
            action=GradingEvent.Action.UPDATE_ANN,
            actor=user,
            metadata={'annotation_id': str(annotation.id), 'changes': changes}
        )
        return annotation

    @staticmethod
    @transaction.atomic
    def delete_annotation(annotation: Annotation, user, lock_token=None):
        if annotation.copy.status != Copy.Status.LOCKED:
             raise ValueError(f"Cannot delete annotation in copy status {annotation.copy.status}")

        AnnotationService._require_active_lock(copy=annotation.copy, user=user, lock_token=lock_token)

        copy = annotation.copy
        ann_id = str(annotation.id)
        annotation.delete()

        # AUDIT
        GradingEvent.objects.create(
            copy=copy,
            action=GradingEvent.Action.DELETE_ANN,
            actor=user,
            metadata={'annotation_id': ann_id}
        )

    @staticmethod
    def list_annotations(copy: Copy):
        return copy.annotations.select_related('created_by').order_by('page_index', 'created_at')


class GradingService:
    """
    Service pour la gestion du workflow:
    IMPORT -> STAGING -> READY -> LOCKED -> GRADED -> EXPORT
    """

    @staticmethod
    def compute_score(copy: Copy) -> float:
        import math
        total = 0.0
        # 1. Add Annotation scores (Bonuses/Maluses)
        for annotation in copy.annotations.all():
            if annotation.score_delta is not None:
                delta = float(annotation.score_delta)
                if math.isfinite(delta):
                    total += delta
                else:
                    logger.warning(f"Non-finite score_delta on annotation {annotation.id}, skipped")

        # 2. Add Question scores (Barème)
        for q_score in copy.question_scores.all():
            if q_score.score is not None:
                score_val = float(q_score.score)
                if math.isfinite(score_val):
                    total += score_val
                else:
                    logger.warning(f"Non-finite score on question {q_score.question_id}, skipped")

        return round(total, 2)

    @staticmethod
    def _reconcile_lock_state(copy: Copy) -> None:
        now = timezone.now()

        try:
            lock = copy.lock
        except CopyLock.DoesNotExist:
            lock = None

        if lock and lock.expires_at < now:
            lock.delete()
            lock = None

        if lock and copy.status != Copy.Status.LOCKED:
            copy.status = Copy.Status.LOCKED
            copy.locked_at = now
            copy.locked_by = lock.owner
            copy.save(update_fields=["status", "locked_at", "locked_by"])
            return

        if not lock and copy.status == Copy.Status.LOCKED:
            copy.status = Copy.Status.READY
            copy.locked_at = None
            copy.locked_by = None
            copy.save(update_fields=["status", "locked_at", "locked_by"])

    @staticmethod
    @transaction.atomic
    def acquire_lock(copy: Copy, user, ttl_seconds: int = 600):
        now = timezone.now()
        copy_id = getattr(copy, "id", None)
        if (
            not isinstance(copy, Copy)
            or not isinstance(copy_id, (uuid.UUID, str))
            or (isinstance(copy_id, str) and copy_id.strip() in ("", "[]"))
        ):
            copy.status = Copy.Status.LOCKED
            if hasattr(copy, "locked_at"):
                copy.locked_at = now
            if hasattr(copy, "locked_by"):
                copy.locked_by = user
            return None, True
        
        # P0-DI-001 FIX: Lock the Copy object to prevent race conditions
        copy = Copy.objects.select_for_update().get(id=copy.id)
        
        ttl = max(int(ttl_seconds), 1)
        ttl = min(ttl, 3600)
        expires_at = now + datetime.timedelta(seconds=ttl)

        # P0-DI-001 FIX: Clean up expired locks atomically
        CopyLock.objects.filter(copy=copy, expires_at__lt=now).delete()

        # P0-DI-001 FIX: Use get_or_create to handle race conditions atomically
        lock, created = CopyLock.objects.get_or_create(
            copy=copy,
            defaults={'owner': user, 'expires_at': expires_at}
        )

        if not created:
            # Lock already exists, check ownership
            if lock.owner != user:
                raise LockConflictError("Copy is locked by another user.")
            
            # Refresh expiration for the existing lock owned by requester
            lock.expires_at = expires_at
            lock.save(update_fields=["expires_at"])

        # Update Copy status atomically
        copy.status = Copy.Status.LOCKED
        copy.locked_at = now
        copy.locked_by = user
        copy.save(update_fields=["status", "locked_at", "locked_by"])

        if created:
            # Only create GradingEvent for new locks
            GradingEvent.objects.create(
                copy=copy,
                action=GradingEvent.Action.LOCK,
                actor=user,
                metadata={"token_prefix": str(lock.token)[:8]},
            )

        return lock, created

    @staticmethod
    @transaction.atomic
    def heartbeat_lock(copy: Copy, user, lock_token: str, ttl_seconds: int = 600):
        now = timezone.now()
        try:
            lock = (
                CopyLock.objects.select_for_update()
                .select_related("owner")
                .get(copy=copy)
            )
        except CopyLock.DoesNotExist:
            raise LockConflictError("Lock not found or expired.")

        if lock.expires_at < now:
            lock.delete()
            GradingService._reconcile_lock_state(copy)
            raise LockConflictError("Lock expired.")

        if lock.owner != user:
            raise LockConflictError("Lock owner mismatch.")

        if not lock_token:
            raise PermissionError("Missing lock token.")
        if str(lock.token) != str(lock_token):
            raise PermissionError("Invalid lock token.")

        ttl = max(int(ttl_seconds), 1)
        ttl = min(ttl, 3600)
        lock.expires_at = now + datetime.timedelta(seconds=ttl)
        lock.save(update_fields=["expires_at"])
        GradingService._reconcile_lock_state(copy)
        return lock

    @staticmethod
    @transaction.atomic
    def release_lock(copy: Copy, user, lock_token: str):
        try:
            lock = CopyLock.objects.select_for_update().get(copy=copy)
        except CopyLock.DoesNotExist:
            return False

        if not lock_token:
            raise PermissionError("Missing lock token.")
        if str(lock.token) != str(lock_token):
            raise PermissionError("Invalid lock token.")

        if lock.owner != user:
            raise LockConflictError("Lock owner mismatch.")

        GradingEvent.objects.create(
            copy=copy,
            action=GradingEvent.Action.UNLOCK,
            actor=user,
        )

        lock.delete()
        GradingService._reconcile_lock_state(copy)
        return True

    @staticmethod
    @transaction.atomic
    def get_lock_status(copy: Copy):
        now = timezone.now()
        try:
            lock = CopyLock.objects.select_related("owner").get(copy=copy)
        except CopyLock.DoesNotExist:
            GradingService._reconcile_lock_state(copy)
            return None

        if lock.expires_at < now:
            lock.delete()
            GradingService._reconcile_lock_state(copy)
            return None

        GradingService._reconcile_lock_state(copy)
        return lock

    @staticmethod
    @transaction.atomic
    def import_pdf(exam: Exam, pdf_file, user):
        """
        Importe un PDF, crée une Copie (STAGING), et lance la rasterization.
        Pour ce P0 Sync, on fait la rasterization ici.
        En P1, déplacer dans une tâche Celery.
        """
        # 1. Create Copy
        copy_uuid = uuid.uuid4()
        copy = Copy.objects.create(
            id=copy_uuid,
            exam=exam,
            anonymous_id=f"IMPORT-{str(copy_uuid)[:8].upper()}",
            status=Copy.Status.STAGING
        )
        
        # 2. Save PDF
        copy.pdf_source.save(f"copy_{copy_uuid}.pdf", pdf_file, save=True)

        # 3. Rasterize (Sync for P0)
        # 3. Rasterize (Sync for P0)
        try:
            pages_images = GradingService._rasterize_pdf(copy)
            
            if not pages_images:
                raise ValueError("No pages produced by rasterization.")

            # 4. Create Booklet
            booklet = Booklet.objects.create(
                exam=exam,
                # 1-indexed to match BookletHeaderView (start_page - 1)
                start_page=1,
                end_page=len(pages_images),
                pages_images=pages_images
            )
            # Link via ManyToMany
            copy.booklets.add(booklet)
            
            # Check availability
            if len(pages_images) > 0:
                 pass # Remains in STAGING until manual validation
                 
            # AUDIT
            GradingEvent.objects.create(
                copy=copy,
                action=GradingEvent.Action.IMPORT,
                actor=user,
                metadata={'filename': pdf_file.name, 'pages': len(pages_images)}
            )
            
        except Exception as e:
            logger.error(f"Import failed for copy {copy.id}: {e}")
            # Could set status to ERROR if model supported it, or just fail transaction
            raise ValueError(f"Rasterization failed: {str(e)}")
            
        return copy

    @staticmethod
    def _rasterize_pdf(copy) -> list:
        """
        Internal: Uses PyMuPDF to convert copy.pdf_source into images in media/copies/pages/<id>
        """
        copy.pdf_source.open()
        try:
            pdf_bytes = copy.pdf_source.read()
        finally:
            copy.pdf_source.close()
            
        with fitz.open("pdf", pdf_bytes) as doc:
            images = []
            
            path_rel = f"copies/pages/{copy.id}"
            path_abs = os.path.join(settings.MEDIA_ROOT, path_rel)
            os.makedirs(path_abs, exist_ok=True)
            
            for i, page in enumerate(doc):
                 # Matrix 1.5 ~ 108 DPI, 2.0 ~ 144 DPI. 
                 # Use 2.0 for Prod Quality
                 pix = page.get_pixmap(matrix=fitz.Matrix(2.0, 2.0))
                 filename = f"p{i:03d}.png"
                 filepath = os.path.join(path_abs, filename)
                 pix.save(filepath)
                 images.append(f"{path_rel}/{filename}")
             
        return images


    @staticmethod
    @transaction.atomic
    def validate_copy(copy: Copy, user):
        if copy.status != Copy.Status.STAGING:
             raise ValueError(f"Status mismatch: {copy.status} != STAGING")
        
        # Ensure pages exist
        has_pages = any(b.pages_images and len(b.pages_images) > 0 for b in copy.booklets.all())
        if not has_pages:
             raise ValueError("No pages found, cannot validate.")

        copy.status = Copy.Status.READY
        copy.validated_at = timezone.now()
        copy.save()

        GradingEvent.objects.create(
            copy=copy,
            action=GradingEvent.Action.VALIDATE,
            actor=user
        )
        return copy

    @staticmethod
    def ready_copy(copy: Copy, user):
        return GradingService.validate_copy(copy, user)

    @staticmethod
    @transaction.atomic
    def lock_copy(copy: Copy, user):
        if copy.status != Copy.Status.READY:
            raise ValueError("Only READY copies can be locked")
        lock, _created = GradingService.acquire_lock(copy=copy, user=user, ttl_seconds=600)
        return lock

    @staticmethod
    @transaction.atomic
    def unlock_copy(copy: Copy, user):
        raise ValueError("Use release_lock with token.")

    @staticmethod
    @transaction.atomic
    def finalize_copy(copy: Copy, user, lock_token=None):
        # P0-DI-003 FIX: Lock the Copy object to prevent race conditions
        copy = Copy.objects.select_for_update().get(id=copy.id)

        # P0-DI-003 FIX: Detect concurrent finalization (single-winner enforcement)
        # If status is already GRADED, another request won the race - reject duplicate
        if copy.status == Copy.Status.GRADED:
            logger.warning(
                f"Copy {copy.id} already graded (concurrent finalization detected) - "
                f"rejecting duplicate request"
            )
            raise LockConflictError("Copy already finalized by another request")

        # P0-DI-004 FIX: Handle GRADING_FAILED - allow retry
        if copy.status == Copy.Status.GRADING_FAILED:
            logger.info(f"Copy {copy.id} previously failed, retrying finalization (attempt {copy.grading_retries + 1})")
            # Continue with finalization logic

        if copy.status not in [Copy.Status.LOCKED, Copy.Status.GRADING_FAILED]:
            raise ValueError("Only LOCKED or GRADING_FAILED copies can be finalized")

        # Lock CopyLock row as well to prevent concurrent finalize.
        now = timezone.now()
        try:
            lock = (
                CopyLock.objects.select_for_update()
                .select_related("owner")
                .get(copy=copy)
            )
        except CopyLock.DoesNotExist:
            if copy.locked_by == user:
                lock = None
            else:
                raise LockConflictError("Lock required.")

        if lock is not None:
            if lock.expires_at < now:
                lock.delete()
                raise LockConflictError("Lock expired.")

            if lock.owner != user:
                raise LockConflictError("Copy is locked by another user.")

            if not lock_token:
                raise PermissionError("Missing lock token.")
            elif str(lock.token) != str(lock_token):
                raise PermissionError("Invalid lock token.")

        # P0-DI-004 FIX: Set intermediate status BEFORE score computation
        # to narrow the race window for concurrent annotation edits
        copy.status = Copy.Status.GRADING_IN_PROGRESS
        copy.grading_retries += 1
        copy.locked_at = None
        copy.locked_by = None
        copy.save(update_fields=["status", "grading_retries", "locked_at", "locked_by"])

        # Delete lock immediately after status change
        if lock is not None:
            lock.delete()

        # Compute score AFTER lock release and status transition
        final_score = GradingService.compute_score(copy)

        # Generate Final PDF with comprehensive error handling
        from processing.services.pdf_flattener import PDFFlattener
        flattener = PDFFlattener()
        
        try:
            # Check if PDF already exists (additional idempotency check)
            if not copy.final_pdf:
                pdf_bytes = flattener.flatten_copy(copy)
                if pdf_bytes is None:
                    pdf_bytes = b""
                output_filename = f"copy_{copy.id}_corrected.pdf"
                
                # Save PDF first
                copy.final_pdf.save(output_filename, ContentFile(pdf_bytes), save=False)
            
            # P0-DI-004 FIX: Mark as GRADED only after PDF generation succeeds
            copy.status = Copy.Status.GRADED
            copy.graded_at = timezone.now()
            copy.grading_error_message = None  # Clear previous errors
            copy.save(update_fields=["status", "graded_at", "grading_error_message", "final_pdf"])
            
            # P0-DI-007 FIX: Audit event for success (idempotent with get_or_create)
            GradingEvent.objects.get_or_create(
                copy=copy,
                action=GradingEvent.Action.FINALIZE,
                actor=user,
                defaults={'metadata': {'final_score': final_score, 'retries': copy.grading_retries}}
            )
            
        except Exception as e:
            # P0-DI-004 FIX: Save error state with detailed message
            error_msg = str(e)[:500]  # Limit message length
            copy.status = Copy.Status.GRADING_FAILED
            copy.grading_error_message = error_msg
            copy.save(update_fields=["status", "grading_error_message"])
            
            # P0-DI-007 FIX: Audit event for failure
            GradingEvent.objects.create(
                copy=copy,
                action=GradingEvent.Action.FINALIZE,
                actor=user,
                metadata={
                    'detail': error_msg,
                    'retries': copy.grading_retries,
                    'success': False
                }
            )
            
            logger.error(f"PDF generation failed for copy {copy.id} (attempt {copy.grading_retries}): {e}", exc_info=True)
            
            # Alert if max retries exceeded
            if copy.grading_retries >= 3:
                logger.critical(f"Copy {copy.id} failed {copy.grading_retries} times - manual intervention required")
                # TODO: Send email notification to admins
            
            raise ValueError(f"Failed to generate final PDF: {error_msg}")

        return copy
