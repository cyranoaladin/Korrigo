#!/bin/bash
set -e

# Fix permissions for Docker-mounted volumes (owned by root when first created)
# This runs as whatever user the container starts with (root in Dockerfile, or --user root)
if [ "$(id -u)" = "0" ]; then
    echo "--> Fixing volume permissions..."
    mkdir -p /app/staticfiles /app/media /app/.cache /app/logs
    chown -R korrigo:korrigo /app/staticfiles /app/media /app/.cache /app/logs
fi

# Only run migrations if DJANGO_AUTO_MIGRATE is not explicitly set to false
if [ "${DJANGO_AUTO_MIGRATE:-true}" != "false" ]; then
    echo "--> Applied database migrations..."
    python manage.py migrate
else
    echo "--> Skipping automatic migrations (DJANGO_AUTO_MIGRATE=false)"
fi

echo "--> Collecting static files..."
python manage.py collectstatic --noinput

# Seed production data if SEED_ON_START is enabled
if [ "${SEED_ON_START:-false}" = "true" ]; then
    echo "--> Running seed_initial_exams (idempotent)..."
    python manage.py seed_initial_exams || echo "WARNING: seed_initial_exams failed (non-blocking)"
fi

echo "--> Ensuring user roles exist..."
python manage.py shell -c "from core.auth import create_user_roles; create_user_roles()" || true

echo "Args passed: $@"
echo "Arg count: $#"

# Drop privileges if running as root
if [ "$(id -u)" = "0" ]; then
    echo "--> Dropping to user korrigo..."
    if [ "$#" -gt 0 ]; then
        exec su -s /bin/bash korrigo -c "$*"
    else
        echo "--> Starting Gunicorn..."
        exec su -s /bin/bash korrigo -c "gunicorn core.wsgi:application -c gunicorn_config.py"
    fi
else
    if [ "$#" -gt 0 ]; then
        exec "$@"
    else
        echo "--> Starting Gunicorn..."
        exec gunicorn core.wsgi:application -c gunicorn_config.py
    fi
fi
