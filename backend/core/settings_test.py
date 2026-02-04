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

# Force development mode for tests to avoid production checks
os.environ['DJANGO_ENV'] = 'development'
os.environ.setdefault('DEBUG', 'True')

from .settings import *

try:
    import dj_database_url
except Exception:
    dj_database_url = None

raw_suffix = os.environ.get("CI_NODE_INDEX") or os.environ.get("PYTEST_XDIST_WORKER") or "0"
# Normalize suffix for CI/xdist (e.g., "gw0") and avoid unexpected chars
DB_SUFFIX = "".join(ch for ch in str(raw_suffix) if ch.isalnum() or ch in "_").lower() or "0"

DATABASES['default']['CONN_MAX_AGE'] = 0
DATABASES['default']['TEST'] = {
    'NAME': f'test_viatique_{DB_SUFFIX}',
    'SERIALIZE': False, # Prevent IntegrityErrors in django_content_type
}

database_url = os.environ.get("DATABASE_URL")
if database_url and dj_database_url is not None:
    DATABASES['default'] = dj_database_url.parse(database_url)
    DATABASES['default']['CONN_MAX_AGE'] = 0
    DATABASES['default']['TEST'] = {
        'NAME': f'test_viatique_{DB_SUFFIX}',
        'SERIALIZE': False,
    }

# Faster password hashing for tests
PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.MD5PasswordHasher',
]

# Ensure we are in test mode
DEBUG = False
CELERY_TASK_ALWAYS_EAGER = True

# Disable rate limiting in tests (django-ratelimit)
# This allows login tests to work without Redis and without hitting rate limits
RATELIMIT_ENABLE = False

# Disable login lockout in tests to allow multiple failed login attempts
LOGIN_LOCKOUT_THRESHOLD = 9999  # Effectively disabled
