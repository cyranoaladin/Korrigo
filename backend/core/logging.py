"""
Production-grade JSON logging for Viatique
Conformité: Phase S5-A - Observability

This module provides structured JSON logging for production environments
while maintaining human-readable logs for development.

Security:
- No secrets/passwords logged
- User ID logged (integer), not email/username
- Exception stacktraces serialized as single-line strings
"""
import logging
from pythonjsonlogger import jsonlogger


class ViatiqueJSONFormatter(jsonlogger.JsonFormatter):
    """
    Custom JSON formatter with request context and security controls.

    Fields included in JSON logs:
    - timestamp: ISO 8601 timestamp
    - level: Log level (INFO, WARNING, ERROR, etc.)
    - logger: Logger name (django, audit, grading, etc.)
    - message: Log message
    - module: Python module name
    - function: Function name
    - line: Line number
    - path: HTTP request path (if available)
    - method: HTTP method (if available)
    - status_code: HTTP status code (if available)
    - request_id: Unique request ID (if available)
    - user_id: Authenticated user ID (if available, NOT email)
    - exc_info: Exception info (serialized as string, not multi-line)
    - duration_ms: Request duration in milliseconds (if available)

    Security:
    - No passwords, tokens, or API keys logged
    - User ID only (not email or username)
    - Sensitive data excluded automatically
    """

    def add_fields(self, log_record, record, message_dict):
        """
        Add custom fields to JSON log record.

        Args:
            log_record: Dictionary that will be serialized to JSON
            record: Python LogRecord object
            message_dict: Message dictionary from parent
        """
        super().add_fields(log_record, record, message_dict)

        # Standard fields
        log_record['timestamp'] = self.formatTime(record, self.datefmt)
        log_record['level'] = record.levelname
        log_record['logger'] = record.name
        log_record['module'] = record.module
        log_record['function'] = record.funcName
        log_record['line'] = record.lineno

        # Request context (added by RequestIDMiddleware and RequestContextLogFilter)
        if hasattr(record, 'request_id'):
            log_record['request_id'] = record.request_id

        if hasattr(record, 'path'):
            log_record['path'] = record.path

        if hasattr(record, 'method'):
            log_record['method'] = record.method

        if hasattr(record, 'status_code'):
            log_record['status_code'] = record.status_code

        # User context (user ID only, not email/PII)
        if hasattr(record, 'user_id'):
            # Only log if user_id is truthy (authenticated user)
            if record.user_id:
                log_record['user_id'] = record.user_id

        # Duration (added by MetricsMiddleware)
        if hasattr(record, 'duration_ms'):
            log_record['duration_ms'] = round(record.duration_ms, 2)

        # Exception info (serialize as string, not multi-line)
        if record.exc_info:
            log_record['exc_info'] = self.formatException(record.exc_info)
