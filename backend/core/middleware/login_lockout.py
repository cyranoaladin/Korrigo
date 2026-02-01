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


def _refresh_attempts_ttl(key: str) -> None:
    """
    Refresh TTL on attempts key after incr() to ensure LOCKOUT_DURATION is maintained.

    cache.incr() may not preserve TTL on some backends, so we explicitly refresh it.
    Uses multiple fallback strategies for compatibility.
    """
    try:
        # Method 1: Django's cache.touch() (most portable)
        result = cache.touch(key, timeout=LOCKOUT_DURATION)
        if result:
            return
    except (AttributeError, NotImplementedError):
        pass

    # Method 2: django-redis direct expire (if available)
    try:
        from django_redis import get_redis_connection
        conn = get_redis_connection("default")
        conn.expire(key, LOCKOUT_DURATION)
        return
    except (ImportError, Exception):
        pass

    # No safe fallback: get/set would cause race conditions (overwrite concurrent incr)
    # Best effort: log warning and accept that TTL may not be refreshed on unsupported backends
    logger.warning(
        "Cache backend does not support TTL refresh (touch/expire unavailable). "
        "Lockout window may be inconsistent on this backend.",
        extra={'key': key, 'backend': type(cache).__name__}
    )


def record_failed_attempt(username: str) -> int:
    """
    Record a failed login attempt (atomic increment).
    Returns the current attempt count.
    """
    if not username:
        return 0

    attempts_key = _get_attempts_key(username)
    lockout_key = _get_lockout_key(username)

    # Atomic increment to prevent race conditions
    try:
        attempts = cache.incr(attempts_key)
        # CRITICAL: Refresh TTL after incr() to maintain LOCKOUT_DURATION window
        _refresh_attempts_ttl(attempts_key)
    except ValueError:
        # Key doesn't exist yet, initialize it
        cache.set(attempts_key, 1, timeout=LOCKOUT_DURATION)
        attempts = 1

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
