"""
Error Handling Utilities
P1.4: Prevent information disclosure in error messages
"""
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


def safe_error_response(exception, context="Operation", user_message=None):
    """
    Return safe error response that doesn't leak internal details.
    
    - Production: Generic message only
    - Development: Full exception details for debugging
    - Always log full exception for investigation
    
    Args:
        exception: The caught exception
        context: Context string (e.g., "PDF processing")
        user_message: Optional user-friendly message override
        
    Returns:
        dict: Safe error response
    """
    # Always log full exception for debugging (secure logs)
    logger.error(f"{context} failed: {exception}", exc_info=True)
    
    if settings.DEBUG:
        # Development: show details for debugging
        return {"error": f"{context} failed: {str(exception)}"}
    else:
        # Production: generic message, no internal details
        return {
            "error": user_message or f"{context} failed. Please contact support.",
            "error_code": "INTERNAL_ERROR"
        }


def safe_error_message(exception, context="Operation", user_message=None):
    """
    Return safe error message string (without dict wrapper).
    
    For backward compatibility with code that returns error strings directly.
    """
    logger.error(f"{context} failed: {exception}", exc_info=True)
    
    if settings.DEBUG:
        return f"{context} failed: {str(exception)}"
    else:
        return user_message or f"{context} failed. Please contact support."
