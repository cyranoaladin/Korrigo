"""
Phase 2: Async Celery tasks for student operations
Prevents blocking HTTP requests during bulk imports
"""
from celery import shared_task
import os
import logging

logger = logging.getLogger('students')


@shared_task(bind=True, max_retries=2, default_retry_delay=30)
def async_import_students(self, csv_path, user_id=None):
    """
    Async student import from CSV file

    Phase 2 Fix: Moves bulk CSV import to background worker
    - Prevents blocking HTTP requests for large CSV files (1000+ students)
    - Handles file I/O and database writes in background

    Args:
        csv_path: Path to uploaded CSV file
        user_id: ID of user performing import (for audit trail)

    Returns:
        dict: {'status': str, 'created': int, 'updated': int, 'errors': list}
    """
    try:
        from students.models import Student
        from students.services.csv_import import import_students_from_csv, CsvReadError

        logger.info(f"Starting async student import from {csv_path}")

        if not os.path.exists(csv_path):
            return {
                'status': 'error',
                'detail': f'CSV file not found: {csv_path}'
            }

        try:
            # Import students
            result = import_students_from_csv(csv_path, Student)

            logger.info(
                f"Student import completed: "
                f"created={result.created}, updated={result.updated}, "
                f"skipped={result.skipped}, errors={len(result.errors)}"
            )

            response = {
                'status': 'success',
                'created': result.created,
                'updated': result.updated,
                'skipped': result.skipped,
                'errors': [
                    {'row': e.row, 'message': e.message}
                    for e in result.errors[:10]  # Limit to first 10 errors
                ],
                'total_errors': len(result.errors),
                'attempt': self.request.retries + 1
            }

            # Include generated passwords if any
            if hasattr(result, 'passwords') and result.passwords:
                response['passwords'] = result.passwords
                response['message'] = (
                    'Import successful. IMPORTANT: Save generated passwords '
                    'and communicate them securely to students.'
                )

            return response

        except CsvReadError as e:
            logger.error(f"CSV read error during import: {e}")
            return {
                'status': 'error',
                'detail': str(e)
            }

        finally:
            # Clean up temp file
            try:
                if os.path.exists(csv_path):
                    os.remove(csv_path)
                    logger.info(f"Cleaned up temp file: {csv_path}")
            except Exception as e:
                logger.warning(f"Failed to clean up {csv_path}: {e}")

    except Exception as exc:
        logger.error(
            f"Async student import failed for {csv_path} "
            f"(attempt {self.request.retries + 1}/2): {exc}",
            exc_info=True
        )

        return {
            'status': 'error',
            'detail': str(exc)
        }


@shared_task
def async_bulk_create_users(student_ids):
    """
    Bulk create User accounts for students without accounts

    Phase 2: Helps with initial setup when importing existing student lists

    Args:
        student_ids: List of Student IDs to create users for

    Returns:
        dict: {'created': int, 'skipped': int, 'errors': list}
    """
    from students.models import Student
    from django.contrib.auth import get_user_model

    User = get_user_model()
    created = 0
    skipped = 0
    errors = []

    logger.info(f"Bulk creating users for {len(student_ids)} students")

    for student_id in student_ids:
        try:
            student = Student.objects.get(id=student_id)

            if student.user:
                skipped += 1
                continue

            # Create user with email as username
            if not student.email:
                errors.append({'student_id': str(student_id), 'error': 'No email'})
                continue

            user = User.objects.create_user(
                username=student.email,
                email=student.email,
                first_name=student.first_name,
                last_name=student.last_name
            )

            student.user = user
            student.save()
            created += 1

        except Student.DoesNotExist:
            errors.append({'student_id': str(student_id), 'error': 'Student not found'})
        except Exception as e:
            errors.append({'student_id': str(student_id), 'error': str(e)})

    logger.info(f"Bulk user creation: created={created}, skipped={skipped}, errors={len(errors)}")

    return {
        'created': created,
        'skipped': skipped,
        'errors': errors[:10]  # Limit errors
    }
