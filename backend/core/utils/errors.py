from django.conf import settings
import logging

logger = logging.getLogger(__name__)

def safe_error_response(exception, context="Operation", user_message=None):
    """
    Return safe error response that doesn't leak internal details.
    
    P1.4 FIX: Prevents information disclosure via error messages
    
    - Production: Generic message
    - Development: Full exception details
    - Always log full exception for debugging
    
    Args:
        exception: The caught exception
        context: Description of the operation (e.g., "PDF processing")
        user_message: Optional custom user-facing message
        
    Returns:
        dict: Safe error response suitable for API response
    """
    logger.error(f"{context} failed: {exception}", exc_info=True)
    
    if settings.DEBUG:
        return {"error": f"{context} failed: {str(exception)}"}
    else:
        return {
            "error": user_message or f"{context} failed. Please contact support.",
            "error_code": "INTERNAL_ERROR"
        }
