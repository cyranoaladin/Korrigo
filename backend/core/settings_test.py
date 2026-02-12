import sys
import os
import warnings

"""
Test settings hardening:
- Keep warnings strict in pytest.ini (error) with a single targeted ignore there.
- Add a *minimal* fallback ignore here, in case the warning is emitted during early
  Django settings initialization (before pytest warning filters fully apply).
"""
try:
    from django.utils.deprecation import RemovedInDjango50Warning
    warnings.filterwarnings(
        "ignore",
        message=r".*SERIALIZE test database setting is deprecated.*",
        category=RemovedInDjango50Warning,
    )
except Exception:
    # If Django isn't importable yet, do not broaden ignores.
    pass

from .settings import *

try:
    import dj_database_url
except Exception:
    dj_database_url = None

raw_suffix = os.environ.get("CI_NODE_INDEX") or os.environ.get("PYTEST_XDIST_WORKER") or "0"
# Normalize suffix for CI/xdist (e.g., "gw0") and avoid unexpected chars
DB_SUFFIX = "".join(ch for ch in str(raw_suffix) if ch.isalnum() or ch in "_").lower() or "0"

# Force SQLite in-memory for local tests (no Docker PostgreSQL dependency)
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
        'TEST': {
            'NAME': ':memory:',
        },
    }
}

# Faster password hashing for tests
PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.MD5PasswordHasher',
]

# Ensure we are in test mode
DEBUG = False
CELERY_TASK_ALWAYS_EAGER = True

# Disable security redirects that break test client (HTTP → HTTPS redirect causes 301)
SECURE_SSL_REDIRECT = False
SECURE_HSTS_SECONDS = 0
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False

# Allow test client host
ALLOWED_HOSTS = ['*']

# Force LocMemCache in tests (base settings uses Redis when REDIS_HOST is set)
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'test-cache',
    }
}

# Force simple DB session engine (cached_db requires working cache backend)
SESSION_ENGINE = 'django.contrib.sessions.backends.db'

# Disable rate limiting in tests (django-ratelimit)
# This allows login tests to work without Redis and without hitting rate limits
RATELIMIT_ENABLE = False
