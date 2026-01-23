#!/bin/bash
set -e

echo "--> Applied database migrations..."
python manage.py migrate

echo "--> Collecting static files..."
python manage.py collectstatic --noinput

echo "Args passed: $@"
echo "Arg count: $#"

if [ "$#" -gt 0 ]; then
    exec "$@"
else
    echo "--> Starting Gunicorn..."
    exec gunicorn core.wsgi:application -c gunicorn_config.py
fi
