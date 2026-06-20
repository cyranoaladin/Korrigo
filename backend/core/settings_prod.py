import os

from .settings import *  # noqa: F403


def _get_required_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise ValueError(f"{name} environment variable must be set")
    return value


DJANGO_ENV = "production"
DEBUG = False

SECRET_KEY = _get_required_env("SECRET_KEY")
_INSECURE_PREFIXES = ("django-insecure-", "CHANGE_ME", "CHANGE_THIS")
if any(SECRET_KEY.startswith(p) for p in _INSECURE_PREFIXES):
    raise ValueError(
        "SECRET_KEY looks like a placeholder. "
        "Generate a real key with: python -c \"from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())\""
    )

DJANGO_ALLOWED_HOSTS = os.environ.get("DJANGO_ALLOWED_HOSTS", "")
ALLOWED_HOSTS = [h.strip() for h in DJANGO_ALLOWED_HOSTS.split(",") if h.strip()]
if not ALLOWED_HOSTS:
    raise ValueError("DJANGO_ALLOWED_HOSTS must be set (comma-separated)")

DB_NAME = _get_required_env("DB_NAME")
DB_USER = _get_required_env("DB_USER")
DB_PASSWORD = _get_required_env("DB_PASSWORD")
DB_HOST = _get_required_env("DB_HOST")
DB_PORT = _get_required_env("DB_PORT")

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": DB_NAME,
        "USER": DB_USER,
        "PASSWORD": DB_PASSWORD,
        "HOST": DB_HOST,
        "PORT": DB_PORT,
        "CONN_MAX_AGE": int(os.environ.get("DB_CONN_MAX_AGE", "600")),
    }
}

# P1.2: Protection timeouts (aligné avec settings.py base)
DATABASES['default']['OPTIONS'] = {
    'connect_timeout': 10,
    'options': '-c lock_timeout=5000 -c statement_timeout=30000 -c idle_in_transaction_session_timeout=60000',
}
DATABASES['default']['CONN_HEALTH_CHECKS'] = True

# Guardrail for explicit one-shot import/seed commands only.
# Production backend/celery runtime must not carry DEFAULT_PASSWORD permanently;
# if an operator provides it for a provisioning command, keep blocking trivial
# values at settings load time before any import can create accounts.
_TRIVIAL_PASSWORDS = ('passe123', 'password', '123456', 'changeme', '')
if DEFAULT_PASSWORD and DEFAULT_PASSWORD in _TRIVIAL_PASSWORDS:  # noqa: F405
    raise ValueError(
        "DEFAULT_PASSWORD must be set to a non-trivial value in production. "
        "Use a one-shot import/seed secret, not the runtime environment."
    )

# Respect SSL_ENABLED from base settings (CI runs HTTP-only with SSL_ENABLED=false)
_ssl_enabled = os.environ.get("SSL_ENABLED", "true").lower() == "true"
SESSION_COOKIE_SECURE = _ssl_enabled
CSRF_COOKIE_SECURE = _ssl_enabled
if _ssl_enabled:
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

SECURE_HSTS_SECONDS = int(os.environ.get("SECURE_HSTS_SECONDS", "31536000"))
SECURE_HSTS_INCLUDE_SUBDOMAINS = os.environ.get("SECURE_HSTS_INCLUDE_SUBDOMAINS", "true").lower() == "true"
SECURE_HSTS_PRELOAD = os.environ.get("SECURE_HSTS_PRELOAD", "true").lower() == "true"

# Session: 8h par défaut, renouvelée à chaque requête active
SESSION_COOKIE_AGE = int(os.environ.get('SESSION_COOKIE_AGE', 28800))  # 8h
SESSION_SAVE_EVERY_REQUEST = True

# P1.1: Extend inherited LOGGING from settings.py instead of overwriting it.
# This preserves audit_file, file handlers, json formatter, and request_context filters.
import copy
LOG_LEVEL = os.environ.get("DJANGO_LOG_LEVEL", "INFO")
LOGGING = copy.deepcopy(LOGGING)  # noqa: F405
LOGGING['root']['level'] = LOG_LEVEL
# Force JSON formatter on all handlers in production (except mail_admins)
for _handler_name, _handler_config in LOGGING['handlers'].items():
    if _handler_name != 'mail_admins':
        _handler_config['formatter'] = 'json'
