"""
ZF-AUD-13: Cache utilities for performance optimization
Provides caching for frequently accessed data to reduce DB load.
"""
from django.core.cache import cache
from django.conf import settings
import logging

logger = logging.getLogger('grading')

# Cache timeouts (seconds)
CACHE_TIMEOUT_SHORT = 60  # 1 minute
CACHE_TIMEOUT_MEDIUM = 300  # 5 minutes
CACHE_TIMEOUT_LONG = 3600  # 1 hour

# Sentinel value to distinguish "cached None" from "cache miss"
CACHED_NONE = "__CACHED_NONE__"


def get_exam_stats(exam_id: str) -> dict:
    """
    Get cached exam statistics (copy counts by status).

    Args:
        exam_id: UUID of the exam

    Returns:
        dict with copy counts by status
    """
    cache_key = f"exam:{exam_id}:stats"
    stats = cache.get(cache_key, default=None)

    if stats == CACHED_NONE:
        return None

    if stats is None:
        from exams.models import Copy

        stats = {
            'total': Copy.objects.filter(exam_id=exam_id).count(),
            'staging': Copy.objects.filter(exam_id=exam_id, status=Copy.Status.STAGING).count(),
            'ready': Copy.objects.filter(exam_id=exam_id, status=Copy.Status.READY).count(),
            'locked': Copy.objects.filter(exam_id=exam_id, status=Copy.Status.LOCKED).count(),
            'graded': Copy.objects.filter(exam_id=exam_id, status=Copy.Status.GRADED).count(),
        }

        if stats is None:
            cache.set(cache_key, CACHED_NONE, timeout=CACHE_TIMEOUT_SHORT)
        else:
            cache.set(cache_key, stats, timeout=CACHE_TIMEOUT_SHORT)
        logger.debug(f"Cached exam stats for {exam_id}")

    return stats


def invalidate_exam_stats(exam_id: str):
    """Invalidate exam stats cache when copy status changes."""
    cache_key = f"exam:{exam_id}:stats"
    cache.delete(cache_key)
    logger.debug(f"Invalidated exam stats cache for {exam_id}")


def get_copy_annotation_count(copy_id: str) -> int:
    """
    Get cached annotation count for a copy.

    Args:
        copy_id: UUID of the copy

    Returns:
        int: Number of annotations
    """
    cache_key = f"copy:{copy_id}:ann_count"
    count = cache.get(cache_key, default=None)

    if count == CACHED_NONE:
        return None

    if count is None:
        from grading.models import Annotation

        count = Annotation.objects.filter(copy_id=copy_id).count()

        if count is None:
            cache.set(cache_key, CACHED_NONE, timeout=CACHE_TIMEOUT_SHORT)
        else:
            cache.set(cache_key, count, timeout=CACHE_TIMEOUT_SHORT)

    return count


def invalidate_copy_annotation_count(copy_id: str):
    """Invalidate annotation count cache when annotations change."""
    cache_key = f"copy:{copy_id}:ann_count"
    cache.delete(cache_key)


def get_user_assigned_copies_count(user_id: int) -> int:
    """
    Get cached count of copies assigned to a corrector.

    Args:
        user_id: ID of the user

    Returns:
        int: Number of assigned copies
    """
    cache_key = f"user:{user_id}:assigned_count"
    count = cache.get(cache_key, default=None)

    if count == CACHED_NONE:
        return None

    if count is None:
        from exams.models import Copy

        count = Copy.objects.filter(
            assigned_corrector_id=user_id,
            status__in=[Copy.Status.READY, Copy.Status.LOCKED]
        ).count()

        if count is None:
            cache.set(cache_key, CACHED_NONE, timeout=CACHE_TIMEOUT_SHORT)
        else:
            cache.set(cache_key, count, timeout=CACHE_TIMEOUT_SHORT)

    return count


def invalidate_user_assigned_copies(user_id: int):
    """Invalidate assigned copies cache when assignment changes."""
    cache_key = f"user:{user_id}:assigned_count"
    cache.delete(cache_key)


def get_grading_structure(exam_id: str) -> dict:
    """
    Get cached grading structure for an exam.

    Args:
        exam_id: UUID of the exam

    Returns:
        dict: Grading structure or empty dict
    """
    cache_key = f"exam:{exam_id}:grading_structure"
    structure = cache.get(cache_key, default=None)

    if structure == CACHED_NONE:
        return None

    if structure is None:
        from exams.models import Exam

        try:
            exam = Exam.objects.get(id=exam_id)
            structure = exam.grading_structure or {}
        except Exam.DoesNotExist:
            structure = {}

        if structure is None:
            cache.set(cache_key, CACHED_NONE, timeout=CACHE_TIMEOUT_LONG)
        else:
            cache.set(cache_key, structure, timeout=CACHE_TIMEOUT_LONG)

    return structure


def invalidate_grading_structure(exam_id: str):
    """Invalidate grading structure cache when exam is updated."""
    cache_key = f"exam:{exam_id}:grading_structure"
    cache.delete(cache_key)


# Cache decorator for expensive operations
def cached_result(timeout: int = CACHE_TIMEOUT_MEDIUM):
    """
    Decorator to cache function results.

    Usage:
        @cached_result(timeout=300)
        def expensive_computation(arg1, arg2):
            ...
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            # Create cache key from function name and arguments
            key_parts = [func.__name__] + [str(a) for a in args]
            key_parts += [f"{k}={v}" for k, v in sorted(kwargs.items())]
            cache_key = ":".join(key_parts)

            result = cache.get(cache_key, default=None)

            if result == CACHED_NONE:
                return None

            if result is None:
                result = func(*args, **kwargs)
                if result is None:
                    cache.set(cache_key, CACHED_NONE, timeout=timeout)
                else:
                    cache.set(cache_key, result, timeout=timeout)

            return result
        return wrapper
    return decorator
