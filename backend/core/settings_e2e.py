"""
E2E test settings — extends production settings with E2E-specific overrides.
Used by docker-compose.e2e.yml.
"""
import os

from .settings_prod import *  # noqa: F403, F401

DJANGO_ENV = "e2e"

# Override ALLOWED_HOSTS for local E2E
ALLOWED_HOSTS = [
    h.strip()
    for h in os.environ.get(
        "ALLOWED_HOSTS", "localhost,127.0.0.1,backend"
    ).split(",")
    if h.strip()
]

# HTTP-compatible cookies for local E2E (no HTTPS)
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SAMESITE = "Lax"

# Disable rate limiting for E2E
RATELIMIT_ENABLE = False

# CSRF trusted origins for local E2E
CSRF_TRUSTED_ORIGINS = [
    h.strip()
    for h in os.environ.get(
        "CSRF_TRUSTED_ORIGINS", "http://localhost:8088,http://127.0.0.1:8088"
    ).split(",")
    if h.strip()
]

CORS_ALLOWED_ORIGINS = [
    h.strip()
    for h in os.environ.get(
        "CORS_ALLOWED_ORIGINS", "http://localhost:8088,http://127.0.0.1:8088"
    ).split(",")
    if h.strip()
]

# Disable SSL redirect for E2E
SECURE_SSL_REDIRECT = False
SECURE_HSTS_SECONDS = 0
