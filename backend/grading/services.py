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
from grading.models import Annotation, GradingEvent
from exams.models import Copy, Booklet, Exam
import logging

logger = logging.getLogger(__name__)


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
    def add_annotation(copy: Copy, payload: dict, user):
        if copy.status != Copy.Status.READY:
            raise ValueError(f"Cannot annotate copy in status {copy.status}")

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
    def update_annotation(annotation: Annotation, payload: dict, user):
        if annotation.copy.status != Copy.Status.READY:
            raise ValueError(f"Cannot update annotation in copy status {annotation.copy.status}")

        # Basic ownership check (if not enforced by Permission class)
        # But Service usually enforces invariant logic, permissions enforce access.
        # We'll rely on View permissions for Owner check, but invariant logic here.
        
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

        annotation.save()

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
    def delete_annotation(annotation: Annotation, user):
        if annotation.copy.status != Copy.Status.READY:
             raise ValueError(f"Cannot delete annotation in copy status {annotation.copy.status}")

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
    def compute_score(copy: Copy) -> int:
        total = 0
        for annotation in copy.annotations.all():
            if annotation.score_delta is not None:
                total += annotation.score_delta
        return total

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

        copy.status = Copy.Status.LOCKED
        copy.locked_at = timezone.now()
        copy.locked_by = user
        copy.save()

        GradingEvent.objects.create(
            copy=copy,
            action=GradingEvent.Action.LOCK,
            actor=user
        )
        return copy

    @staticmethod
    @transaction.atomic
    def unlock_copy(copy: Copy, user):
        if copy.status != Copy.Status.LOCKED:
            raise ValueError("Only LOCKED copies can be unlocked")

        previous_locker = copy.locked_by.username if copy.locked_by else "unknown"

        copy.status = Copy.Status.READY
        copy.locked_at = None
        copy.locked_by = None
        copy.save()

        GradingEvent.objects.create(
            copy=copy,
            action=GradingEvent.Action.UNLOCK,
            actor=user,
            metadata={'previous_locker': previous_locker}
        )
        return copy

    @staticmethod
    @transaction.atomic
    def finalize_copy(copy: Copy, user):
        if copy.status not in [Copy.Status.LOCKED, Copy.Status.READY]:
            raise ValueError("Only LOCKED or READY copies can be finalized")

        final_score = GradingService.compute_score(copy)

        # Generate Final PDF
        from processing.services.pdf_flattener import PDFFlattener
        flattener = PDFFlattener()
        try:
             flattener.flatten_copy(copy)
        except Exception as e:
             logger.error(f"Flattten failed: {e}")
             raise ValueError(f"Failed to generate final PDF: {e}")

        copy.status = Copy.Status.GRADED
        copy.graded_at = timezone.now()
        copy.save()

        GradingEvent.objects.create(
            copy=copy,
            action=GradingEvent.Action.FINALIZE,
            actor=user,
            metadata={'final_score': final_score}
        )
        return copy
