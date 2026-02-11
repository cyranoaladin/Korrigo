"""
Prometheus metrics for grading workflows.
Conformité: Phase S5-B - Observability (Domain-specific metrics)

Provides domain-specific metrics for diagnostic capabilities:
- Import performance tracking (duration, pages)
- Finalization performance tracking (duration, retries)
- OCR/rasterization error tracking
- Lock conflict monitoring
- Workflow backlog monitoring (copies by status)

Usage:
    from grading.metrics import track_import_duration, track_finalize_duration
    
    with track_import_duration(pages=15, status='success'):
        # Perform import operation
        pass
    
    with track_finalize_duration(retry_attempt=1, status='success'):
        # Perform finalization
        pass
"""
import logging
from contextlib import contextmanager
from prometheus_client import Counter, Histogram, Gauge
from core.prometheus import registry
import time

logger = logging.getLogger(__name__)


# Histogram: Import duration with page bucketing
grading_import_duration_seconds = Histogram(
    'grading_import_duration_seconds',
    'PDF import duration distribution in seconds',
    ['status', 'pages_bucket'],
    buckets=[0.1, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0, 120.0],
    registry=registry
)

# Histogram: Finalize duration with retry attempt tracking
grading_finalize_duration_seconds = Histogram(
    'grading_finalize_duration_seconds',
    'PDF finalization duration distribution in seconds',
    ['status', 'retry_attempt'],
    buckets=[0.1, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0, 120.0],
    registry=registry
)

# Counter: OCR/rasterization errors
grading_ocr_errors_total = Counter(
    'grading_ocr_errors_total',
    'Total OCR/rasterization errors encountered',
    ['error_type'],
    registry=registry
)

# Counter: Lock conflicts
grading_lock_conflicts_total = Counter(
    'grading_lock_conflicts_total',
    'Total lock conflicts encountered',
    ['conflict_type'],
    registry=registry
)

# Gauge: Copies by status (workflow backlog monitoring)
grading_copies_by_status = Gauge(
    'grading_copies_by_status',
    'Current count of copies by status',
    ['status'],
    registry=registry
)


def _get_pages_bucket(pages):
    """
    Classify page count into buckets for metrics cardinality control.
    
    Args:
        pages (int): Number of pages in the PDF
    
    Returns:
        str: Bucket label (1-10, 11-50, 51-100, 100+)
    
    Examples:
        >>> _get_pages_bucket(5)
        '1-10'
        >>> _get_pages_bucket(25)
        '11-50'
        >>> _get_pages_bucket(75)
        '51-100'
        >>> _get_pages_bucket(150)
        '100+'
    """
    if pages <= 10:
        return '1-10'
    elif pages <= 50:
        return '11-50'
    elif pages <= 100:
        return '51-100'
    else:
        return '100+'


@contextmanager
def track_import_duration(pages, status):
    """
    Context manager to track PDF import duration metrics.
    
    Args:
        pages (int): Number of pages in the PDF
        status (str): Import status ('success' or 'failed')
    
    Usage:
        with track_import_duration(pages=15, status='success'):
            # Perform import operation
            pdf_data = rasterize_pdf(file)
    
    Note:
        This context manager catches all exceptions to ensure metrics
        recording never breaks import processing. Exceptions are re-raised
        after recording the metric.
    """
    start_time = time.time()
    pages_bucket = _get_pages_bucket(pages)
    
    try:
        yield
    except Exception:
        # Record failure metric before re-raising
        duration = time.time() - start_time
        try:
            grading_import_duration_seconds.labels(
                status='failed',
                pages_bucket=pages_bucket
            ).observe(duration)
        except Exception as e:
            logger.warning(f"Failed to record import failure metric: {e}", exc_info=True)
        raise
    else:
        # Record success metric
        duration = time.time() - start_time
        try:
            grading_import_duration_seconds.labels(
                status=status,
                pages_bucket=pages_bucket
            ).observe(duration)
        except Exception as e:
            logger.warning(f"Failed to record import success metric: {e}", exc_info=True)


@contextmanager
def track_finalize_duration(retry_attempt, status):
    """
    Context manager to track PDF finalization duration metrics.
    
    Args:
        retry_attempt (int): Current retry attempt number (1-indexed)
        status (str): Finalization status ('success' or 'failed')
    
    Usage:
        with track_finalize_duration(retry_attempt=1, status='success'):
            # Perform finalization operation
            final_pdf = flatten_copy(copy)
    
    Note:
        This context manager catches all exceptions to ensure metrics
        recording never breaks finalization processing. Exceptions are
        re-raised after recording the metric.
    """
    start_time = time.time()
    
    # Bucket retry attempts to control cardinality
    if retry_attempt >= 3:
        retry_bucket = '3+'
    else:
        retry_bucket = str(retry_attempt)
    
    try:
        yield
    except Exception:
        # Record failure metric before re-raising
        duration = time.time() - start_time
        try:
            grading_finalize_duration_seconds.labels(
                status='failed',
                retry_attempt=retry_bucket
            ).observe(duration)
        except Exception as e:
            logger.warning(f"Failed to record finalize failure metric: {e}", exc_info=True)
        raise
    else:
        # Record success metric
        duration = time.time() - start_time
        try:
            grading_finalize_duration_seconds.labels(
                status=status,
                retry_attempt=retry_bucket
            ).observe(duration)
        except Exception as e:
            logger.warning(f"Failed to record finalize success metric: {e}", exc_info=True)
