"""
Login Lockout Middleware - R4 Security Fix

Implements account lockout after N failed login attempts using Django cache.
Works with django-ratelimit for IP-based rate limiting.
"""
import hashlib
import logging
from django.core.cache import cache
from django.conf import settings

logger = logging.getLogger(__name__)

LOCKOUT_THRESHOLD = getattr(settings, 'LOGIN_LOCKOUT_THRESHOLD', 5)
LOCKOUT_DURATION = getattr(settings, 'LOGIN_LOCKOUT_DURATION', 900)  # 15 minutes


def _get_lockout_key(username: str) -> str:
    """Generate cache key for lockout tracking."""
    username_hash = hashlib.sha256(username.lower().encode()).hexdigest()[:16]
    return f"login_lockout:{username_hash}"


def _get_attempts_key(username: str) -> str:
    """Generate cache key for failed attempts counter."""
    username_hash = hashlib.sha256(username.lower().encode()).hexdigest()[:16]
    return f"login_attempts:{username_hash}"


def is_locked_out(username: str) -> bool:
    """Check if account is currently locked out."""
    if not username:
        return False
    key = _get_lockout_key(username)
    return cache.get(key) is not None


def get_remaining_lockout_time(username: str) -> int:
    """Get remaining lockout time in seconds."""
    if not username:
        return 0
    key = _get_lockout_key(username)
    ttl = cache.ttl(key) if hasattr(cache, 'ttl') else LOCKOUT_DURATION
    return max(0, ttl) if cache.get(key) else 0


def record_failed_attempt(username: str) -> int:
    """
    Record a failed login attempt.
    Returns the current attempt count.
    """
    if not username:
        return 0
    
    attempts_key = _get_attempts_key(username)
    lockout_key = _get_lockout_key(username)
    
    attempts = cache.get(attempts_key, 0) + 1
    cache.set(attempts_key, attempts, timeout=LOCKOUT_DURATION)
    
    if attempts >= LOCKOUT_THRESHOLD:
        cache.set(lockout_key, True, timeout=LOCKOUT_DURATION)
        logger.warning(
            f"Account locked out after {attempts} failed attempts",
            extra={
                'username_hash': hashlib.sha256(username.lower().encode()).hexdigest()[:8],
                'attempts': attempts,
                'lockout_duration': LOCKOUT_DURATION
            }
        )
    
    return attempts


def clear_failed_attempts(username: str) -> None:
    """Clear failed attempts after successful login."""
    if not username:
        return
    
    attempts_key = _get_attempts_key(username)
    lockout_key = _get_lockout_key(username)
    
    cache.delete(attempts_key)
    cache.delete(lockout_key)
