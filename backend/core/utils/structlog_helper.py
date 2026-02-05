"""
Structlog Helper for Korrigo
Phase 4: Enhanced Structured Logging

This module provides convenient wrappers for structured logging with context.
Use this instead of standard Python logging for better observability.

Example usage:

    from core.utils.structlog_helper import get_logger

    logger = get_logger(__name__)

    # Basic logging
    logger.info("copy_graded", copy_id=copy.id, score=score)

    # With context binding
    logger = logger.bind(exam_id=exam.id, user_id=request.user.id)
    logger.info("grading_started")
    logger.info("grading_completed", duration_ms=elapsed_time)

    # Error logging
    try:
        risky_operation()
    except Exception as e:
        logger.exception("operation_failed", error=str(e))
"""
import structlog
from typing import Any, Dict, Optional


def get_logger(name: Optional[str] = None) -> structlog.BoundLogger:
    """
    Get a structured logger instance.

    Args:
        name: Logger name (usually __name__ from calling module)

    Returns:
        Bound logger with JSON output in production, pretty console in dev

    Example:
        logger = get_logger(__name__)
        logger.info("user_login", user_id=123, ip=request.META.get('REMOTE_ADDR'))
    """
    if name:
        return structlog.get_logger(name)
    return structlog.get_logger()


def log_task_start(logger: structlog.BoundLogger, task_name: str, **context) -> structlog.BoundLogger:
    """
    Log the start of a Celery task with context.

    Args:
        logger: Structlog logger instance
        task_name: Name of the task
        **context: Additional context (task_id, copy_id, etc.)

    Returns:
        Logger with bound context for subsequent logs

    Example:
        logger = get_logger(__name__)
        logger = log_task_start(logger, "async_flatten_copy", copy_id=copy.id)
        # ... do work ...
        logger.info("task_completed", duration_ms=elapsed)
    """
    logger = logger.bind(task=task_name, **context)
    logger.info("task_started")
    return logger


def log_task_end(logger: structlog.BoundLogger, task_name: str, success: bool = True, **context) -> None:
    """
    Log the completion of a Celery task.

    Args:
        logger: Structlog logger instance (with bound context from log_task_start)
        task_name: Name of the task
        success: Whether task succeeded
        **context: Additional context (duration_ms, result_count, etc.)

    Example:
        log_task_end(logger, "async_flatten_copy", success=True, duration_ms=5432.1)
    """
    if success:
        logger.info("task_completed", **context)
    else:
        logger.error("task_failed", **context)


def log_api_request(
    logger: structlog.BoundLogger,
    method: str,
    path: str,
    user_id: Optional[int] = None,
    **context
) -> structlog.BoundLogger:
    """
    Log an API request with context.

    Args:
        logger: Structlog logger instance
        method: HTTP method (GET, POST, etc.)
        path: Request path
        user_id: Authenticated user ID (if any)
        **context: Additional context

    Returns:
        Logger with bound request context

    Example:
        logger = get_logger(__name__)
        logger = log_api_request(logger, "POST", "/api/exams/", user_id=request.user.id)
        # ... handle request ...
        logger.info("request_completed", status_code=200, duration_ms=123.4)
    """
    ctx = {
        "http_method": method,
        "http_path": path,
    }
    if user_id:
        ctx["user_id"] = user_id
    ctx.update(context)

    logger = logger.bind(**ctx)
    logger.info("api_request_received")
    return logger


def log_database_operation(
    logger: structlog.BoundLogger,
    operation: str,
    model: str,
    **context
) -> None:
    """
    Log a significant database operation.

    Args:
        logger: Structlog logger instance
        operation: Operation type (create, update, delete, bulk_create)
        model: Model name (Exam, Copy, Student, etc.)
        **context: Additional context (count, ids, etc.)

    Example:
        log_database_operation(
            logger,
            "bulk_create",
            "Student",
            count=150,
            duration_ms=234.5
        )
    """
    logger.info(
        "database_operation",
        operation=operation,
        model=model,
        **context
    )


def log_security_event(
    logger: structlog.BoundLogger,
    event_type: str,
    user_id: Optional[int] = None,
    ip_address: Optional[str] = None,
    success: bool = True,
    **context
) -> None:
    """
    Log a security-related event (authentication, authorization, etc.).

    Args:
        logger: Structlog logger instance
        event_type: Type of security event (login, logout, unauthorized_access, etc.)
        user_id: User ID if applicable
        ip_address: Client IP address
        success: Whether the action succeeded
        **context: Additional context

    Example:
        log_security_event(
            logger,
            "login_attempt",
            user_id=123,
            ip_address="192.168.1.100",
            success=True
        )
    """
    ctx = {
        "event_type": event_type,
        "success": success,
    }
    if user_id:
        ctx["user_id"] = user_id
    if ip_address:
        ctx["ip_address"] = ip_address
    ctx.update(context)

    log_level = "info" if success else "warning"
    getattr(logger, log_level)("security_event", **ctx)


def log_performance_metric(
    logger: structlog.BoundLogger,
    metric_name: str,
    value: float,
    unit: str = "ms",
    **context
) -> None:
    """
    Log a performance metric.

    Args:
        logger: Structlog logger instance
        metric_name: Name of the metric (query_duration, task_duration, etc.)
        value: Metric value
        unit: Unit of measurement (ms, seconds, count, bytes, etc.)
        **context: Additional context

    Example:
        log_performance_metric(
            logger,
            "ocr_duration",
            5432.1,
            unit="ms",
            copy_id=copy.id
        )
    """
    logger.info(
        "performance_metric",
        metric=metric_name,
        value=value,
        unit=unit,
        **context
    )


# Convenience function for common logging patterns
def log_operation(
    operation: str,
    logger_name: Optional[str] = None,
    **context
) -> None:
    """
    Quick logging for simple operations.

    Args:
        operation: Operation name/description
        logger_name: Logger name (default: None for root logger)
        **context: Context to log

    Example:
        log_operation("copy_graded", copy_id=copy.id, score=18.5, corrector_id=user.id)
    """
    logger = get_logger(logger_name)
    logger.info(operation, **context)
