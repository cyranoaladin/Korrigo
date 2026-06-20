import os
import sys
import dj_database_url
from pathlib import Path
from dotenv import load_dotenv
import tempfile
from urllib.parse import quote

BASE_DIR = Path(__file__).resolve().parent.parent

# Load environment variables from .env files.
# Order matters (python-dotenv does not override existing env vars by default):
# 1) repo root `.env` (docker-compose/project config)
# 2) `backend/.env` (backend-specific overrides, e.g. LLM gateway config)
load_dotenv(BASE_DIR.parent / '.env')
load_dotenv(BASE_DIR / '.env')

# Security: No dangerous defaults in production
SECRET_KEY = os.environ.get("SECRET_KEY")
DJANGO_ENV = os.environ.get("DJANGO_ENV", "development")

if not SECRET_KEY:
    if DJANGO_ENV == "production":
        raise ValueError("SECRET_KEY environment variable must be set in production")
    # Development fallback only
    SECRET_KEY = "django-insecure-dev-only-" + "x" * 50

# Patch A: Secure DEBUG
# Logic:
# - If production: DEBUG must be False. If explicitly set to True -> Error.
# - If dev: DEBUG depends on env, default True.

raw_debug = os.environ.get("DEBUG", "True").lower() == "true"

if DJANGO_ENV == "production":
    if raw_debug:
         raise ValueError("CRITICAL: DEBUG must be False in production (DJANGO_ENV=production).")
    DEBUG = False
else:
    DEBUG = raw_debug

# Optional student provisioning default password.
# Production runtime must not carry a standing initial student password; explicit
# import/seed commands may provide DEFAULT_PASSWORD only for that one-shot run.
DEFAULT_PASSWORD = os.environ.get('DEFAULT_PASSWORD')
if DEFAULT_PASSWORD is None:
    DEFAULT_PASSWORD = '' if DJANGO_ENV == "production" else 'Korrigo_Default_Pwd_2026!'

# Helper for CSV environment variables
def csv_env(name: str, default: str = "") -> list:
    """Parse comma-separated environment variable."""
    v = os.environ.get(name, default).strip()
    return [x.strip() for x in v.split(",") if x.strip()]

# ALLOWED_HOSTS: Explicit configuration required
ALLOWED_HOSTS = csv_env("ALLOWED_HOSTS", "localhost,127.0.0.1")
if "*" in ALLOWED_HOSTS and DJANGO_ENV == "production":
    raise ValueError("ALLOWED_HOSTS cannot contain '*' in production")

# CSRF & CORS Configuration (prod-like safe)
CSRF_TRUSTED_ORIGINS = csv_env(
    "CSRF_TRUSTED_ORIGINS",
    "http://localhost:8088,http://127.0.0.1:8088"
)

CORS_ALLOWED_ORIGINS = csv_env(
    "CORS_ALLOWED_ORIGINS",
    "http://localhost:8088,http://localhost:5173"
)

# Cookie settings for E2E/prod-like
SESSION_COOKIE_SAMESITE = os.environ.get("SESSION_COOKIE_SAMESITE", "Lax")
CSRF_COOKIE_SAMESITE = os.environ.get("CSRF_COOKIE_SAMESITE", "Lax")

# In real prod behind TLS, set via env; in local-prod-like keep false
SESSION_COOKIE_SECURE = (
    DJANGO_ENV == 'production'  # toujours Secure en prod
    or os.environ.get("SESSION_COOKIE_SECURE", "false").lower() == "true"
)
CSRF_COOKIE_SECURE = (
    DJANGO_ENV == 'production'  # toujours Secure en prod (miroir de SESSION_COOKIE_SECURE)
    or os.environ.get("CSRF_COOKIE_SECURE", "false").lower() == "true"
)

# Static & Media Files
STATIC_URL = os.environ.get("STATIC_URL", "/static/").strip() or "/static/"
STATIC_ROOT = Path(os.environ.get("STATIC_ROOT", "")).expanduser() if os.environ.get("STATIC_ROOT") else (BASE_DIR / "staticfiles")

MEDIA_URL = os.environ.get("MEDIA_URL", "/media/").strip() or "/media/"
MEDIA_ROOT = Path(os.environ.get("MEDIA_ROOT", "")).expanduser() if os.environ.get("MEDIA_ROOT") else (BASE_DIR / "media")

# File Upload Limits (Mission 5.1)
# Allow large PDF uploads (up to 100MB)
DATA_UPLOAD_MAX_MEMORY_SIZE = 104857600  # 100 MB
FILE_UPLOAD_MAX_MEMORY_SIZE = 104857600  # 100 MB

# E2E Testing Configuration
E2E_SEED_TOKEN = os.environ.get("E2E_SEED_TOKEN")  # Only set in prod-like environment

# LLM Providers (OpenAI / OpenAI-compatible gateways)
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "").strip()
OPENAI_BASE_URL = os.environ.get("OPENAI_BASE_URL", "").strip()

AI_PROVIDER_URL = os.environ.get("AI_PROVIDER_URL", "").strip()
AI_PROVIDER_KEY = os.environ.get("AI_PROVIDER_KEY", "").strip()
AI_MODEL_NAME = os.environ.get("AI_MODEL_NAME", "").strip()

BILAN_LLM_DEFAULT = os.environ.get("BILAN_LLM_DEFAULT", "").strip() or AI_MODEL_NAME or "gpt-4o-mini"
BILAN_LLM_PREMIUM = os.environ.get("BILAN_LLM_PREMIUM", "").strip() or AI_MODEL_NAME or "gpt-4o"

# RAG (retrieval-only) endpoint for bilan prompts
RAG_URL = os.environ.get("RAG_URL", "http://ingestor:8001").strip()
RAG_TOKEN = os.environ.get("RAG_TOKEN", "").strip()

# Optional fallback: allow using local Ollama for Bilan generation when no API provider is configured.
# This remains opt-in to keep "fail-closed" behavior by default.
BILAN_ALLOW_OLLAMA_FALLBACK = os.environ.get("BILAN_ALLOW_OLLAMA_FALLBACK", "").strip().lower() == "true"
# Separate model override for bilans (production may not have the default OLLAMA_MODEL pulled).
BILAN_OLLAMA_MODEL = os.environ.get("BILAN_OLLAMA_MODEL", "").strip()

# Bilan RAG requirement:
# - Production should fail closed if RAG is unavailable (prevents generic/hallucinated analysis).
# - Development can override via BILAN_REQUIRE_RAG=true/false.
_raw_require_rag = os.environ.get("BILAN_REQUIRE_RAG", "").strip()
if _raw_require_rag:
    BILAN_REQUIRE_RAG = _raw_require_rag.lower() == "true"
else:
    BILAN_REQUIRE_RAG = DJANGO_ENV == "production"

# LLM / Ollama Configuration
OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://ollama:11434")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "llama3.2:latest")
OLLAMA_TIMEOUT = int(os.environ.get("OLLAMA_TIMEOUT", "300"))

# Prometheus Metrics Configuration (S5-B)
# METRICS_TOKEN: Required token for /metrics endpoint authentication in production.
# - Development (DEBUG=True): No authentication required
# - Production (DEBUG=False): Token required via X-Metrics-Token header or ?token= query param
METRICS_TOKEN = os.environ.get("METRICS_TOKEN")

# Enforce METRICS_TOKEN for production HTTP processes. The Docker entrypoint
# runs management commands for every container, and Celery imports Django
# settings but does not expose /metrics or receive HTTP-only secrets.
_IS_CELERY_PROCESS = any(arg == "celery" or arg.endswith("/celery") for arg in sys.argv)
_IS_MANAGEMENT_COMMAND = any(arg.endswith("manage.py") for arg in sys.argv)
if (
    DJANGO_ENV == "production"
    and not METRICS_TOKEN
    and not _IS_CELERY_PROCESS
    and not _IS_MANAGEMENT_COMMAND
):
    raise ValueError(
        "METRICS_TOKEN environment variable must be set in production. "
        "The /metrics endpoint must not be publicly accessible. "
        "Set METRICS_TOKEN in your .env file or deployment secrets "
        "(generate with: python -c \"import secrets; print(secrets.token_urlsafe(32))\")."
    )

# Security Settings for Production
# SSL/HTTPS Configuration
# SSL_ENABLED: Set to "False" in prod-like (HTTP-only E2E), "True" in real prod
SSL_ENABLED = os.environ.get("SSL_ENABLED", "False").lower() == "true"

if not DEBUG:
    # Production Security Headers
    if SSL_ENABLED:
        # Real production: Force HTTPS
        SECURE_SSL_REDIRECT = True
        SESSION_COOKIE_SECURE = True
        CSRF_COOKIE_SECURE = True
        SECURE_HSTS_SECONDS = 31536000
        SECURE_HSTS_INCLUDE_SUBDOMAINS = True
        SECURE_HSTS_PRELOAD = True
        SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
        # Exempt health check paths from SSL redirect (Docker internal probes use HTTP)
        SECURE_REDIRECT_EXEMPT = [r'^api/health/']
    else:
        # Prod-like (E2E): HTTP-only, no SSL redirect
        SECURE_SSL_REDIRECT = False
        SESSION_COOKIE_SECURE = False
        CSRF_COOKIE_SECURE = False

    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    X_FRAME_OPTIONS = 'DENY'
else:
    # Development: Cookies not secure (HTTP localhost)
    SESSION_COOKIE_SECURE = False
    CSRF_COOKIE_SECURE = False

# CSRF_COOKIE_HTTPONLY must be False for SPAs to read CSRF token from cookie
CSRF_COOKIE_HTTPONLY = False



INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'drf_spectacular',
    'corsheaders',
    'csp',
    'core',
    'exams',
    'grading',
    'processing',
    'students',
    'identification',
    'bilan',
]

# Django REST Framework Configuration
# Security: Default Deny - All endpoints require explicit authentication
REST_FRAMEWORK = {
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',  # Default: authenticated only
    ],
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.SessionAuthentication',
        # LOT 3: BasicAuthentication removed (plaintext credentials risk)
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 50,
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
}


MIDDLEWARE = [
    'core.middleware.request_id.RequestIDMiddleware',  # S5-A: Request ID for log correlation
    'core.middleware.metrics.MetricsMiddleware',
    'csp.middleware.CSPMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'core.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]


WSGI_APPLICATION = 'core.wsgi.application'

# Database Configuration
def _build_db_config_from_parts():
    required = ("DB_NAME", "DB_USER", "DB_PASSWORD", "DB_HOST", "DB_PORT")
    if not all(os.environ.get(name) for name in required):
        return None

    return {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ["DB_NAME"],
        "USER": os.environ["DB_USER"],
        "PASSWORD": os.environ["DB_PASSWORD"],
        "HOST": os.environ["DB_HOST"],
        "PORT": os.environ["DB_PORT"],
        "CONN_MAX_AGE": int(os.environ.get("DB_CONN_MAX_AGE", "600")),
    }


db_config = None
database_url = os.environ.get("DATABASE_URL")

if database_url:
    # Always prioritize DATABASE_URL if present when it is valid.
    try:
        db_config = dj_database_url.config(conn_max_age=600)
    except ValueError:
        db_config = _build_db_config_from_parts()
        if db_config is None:
            raise
elif os.environ.get("DJANGO_ENV") == "production":
    db_config = _build_db_config_from_parts()

if db_config is not None:
    # P0-OP-04: Add database lock timeout protection
    if db_config.get('ENGINE') == 'django.db.backends.postgresql':
        db_config['OPTIONS'] = {
            'connect_timeout': 10,
            'options': '-c lock_timeout=5000 -c statement_timeout=30000 -c idle_in_transaction_session_timeout=60000'
        }
        db_config['CONN_HEALTH_CHECKS'] = True

    DATABASES = {'default': db_config}
elif DEBUG:
    # Development fallback to SQLite
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }
else:
    raise ValueError("DATABASES: No DATABASE_URL found in production-like environment.")






AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
        'OPTIONS': {
            'min_length': 12,
        }
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# P3-E FIX: Use cached_db sessions only when Redis is available (cross-worker).
# Fallback to plain db sessions when running with LocMemCache to avoid
# sessions being invisible between Gunicorn workers.
_REDIS_AVAILABLE = bool(os.environ.get("REDIS_HOST"))
SESSION_ENGINE = (
    'django.contrib.sessions.backends.cached_db' if _REDIS_AVAILABLE
    else 'django.contrib.sessions.backends.db'
)
SESSION_COOKIE_AGE = 3600  # 1 hour — reduced from 4h to limit stolen-session exposure
SESSION_EXPIRE_AT_BROWSER_CLOSE = False  # BUG-13 FIX: Évite que la session expire brutalement sur les navigateurs mobiles
SESSION_COOKIE_HTTPONLY = True

# P1.1 FIX: Ensure logs directory exists *and is writable* before configuring logging.
# In some environments (containers / restored workspaces), `backend/logs` can be
# owned by a different user (e.g. dnsmasq) and become read-only for the app user,
# which breaks *all* Django commands at startup (logging config happens in
# `django.setup()`).
LOGS_DIR = os.path.join(BASE_DIR, 'logs')
try:
    os.makedirs(LOGS_DIR, exist_ok=True)
    _probe = os.path.join(LOGS_DIR, '.write_probe')
    with open(_probe, 'a', encoding='utf-8'):
        pass
    try:
        os.remove(_probe)
    except OSError:
        pass
except Exception:
    # Safe fallback for dev / CI: always writable.
    # NOTE: use tempfile.gettempdir() to avoid hardcoding /tmp (Bandit B108).
    LOGS_DIR = os.path.join(tempfile.gettempdir(), 'korrigo_logs')
    os.makedirs(LOGS_DIR, exist_ok=True)

# S5-A: Environment-specific formatter selection
# Production: JSON logs for parsing by log aggregation tools
# Development: Human-readable logs for developer convenience
LOG_FORMATTER = 'json' if not DEBUG else 'verbose'

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '[{asctime}] {levelname} {name} {module} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
        'json': {
            # S5-A: Structured JSON logs for production
            '()': 'core.logging.ViatiqueJSONFormatter',
            'format': '%(timestamp)s %(level)s %(logger)s %(message)s',
        },
    },
    'filters': {
        'request_context': {
            # S5-A: Inject request context (request_id, path, method, user_id) into logs
            '()': 'core.middleware.request_id.RequestContextLogFilter',
        },
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': LOG_FORMATTER,  # Dynamic: verbose or json based on DEBUG
            'filters': ['request_context'],
        },
        'file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': os.path.join(LOGS_DIR, 'django.log'),
            'maxBytes': 10485760,  # 10MB
            'backupCount': 10,
            'formatter': LOG_FORMATTER,
            'filters': ['request_context'],
        },
        'audit_file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': os.path.join(LOGS_DIR, 'audit.log'),
            'maxBytes': 10485760,  # 10MB
            'backupCount': 10,
            'formatter': LOG_FORMATTER,
            'filters': ['request_context'],
        },
    },
    'loggers': {
        'django': {
            'handlers': ['console', 'file'],
            'level': os.environ.get('DJANGO_LOG_LEVEL', 'INFO'),
        },
        'audit': {
            'handlers': ['console', 'audit_file'],
            'level': 'INFO',
            'propagate': False,
        },
        'grading': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
        },
        'metrics': {
            'handlers': ['console', 'file'],
            'level': 'WARNING',
        },
        'django.security': {
            'handlers': ['console', 'file'],
            'level': 'WARNING',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    }
}

LANGUAGE_CODE = 'fr-fr'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True
# STATIC_URL is defined at the top
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

def build_redis_url(
    *,
    host: str,
    port: str,
    db: str,
    password: str | None = None,
) -> str:
    if password:
        return f"redis://:{quote(password, safe='')}@{host}:{port}/{db}"
    return f"redis://{host}:{port}/{db}"


_REDIS_PASSWORD = os.environ.get("REDIS_PASSWORD", "")
CELERY_BROKER_URL = os.environ.get(
    "CELERY_BROKER_URL",
    build_redis_url(host="redis", port="6379", db="0", password=_REDIS_PASSWORD),
)
CELERY_RESULT_BACKEND = os.environ.get(
    "CELERY_RESULT_BACKEND",
    build_redis_url(host="redis", port="6379", db="0", password=_REDIS_PASSWORD),
)
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = 'UTC'
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 300
CELERY_TASK_SOFT_TIME_LIMIT = 270
if DEBUG:
    CELERY_TASK_ALWAYS_EAGER = True
    CELERY_TASK_STORE_EAGER_RESULT = True

# Cache Configuration (required for django-ratelimit)
# Production: Redis for cross-worker consistency (rate limiting, sessions)
# Development: LocMemCache (no Redis dependency required)
REDIS_HOST = os.environ.get("REDIS_HOST")
if REDIS_HOST:
    REDIS_PORT = os.environ.get("REDIS_PORT", "6379")
    REDIS_DB = os.environ.get("REDIS_DB", "1")
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.redis.RedisCache',
            'LOCATION': build_redis_url(
                host=REDIS_HOST,
                port=REDIS_PORT,
                db=REDIS_DB,
                password=_REDIS_PASSWORD,
            ),
        }
    }
else:
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
            'LOCATION': 'unique-snowflake',
        }
    }

# Rate limiting configuration
RATELIMIT_USE_CACHE = 'default'

# BUG-01/02 FIX: Indiquer à django-ratelimit que 1 proxy de confiance est en amont
# (Nginx). Sans cela, la résolution d'IP depuis X-Forwarded-For peut être incorrecte.
# Remplacé par get_real_ip() qui lit X-Real-IP directement depuis le header Nginx.
NUM_PROXIES = 1

# Enable/disable django-ratelimit via env (default: enabled)
# Can be disabled for E2E testing environment only (set RATELIMIT_ENABLE=false)
RATELIMIT_ENABLE = os.environ.get("RATELIMIT_ENABLE", "true").lower() == "true"
STUDENT_LOGIN_RATE_LIMIT_ATTEMPTS = int(os.environ.get("STUDENT_LOGIN_RATE_LIMIT_ATTEMPTS", "10"))
STUDENT_LOGIN_RATE_LIMIT_WINDOW = int(os.environ.get("STUDENT_LOGIN_RATE_LIMIT_WINDOW", "900"))

# Production guard: prevent accidental rate limiting disable in production
# Exception: If specific E2E_TEST_MODE flag is set (for pre-production validation)
# DJANGO_ENV is defined at the top of the file
E2E_TEST_MODE = os.environ.get("E2E_TEST_MODE", "false").lower() == "true"

if DJANGO_ENV == "production" and not RATELIMIT_ENABLE and not E2E_TEST_MODE:
    raise ValueError("RATELIMIT_ENABLE cannot be false in production environment (unless E2E_TEST_MODE=true)")

# BUG-02 FIX: Redis obligatoire en production pour que le rate limiting soit
# partagé entre tous les workers Gunicorn. Sans Redis, chaque worker a son
# propre compteur (LocMemCache) : seuil effectif = seuil × nb_workers.
if DJANGO_ENV == "production" and not _REDIS_AVAILABLE and not E2E_TEST_MODE:
    import logging as _logging
    _logging.getLogger(__name__).warning(
        "REDIS_HOST non défini en production. Le rate limiting n'est PAS partagé entre "
        "les workers Gunicorn (LocMemCache par processus). "
        "Définissez REDIS_HOST pour un rate limiting cohérent."
    )

# CORS Configuration
# Conformité: docs/security/MANUEL_SECURITE.md — CORS
if DEBUG:
    # Development: Allow localhost origins for frontend dev server
    CORS_ALLOWED_ORIGINS = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:8088",
        "http://127.0.0.1:8088",
        "http://localhost:5174",
        "http://127.0.0.1:5174",
    ]
    CORS_ALLOW_CREDENTIALS = True
else:
    # Production: Explicit origins only
    # Set via environment variable CORS_ALLOWED_ORIGINS (comma-separated)
    cors_origins = os.environ.get("CORS_ALLOWED_ORIGINS", "")
    if cors_origins:
        CORS_ALLOWED_ORIGINS = [origin.strip() for origin in cors_origins.split(",")]
        CORS_ALLOW_CREDENTIALS = True
    else:
        # Same-origin only (Nginx serves frontend + backend on same domain)
        CORS_ALLOWED_ORIGINS = []
        CORS_ALLOW_CREDENTIALS = False

# CORS Security Headers
CORS_ALLOW_HEADERS = [
    'accept',
    'accept-encoding',
    'authorization',
    'content-type',
    'dnt',
    'origin',
    'user-agent',
    'x-csrftoken',
    'x-requested-with',
]

# Content Security Policy (CSP)
# Conformité: Phase 3 - Review sécurité frontend
if not DEBUG:
    CONTENT_SECURITY_POLICY = {
        'DIRECTIVES': {
            'default-src': ["'self'"],
            'script-src': ["'self'"],
            'style-src': ["'self'", "'unsafe-inline'", "https://fonts.googleapis.com"],
            'img-src': ["'self'", "data:", "blob:"],
            'font-src': ["'self'", "https://fonts.gstatic.com"],
            'connect-src': ["'self'"],
            'frame-ancestors': ["'none'"],
            'base-uri': ["'self'"],
            'form-action': ["'self'"],
        }
    }
else:
    # CSP permissive en développement
    CONTENT_SECURITY_POLICY = {
        'DIRECTIVES': {
            'default-src': ["'self'", "'unsafe-inline'", "'unsafe-eval'"],
            'script-src': ["'self'", "'unsafe-inline'", "'unsafe-eval'"],
            'style-src': ["'self'", "'unsafe-inline'"],
            'img-src': ["'self'", "data:", "blob:", "http:", "https:"],
            'connect-src': ["'self'", "http://localhost:*", "ws://localhost:*"],
            'frame-ancestors': ["'self'"], 
        }
    }

# DRF Spectacular Configuration
# OpenAPI 3.0 Schema Generation
SPECTACULAR_SETTINGS = {
    'TITLE': 'Korrigo API',
    'DESCRIPTION': 'API de la plateforme Korrigo - Correction numérique de copies d\'examens',
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
    'CONTACT': {
        'name': 'Aleddine BEN RHOUMA',
        'email': 'contact@korrigo.edu',
    },
    'LICENSE': {
        'name': 'Proprietary - AEFE/Éducation Nationale',
    },
    'TAGS': [
        {'name': 'Authentication', 'description': 'Endpoints d\'authentification (Professeurs, Admins, Élèves)'},
        {'name': 'Exams', 'description': 'Gestion des examens et copies'},
        {'name': 'Grading', 'description': 'Correction et annotations'},
        {'name': 'Students', 'description': 'Gestion des élèves et accès résultats'},
        {'name': 'Admin', 'description': 'Administration système'},
    ],
    'COMPONENT_SPLIT_REQUEST': True,
    'SCHEMA_PATH_PREFIX': r'/api/',
    'SERVERS': [
        {'url': 'http://localhost:8088', 'description': 'Serveur de développement'},
        {'url': 'https://korrigo.labomaths.tn', 'description': 'Production'},
    ],
}


# Error Notification Configuration (P0-OP-02: Production Readiness)
ADMINS = [
    ('Admin', os.environ.get('ADMIN_EMAIL', '')),
]
MANAGERS = ADMINS

if not DEBUG:
    EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
    EMAIL_HOST = os.environ.get('EMAIL_HOST', '')
    EMAIL_PORT = int(os.environ.get('EMAIL_PORT', 587))
    EMAIL_USE_TLS = os.environ.get('EMAIL_USE_TLS', 'true').lower() == 'true'
    EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER')
    EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD')
    SERVER_EMAIL = os.environ.get('SERVER_EMAIL', '')
    EMAIL_ALERTS_ENABLED = all([
        EMAIL_HOST,
        EMAIL_HOST_USER,
        EMAIL_HOST_PASSWORD,
        SERVER_EMAIL,
        os.environ.get('ADMIN_EMAIL', ''),
    ])

    import logging as _logging
    if EMAIL_ALERTS_ENABLED:
        _logging_handlers: dict = LOGGING['handlers']  # type: ignore[index]
        _logging_handlers['mail_admins'] = {
            'level': 'ERROR',
            'class': 'django.utils.log.AdminEmailHandler',
            'filters': ['require_debug_false'],
        }
        _logging_loggers: dict = LOGGING['loggers']  # type: ignore[index]
        _logging_loggers['django']['handlers'].append('mail_admins')
    else:
        _logging.getLogger(__name__).info(
            'Error notification emails disabled — incomplete SMTP configuration'
        )
else:
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

FRONTEND_URL = os.environ.get('FRONTEND_URL', 'https://korrigo.labomaths.tn')
STUDENT_PORTAL_URL = os.environ.get('STUDENT_PORTAL_URL', 'https://korrigo.labomaths.tn/student/login')
