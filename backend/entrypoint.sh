#!/bin/bash
set -e

echo "--> Applied database migrations..."
python manage.py migrate

echo "--> Collecting static files..."
python manage.py collectstatic --noinput

echo "--> Starting Gunicorn..."
exec gunicorn core.wsgi:application -c gunicorn_config.py
