import os
import dj_database_url
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

# Load environment variables from .env file
load_dotenv(BASE_DIR.parent / '.env')

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
SESSION_COOKIE_SECURE = os.environ.get("SESSION_COOKIE_SECURE", "false").lower() == "true"
CSRF_COOKIE_SECURE = os.environ.get("CSRF_COOKIE_SECURE", "false").lower() == "true"

# Static & Media Files
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# File Upload Limits (Mission 5.1)
# Allow large PDF uploads (up to 100MB)
DATA_UPLOAD_MAX_MEMORY_SIZE = 104857600  # 100 MB
FILE_UPLOAD_MAX_MEMORY_SIZE = 104857600  # 100 MB

# E2E Testing Configuration
E2E_SEED_TOKEN = os.environ.get("E2E_SEED_TOKEN")  # Only set in prod-like environment

# Prometheus Metrics Configuration (S5-B)
# METRICS_TOKEN: Optional token for /metrics endpoint authentication
# - Development (DEBUG=True): No authentication required
# - Production (DEBUG=False):
#   - If METRICS_TOKEN set: Token required via X-Metrics-Token header or ?token= query param
#   - If METRICS_TOKEN not set: Public access (operator's choice, warning logged on startup)
METRICS_TOKEN = os.environ.get("METRICS_TOKEN")

# Warn if METRICS_TOKEN not set in production
if DJANGO_ENV == "production" and not METRICS_TOKEN and not DEBUG:
    import logging
    logger = logging.getLogger(__name__)
    logger.warning(
        "METRICS_TOKEN not set in production. /metrics endpoint will be publicly accessible. "
        "Set METRICS_TOKEN environment variable to secure the endpoint."
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

# Cookie SameSite (all environments)
SESSION_COOKIE_SAMESITE = 'Lax'
CSRF_COOKIE_SAMESITE = 'Lax'
CSRF_COOKIE_HTTPONLY = False  # Required for SPAs to read CSRF token from cookie

# CSRF Trusted Origins
CSRF_TRUSTED_ORIGINS = os.environ.get(
    "CSRF_TRUSTED_ORIGINS",
    "http://localhost:8088,http://127.0.0.1:8088,http://localhost:5173,http://127.0.0.1:5173,http://localhost:5174,http://127.0.0.1:5174"
).split(",")



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
]

# Django REST Framework Configuration
# Security: Default Deny - All endpoints require explicit authentication
REST_FRAMEWORK = {
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',  # Default: authenticated only
    ],
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.SessionAuthentication',
        'rest_framework.authentication.BasicAuthentication',
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

if DEBUG:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }
else:
    db_config = dj_database_url.config(
        default='sqlite:///' + str(BASE_DIR / 'db.sqlite3'),
        conn_max_age=600
    )
    
    # P0-OP-04: Add database lock timeout protection
    if db_config.get('ENGINE') == 'django.db.backends.postgresql':
        db_config['OPTIONS'] = {
            'connect_timeout': 10,
            'options': '-c lock_timeout=5000 -c statement_timeout=30000 -c idle_in_transaction_session_timeout=60000'
        }
        db_config['CONN_HEALTH_CHECKS'] = True
    
    DATABASES = {'default': db_config}






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

SESSION_ENGINE = 'django.contrib.sessions.backends.cached_db'
SESSION_COOKIE_AGE = 14400
SESSION_EXPIRE_AT_BROWSER_CLOSE = True
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'

# Auth URLs
LOGIN_URL = '/admin/login/'
LOGIN_REDIRECT_URL = '/admin-dashboard'
LOGOUT_REDIRECT_URL = '/'

# P1.1 FIX: Ensure logs directory exists before configuring logging
LOGS_DIR = os.path.join(BASE_DIR, 'logs')
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
            'filename': os.path.join(BASE_DIR, 'logs', 'django.log'),
            'maxBytes': 10485760,  # 10MB
            'backupCount': 10,
            'formatter': LOG_FORMATTER,
            'filters': ['request_context'],
        },
        'audit_file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': os.path.join(BASE_DIR, 'logs', 'audit.log'),
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

CELERY_BROKER_URL = os.environ.get("CELERY_BROKER_URL", "redis://redis:6379/0")
CELERY_RESULT_BACKEND = os.environ.get("CELERY_RESULT_BACKEND", "redis://redis:6379/0")
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = 'UTC'
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 300
CELERY_TASK_SOFT_TIME_LIMIT = 270

# ZF-AUD-13: Dedicated queues for performance optimization
# Separate heavy tasks (import, finalize) from light tasks (default)
CELERY_TASK_ROUTES = {
    'grading.tasks.async_import_pdf': {'queue': 'import'},
    'grading.tasks.async_batch_import': {'queue': 'import'},
    'grading.tasks.async_finalize_copy': {'queue': 'finalize'},
    'grading.tasks.cleanup_orphaned_files': {'queue': 'maintenance'},
}

# ZF-AUD-13: Rate limiting to prevent overload
CELERY_TASK_ANNOTATIONS = {
    'grading.tasks.async_import_pdf': {'rate_limit': '10/m'},
    'grading.tasks.async_finalize_copy': {'rate_limit': '5/m'},
}

# ZF-AUD-13: Prefetch multiplier (1 for long tasks to avoid blocking)
CELERY_WORKER_PREFETCH_MULTIPLIER = 1

# Cache Configuration (required for django-ratelimit and login lockout)
# Use Redis if available (production/Docker), otherwise LocMemCache (dev)
REDIS_HOST = os.environ.get('REDIS_HOST', '')
if REDIS_HOST:
    CACHES = {
        'default': {
            'BACKEND': 'django_redis.cache.RedisCache',
            'LOCATION': f'redis://{REDIS_HOST}:{os.environ.get("REDIS_PORT", "6379")}/{os.environ.get("REDIS_DB", "1")}',
            'OPTIONS': {
                'CLIENT_CLASS': 'django_redis.client.DefaultClient',
            },
            'KEY_PREFIX': 'viatique',
            'TIMEOUT': 300,
        }
    }
else:
    # Development: LocMemCache (WARNING: does not work with multiple workers)
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
            'LOCATION': 'unique-snowflake',
        }
    }

# Rate limiting configuration
RATELIMIT_USE_CACHE = 'default'

# Enable/disable django-ratelimit via env (default: enabled)
# Can be disabled for E2E testing environment only (set RATELIMIT_ENABLE=false)
RATELIMIT_ENABLE = os.environ.get("RATELIMIT_ENABLE", "true").lower() == "true"

# Production guard: prevent accidental rate limiting disable in production
# Exception: If specific E2E_TEST_MODE flag is set (for pre-production validation)
# DJANGO_ENV is defined at the top of the file
E2E_TEST_MODE = os.environ.get("E2E_TEST_MODE", "false").lower() == "true"

if DJANGO_ENV == "production" and not RATELIMIT_ENABLE and not E2E_TEST_MODE:
    raise ValueError("RATELIMIT_ENABLE cannot be false in production environment (unless E2E_TEST_MODE=true)")

# CORS Configuration
# Conformité: .antigravity/rules/01_security_rules.md § 4.2
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
            'style-src': ["'self'"],
            'img-src': ["'self'", "data:", "blob:"],
            'font-src': ["'self'"],
            'connect-src': ["'self'"],
            'frame-ancestors': ["'none'"],
            'base-uri': ["'self'"],
            'form-action': ["'self'"],
            'upgrade-insecure-requests': True,
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
    'TITLE': 'Viatique API',
    'DESCRIPTION': 'API de la plateforme Viatique - Correction numérique de copies d\'examens',
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
    'CONTACT': {
        'name': 'Aleddine BEN RHOUMA',
        'email': 'contact@viatique.edu',
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
        {'url': 'https://viatique.example.com', 'description': 'Production'},
    ],
}


# Error Notification Configuration (P0-OP-02: Production Readiness)
ADMINS = [
    ('Admin', os.environ.get('ADMIN_EMAIL', 'admin@example.com')),
]
MANAGERS = ADMINS

if not DEBUG:
    EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
    EMAIL_HOST = os.environ.get('EMAIL_HOST', 'smtp.example.com')
    EMAIL_PORT = int(os.environ.get('EMAIL_PORT', 587))
    EMAIL_USE_TLS = os.environ.get('EMAIL_USE_TLS', 'true').lower() == 'true'
    EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER')
    EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD')
    SERVER_EMAIL = os.environ.get('SERVER_EMAIL', 'korrigo@example.com')
    
    LOGGING['handlers']['mail_admins'] = {
        'level': 'ERROR',
        'class': 'django.utils.log.AdminEmailHandler',
        'filters': ['require_debug_false'],
    }
    LOGGING['loggers']['django']['handlers'].append('mail_admins')
else:
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'