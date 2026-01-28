"""
Request ID middleware for request correlation
Conformité: Phase S5-A - Observability

This module provides unique request IDs for every HTTP request,
enabling log correlation across multiple log lines for the same request.

Features:
- Generates UUID4 for each request
- Accepts client-provided request ID (for distributed tracing)
- Adds X-Request-ID header to response
- Makes request ID available to loggers via thread-local storage
"""
import uuid
import logging
import threading
from django.utils.deprecation import MiddlewareMixin


# Thread-local storage for request context
# Used to make request ID available to loggers without passing it explicitly
_thread_locals = threading.local()


def get_current_request_id():
    """
    Get current request ID from thread-local storage.

    Returns:
        str: Request ID (UUID4 string) if available, None otherwise
    """
    return getattr(_thread_locals, 'request_id', None)


def get_current_request():
    """
    Get current request object from thread-local storage.

    Returns:
        HttpRequest: Current request object if available, None otherwise
    """
    return getattr(_thread_locals, 'request', None)


class RequestIDMiddleware(MiddlewareMixin):
    """
    Middleware to generate and attach unique request ID to every request.

    Workflow:
    1. process_request: Generate or accept request ID, store in thread-local
    2. View processing: Request ID available to all loggers
    3. process_response: Add X-Request-ID header to response
    4. Cleanup: Remove request ID from thread-local storage

    Thread Safety:
    - Uses thread-local storage (threading.local())
    - Each request thread has its own request_id
    - No race conditions or leakage between requests
    """

    def process_request(self, request):
        """
        Generate request ID at start of request.

        Checks for client-provided request ID first (HTTP_X_REQUEST_ID header).
        If not provided, generates new UUID4.

        Args:
            request: Django HttpRequest object

        Returns:
            None (continues middleware chain)
        """
        # Check if request ID provided by client (useful for distributed tracing)
        request_id = request.META.get('HTTP_X_REQUEST_ID')

        if not request_id:
            # Generate new UUID4
            request_id = str(uuid.uuid4())

        # Store in request object (accessible in views)
        request.request_id = request_id

        # Store in thread-local storage (accessible by loggers)
        _thread_locals.request_id = request_id
        _thread_locals.request = request

        return None

    def process_response(self, request, response):
        """
        Add request ID to response headers.

        Args:
            request: Django HttpRequest object
            response: Django HttpResponse object

        Returns:
            HttpResponse: Response with X-Request-ID header
        """
        if hasattr(request, 'request_id'):
            response['X-Request-ID'] = request.request_id

        # Clean up thread-local storage
        self._cleanup_thread_locals()

        return response

    def process_exception(self, request, exception):
        """
        Ensure thread-local cleanup on exception.

        Args:
            request: Django HttpRequest object
            exception: Exception that was raised

        Returns:
            None (exception handled by Django)
        """
        self._cleanup_thread_locals()
        return None

    @staticmethod
    def _cleanup_thread_locals():
        """
        Clean up thread-local storage.

        Removes request_id and request from thread-local storage
        to prevent memory leaks and cross-request contamination.
        """
        if hasattr(_thread_locals, 'request_id'):
            delattr(_thread_locals, 'request_id')

        if hasattr(_thread_locals, 'request'):
            delattr(_thread_locals, 'request')


class RequestContextLogFilter(logging.Filter):
    """
    Logging filter to add request context to all log records.

    Automatically adds the following fields to every log record:
    - request_id: Unique request ID (if available)
    - path: HTTP request path (if available)
    - method: HTTP method (if available)
    - user_id: Authenticated user ID (if available, NOT email)

    This filter works with RequestIDMiddleware to inject request context
    into logs without requiring explicit extra={} in every log call.

    Thread Safety:
    - Reads from thread-local storage
    - Safe for multi-threaded Django applications
    """

    def filter(self, record):
        """
        Add request context to log record.

        Args:
            record: Python LogRecord object

        Returns:
            bool: True (always passes filter, just enriches record)
        """
        # Add request ID from thread-local storage
        request_id = get_current_request_id()
        if request_id:
            record.request_id = request_id

        # Add request context (path, method, user_id)
        request = get_current_request()
        if request:
            # Add path and method
            if hasattr(request, 'path'):
                record.path = request.path

            if hasattr(request, 'method'):
                record.method = request.method

            # Add user ID (if authenticated)
            # SECURITY: User ID only (integer), not email or username
            if hasattr(request, 'user') and request.user.is_authenticated:
                record.user_id = request.user.id
            else:
                record.user_id = None

        return True
