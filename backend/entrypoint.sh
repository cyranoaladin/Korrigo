#!/bin/bash
set -e

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

echo "Args passed: $@"
echo "Arg count: $#"

if [ "$#" -gt 0 ]; then
    exec "$@"
else
    echo "--> Starting Gunicorn..."
    exec gunicorn core.wsgi:application -c gunicorn_config.py
fi
