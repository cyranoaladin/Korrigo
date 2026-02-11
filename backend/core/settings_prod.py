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
        "CONN_MAX_AGE": int(os.environ.get("DB_CONN_MAX_AGE", "60")),
    }
}

SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

SECURE_HSTS_SECONDS = int(os.environ.get("SECURE_HSTS_SECONDS", "31536000"))
SECURE_HSTS_INCLUDE_SUBDOMAINS = os.environ.get("SECURE_HSTS_INCLUDE_SUBDOMAINS", "true").lower() == "true"
SECURE_HSTS_PRELOAD = os.environ.get("SECURE_HSTS_PRELOAD", "true").lower() == "true"

LOG_LEVEL = os.environ.get("DJANGO_LOG_LEVEL", "INFO")
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "default": {
            "format": "%(asctime)s %(levelname)s %(name)s %(message)s",
        }
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "default",
        }
    },
    "root": {
        "handlers": ["console"],
        "level": LOG_LEVEL,
    },
}
