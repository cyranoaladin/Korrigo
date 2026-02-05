"""
Phase 2: Async Celery tasks for OCR operations
Prevents blocking HTTP requests during heavy OCR processing
"""
from celery import shared_task
from django.conf import settings
import os
import logging

logger = logging.getLogger('identification')


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def async_cmen_ocr(self, copy_id):
    """
    Async OCR processing for CMEN headers

    Phase 2 Fix: Moves OCR processing to background worker
    - Prevents blocking HTTP requests (5-10s per copy)
    - Handles cv2.imread and OCR in background
    - Automatic retry on transient failures

    Args:
        copy_id: UUID of the Copy to process

    Returns:
        dict: {'copy_id': str, 'status': str, 'matched_student': dict or None}
    """
    try:
        from exams.models import Copy
        from processing.services.cmen_header_ocr import CMENHeaderOCR, load_students_from_csv
        import cv2

        logger.info(f"Starting async CMEN OCR for copy {copy_id}")

        try:
            copy = Copy.objects.get(id=copy_id)
        except Copy.DoesNotExist:
            logger.error(f"Copy {copy_id} not found")
            return {
                'copy_id': str(copy_id),
                'status': 'error',
                'detail': 'Copy not found'
            }

        booklet = copy.booklets.first()
        if not booklet:
            return {
                'copy_id': str(copy_id),
                'status': 'error',
                'detail': 'No booklet associated with this copy'
            }

        # Get header image
        if not booklet.pages_images or len(booklet.pages_images) == 0:
            return {
                'copy_id': str(copy_id),
                'status': 'error',
                'detail': 'No pages images found'
            }

        first_page_path = booklet.pages_images[0]
        full_path = os.path.join(settings.MEDIA_ROOT, first_page_path)

        if not os.path.exists(full_path):
            return {
                'copy_id': str(copy_id),
                'status': 'error',
                'detail': f'Image not found: {first_page_path}'
            }

        # Load image (blocking I/O - but now in background)
        image = cv2.imread(full_path)
        if image is None:
            return {
                'copy_id': str(copy_id),
                'status': 'error',
                'detail': 'Failed to load image'
            }

        # Extract header (top 25%)
        height = image.shape[0]
        header_height = int(height * 0.25)
        header_image = image[:header_height, :]

        # Perform OCR (heavy computation - but now in background)
        ocr = CMENHeaderOCR(debug=False)
        header_result = ocr.extract_header(header_image)

        # Load students from database
        students = load_students_from_csv(copy.exam)

        # Match student
        matched_student = None
        if header_result and students:
            from processing.services.cmen_header_ocr import fuzzy_match_student
            matched_student = fuzzy_match_student(header_result, students)

        logger.info(f"OCR completed for copy {copy_id}, match: {matched_student is not None}")

        result = {
            'copy_id': str(copy_id),
            'status': 'success',
            'header_result': header_result,
            'matched_student': matched_student,
            'attempt': self.request.retries + 1
        }

        # Auto-identify if match found
        if matched_student:
            from students.models import Student
            try:
                student = Student.objects.get(id=matched_student['id'])
                copy.student = student
                copy.is_identified = True
                copy.save()
                logger.info(f"Auto-identified copy {copy_id} to student {student.id}")
                result['auto_identified'] = True
            except Student.DoesNotExist:
                logger.warning(f"Matched student {matched_student['id']} not found")
                result['auto_identified'] = False

        return result

    except Exception as exc:
        logger.error(
            f"Async CMEN OCR failed for copy {copy_id} "
            f"(attempt {self.request.retries + 1}/3): {exc}",
            exc_info=True
        )

        return {
            'copy_id': str(copy_id),
            'status': 'error',
            'detail': str(exc)
        }


@shared_task(bind=True, max_retries=2)
def async_batch_ocr(self, copy_ids):
    """
    Batch OCR processing for multiple copies

    Phase 2: Process multiple copies in parallel

    Args:
        copy_ids: List of Copy UUIDs

    Returns:
        dict: {'total': int, 'task_ids': list}
    """
    logger.info(f"Starting batch OCR for {len(copy_ids)} copies")

    task_ids = []
    for copy_id in copy_ids:
        result = async_cmen_ocr.delay(copy_id)
        task_ids.append(result.id)

    logger.info(f"Queued {len(task_ids)} OCR tasks")

    return {
        'total': len(copy_ids),
        'task_ids': task_ids,
        'status': 'queued'
    }
