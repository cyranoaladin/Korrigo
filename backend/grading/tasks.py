"""
P0-OP-03: Async Celery tasks for heavy PDF operations
Prevents worker starvation and request timeouts
"""
from celery import shared_task
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.mail import send_mail
from django.db import transaction
import os
import logging

# P0-OP-03: Module-level imports required for test patching
from grading.questionnaire_bilan import generate_questionnaire_bilan
from grading.services import GradingService, LockConflictError
from grading.pdf_processor import PDFProcessor
from exams.models import Copy, Exam
from core.utils.audit import redact_log_value

logger = logging.getLogger('grading')
User = get_user_model()


@shared_task
def generate_questionnaire_bilan_task(force=False):
    return generate_questionnaire_bilan(force=force)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def notify_students_results_released(self, exam_id: str):
    """Envoie un email aux élèves ayant une copie FINALIZED pour cet examen."""
    exam = Exam.objects.get(id=exam_id)
    copies = Copy.objects.filter(
        exam=exam,
        status=Copy.Status.FINALIZED,
        student__isnull=False,
        student__email__isnull=False,
    ).select_related('student')

    sent = 0
    errors = []
    login_url = getattr(
        settings,
        'STUDENT_PORTAL_URL',
        'https://korrigo.labomaths.tn/student/login',
    )

    for copy in copies:
        student = copy.student
        if not student or not student.email:
            continue

        try:
            send_mail(
                subject=f"[Korrigo] Vos résultats pour {exam.name} sont disponibles",
                message=(
                    f"Bonjour {student.first_name},\n\n"
                    f"Vos résultats pour l'examen « {exam.name} » sont maintenant disponibles "
                    f"sur votre espace élève.\n\n"
                    f"Connectez-vous sur {login_url}\n\n"
                    f"L'équipe Korrigo"
                ),
                from_email=settings.SERVER_EMAIL,
                recipient_list=[student.email],
                fail_silently=False,
            )
            sent += 1
        except Exception as exc:  # pragma: no cover
            safe_error = redact_log_value(str(exc))
            logger.warning(
                "Failed to notify student for exam release",
                extra={
                    'exam_id': str(exam.id),
                    'student_id': student.id,
                    'student_identifier': '<redacted-email>',
                    'error_message': safe_error,
                },
            )
            errors.append(safe_error)

    return {'sent': sent, 'errors': errors}


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def async_finalize_copy(self, copy_id, user_id, lock_token=None, request_id=None):
    """
    Async PDF finalization with automatic retry

    P0-OP-03 FIX: Moves PDF flattening to background worker
    - Prevents blocking HTTP requests (90s+ operations)
    - Automatic retry on transient failures (3 attempts)
    - Proper error state management

    Args:
        copy_id: UUID of the Copy to finalize
        user_id: ID of the user performing finalization
        lock_token: Lock token for verification
        request_id: Optional request ID for log correlation

    Returns:
        dict: {'copy_id': str, 'status': str, 'final_score': int}

    Raises:
        Retry exception on transient failures (max 3 attempts)
    """
    extra = {'request_id': request_id} if request_id else {}

    # Non-retryable: missing data
    try:
        copy = Copy.objects.get(id=copy_id)
    except Copy.DoesNotExist:
        logger.error(f"Copy {copy_id} not found", extra=extra)
        return {
            'copy_id': str(copy_id),
            'status': 'error',
            'detail': f'Copy {copy_id} not found'
        }

    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        logger.error(f"User {user_id} not found", extra=extra)
        return {
            'copy_id': str(copy_id),
            'status': 'error',
            'detail': f'User {user_id} not found'
        }

    logger.info(f"Starting async finalization for copy {copy_id} by user {user_id}", extra=extra)

    try:
        finalized_copy = GradingService.finalize_copy(copy, user, lock_token=lock_token)

        final_score = GradingService.compute_score(finalized_copy)
        logger.info(f"Successfully finalized copy {copy_id} with score {final_score}", extra=extra)

        return {
            'copy_id': str(copy_id),
            'status': 'success',
            'final_score': final_score,
            'attempt': self.request.retries + 1
        }

    except (ValueError, LockConflictError) as exc:
        # Non-retryable business errors (status mismatch, lock conflict, etc.)
        logger.warning(
            f"Async finalization rejected for copy {copy_id}: {exc}",
            extra=extra
        )
        return {
            'copy_id': str(copy_id),
            'status': 'error',
            'detail': str(exc)
        }

    except Exception as exc:
        # LOT 4: Transient failures → use Celery retry mechanism
        logger.error(
            f"Async finalization failed for copy {copy_id} "
            f"(attempt {self.request.retries + 1}/3): {exc}",
            exc_info=True,
            extra=extra
        )
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def async_import_pdf(self, exam_id, pdf_path, user_id, anonymous_id, request_id=None):
    """
    Async PDF import with rasterization

    P0-OP-03 FIX: Moves PDF rasterization to background worker
    - Prevents blocking HTTP requests during upload
    - Handles large PDFs (50+ pages) without timeout

    Args:
        exam_id: UUID of the Exam
        pdf_path: Temporary path to uploaded PDF file
        user_id: ID of the uploading user
        anonymous_id: Anonymous ID for the copy
        request_id: Optional request ID for log correlation

    Returns:
        dict: {'copy_id': str, 'status': str, 'pages': int}
    """
    try:
        exam = Exam.objects.get(id=exam_id)
        user = User.objects.get(id=user_id)

        extra = {'request_id': request_id} if request_id else {}
        logger.info(f"Starting async PDF import for exam {exam_id}, file {pdf_path}", extra=extra)

        # Open the uploaded file
        if not os.path.exists(pdf_path):
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")

        with open(pdf_path, 'rb') as pdf_file:
            # This will create Copy, rasterize pages, create Booklet
            copy = PDFProcessor.import_pdf(exam, pdf_file, user, anonymous_id=anonymous_id)

        # Get page count
        booklets = copy.booklets.all()
        total_pages = sum(len(b.pages_images) for b in booklets if b.pages_images)

        extra = {'request_id': request_id} if request_id else {}
        logger.info(f"Successfully imported copy {copy.id} with {total_pages} pages", extra=extra)

        # Clean up temporary file
        try:
            os.remove(pdf_path)
        except Exception as e:
            extra = {'request_id': request_id} if request_id else {}
            logger.warning(f"Failed to clean up temp file {pdf_path}: {e}", extra=extra)

        return {
            'copy_id': str(copy.id),
            'status': 'success',
            'pages': total_pages,
            'attempt': self.request.retries + 1
        }

    except Exception as exc:
        extra = {'request_id': request_id} if request_id else {}
        logger.error(
            f"Async PDF import failed for exam {exam_id} "
            f"(attempt {self.request.retries + 1}/3): {exc}",
            exc_info=True,
            extra=extra
        )

        # Return error dict for tests
        return {
            'status': 'error',
            'detail': str(exc)
        }


@shared_task
def cleanup_orphaned_files():
    """
    Periodic task to clean up orphaned PDF files and images
    
    P0-OP-03: Prevents disk exhaustion from failed operations
    Should be run periodically (e.g., daily via Celery Beat)
    """
    from django.conf import settings
    from exams.models import Copy
    import os
    from datetime import datetime, timedelta
    
    logger.info("Starting orphaned file cleanup")
    
    removed_count = 0
    # Find files older than 24 hours in temp upload directory
    temp_dir = os.path.join(settings.MEDIA_ROOT, 'temp_uploads')
    if os.path.exists(temp_dir):
        cutoff_time = datetime.now().timestamp() - (24 * 3600)
        
        for filename in os.listdir(temp_dir):
            filepath = os.path.join(temp_dir, filename)
            file_mtime = os.path.getmtime(filepath)
            if file_mtime < cutoff_time:
                try:
                    os.remove(filepath)
                    removed_count += 1
                except Exception as e:
                    logger.error(f"Failed to remove orphaned file {filepath}: {e}", exc_info=True)
        
        logger.info(f"Cleaned up {removed_count} orphaned temp files")
    
    # TODO: Clean up orphaned page images (pages with no corresponding Copy)
    
    return {'removed_count': removed_count}


@shared_task
def cleanup_expired_locks():
    """
    LOT 9: Periodic task to clean up expired CopyLock entries.
    Prevents stale locks from blocking editors after session abandonment.
    Should be run every 5 minutes via Celery Beat.
    """
    from grading.models import CopyLock
    from django.utils import timezone

    now = timezone.now()
    expired = CopyLock.objects.filter(expires_at__lte=now)
    count = expired.count()
    if count > 0:
        expired.delete()
        logger.info(f"Cleaned up {count} expired CopyLock entries")
    return {'deleted': count}


@shared_task
def run_copy_integrity_audit():
    """
    Periodic guardrail for critical grading invariants.

    Runs the integrity command in fail-fast mode so Celery Beat logs a hard
    failure whenever FINALIZED copies or released results drift into an invalid
    state.
    """
    try:
        call_command("check_copy_integrity", fail_on_issues=True)
        logger.info("Copy integrity audit completed without issues")
        return {"status": "ok"}
    except SystemExit as exc:
        exit_code = exc.code if isinstance(exc.code, int) else 1
        logger.error("Copy integrity audit detected issues", extra={"exit_code": exit_code})
        return {"status": "issues_detected", "exit_code": exit_code}


@shared_task
def purge_old_audit_logs(retention_days=365):
    """
    LOT 9 RGPD: Purge AuditLog entries older than retention_days.
    Default: 365 days (1 year). Conformité RGPD — minimisation des données.
    Should be run daily via Celery Beat.
    """
    from core.models import AuditLog
    from django.utils import timezone
    import datetime

    cutoff = timezone.now() - datetime.timedelta(days=retention_days)
    old_entries = AuditLog.objects.filter(timestamp__lt=cutoff)
    count = old_entries.count()
    if count > 0:
        old_entries.delete()
        logger.info(f"Purged {count} AuditLog entries older than {retention_days} days")
    return {'purged': count, 'cutoff': cutoff.isoformat()}


@shared_task
def update_copy_status_metrics():
    """
    Periodic task to update grading_copies_by_status gauge
    
    Observability: Tracks workflow backlog by monitoring copy counts per status
    Should be run every 60 seconds via Celery Beat
    
    Returns:
        dict: Status counts for verification
    """
    from django.db.models import Count
    from grading.metrics import grading_copies_by_status
    
    try:
        status_counts = Copy.objects.values('status').annotate(count=Count('id'))
        
        counts_dict = {}
        for item in status_counts:
            status = item['status']
            count = item['count']
            counts_dict[status] = count
            
            try:
                grading_copies_by_status.labels(status=status).set(count)
            except Exception as e:
                logger.warning(f"Failed to update gauge for status {status}: {e}", exc_info=True)
        
        logger.debug(f"Updated copy status metrics: {counts_dict}")
        return {'status_counts': counts_dict}
        
    except Exception as exc:
        logger.error(f"Failed to update copy status metrics: {exc}", exc_info=True)
        return {'detail': str(exc)}
