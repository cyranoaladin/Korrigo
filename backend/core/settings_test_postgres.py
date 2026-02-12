"""
Test settings for postgres-marked tests.
Uses the real PostgreSQL backend (from DATABASE_URL env var) instead of SQLite,
so that SELECT FOR UPDATE and row-level locking work correctly.
"""
from .settings_test import *  # noqa: F401,F403

import os

# Override the SQLite database with PostgreSQL from environment
DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgres://viatique_user:viatique_password@db:5432/viatique",
)

try:
    import dj_database_url

    DATABASES = {
        "default": dj_database_url.parse(
            DATABASE_URL,
            conn_max_age=0,
        )
    }
    DATABASES["default"]["TEST"] = {"NAME": "test_viatique_postgres"}
except ImportError:
    raise RuntimeError(
        "dj-database-url is required for postgres test settings. "
        "Install it with: pip install dj-database-url"
    )
