#!/bin/bash
set -euo pipefail

run_as_app_user() {
    if [ "$(id -u)" = "0" ]; then
        su -s /bin/bash korrigo -c "$*"
    else
        bash -lc "$*"
    fi
}

prepare_volumes() {
    if [ "$(id -u)" != "0" ]; then
        echo "--> Volume permission preparation skipped (not root)"
        return 0
    fi

    echo "--> Preparing writable runtime directories..."
    mkdir -p /app/staticfiles /app/media /app/.cache /app/logs
    if ! chown -R korrigo:korrigo /app/staticfiles /app/media /app/.cache /app/logs; then
        echo "WARNING: could not adjust runtime directory ownership; continuing"
    fi
}

collect_static_best_effort() {
    echo "--> Collecting static files..."
    if ! run_as_app_user "python manage.py collectstatic --noinput"; then
        echo "WARNING: collectstatic failed during preparation; continuing to schema invariants"
    fi
}

is_explicit_migration_command() {
    [ "${1:-}" = "python" ] && [ "${2:-}" = "manage.py" ] && [ "${3:-}" = "migrate" ]
}

run_auto_migrations_if_enabled() {
    if [ "${DJANGO_AUTO_MIGRATE:-true}" = "false" ]; then
        echo "--> Skipping automatic migrations (DJANGO_AUTO_MIGRATE=false)"
        return 0
    fi

    echo "--> Applying database migrations (DJANGO_AUTO_MIGRATE enabled)..."
    run_as_app_user "python manage.py migrate --noinput"
}

ensure_schema_ready() {
    echo "--> Checking database schema invariants..."
    local check_log
    check_log="$(mktemp)"
    if run_as_app_user "python manage.py migrate --check --noinput" >"${check_log}" 2>&1; then
        rm -f "${check_log}"
        return 0
    fi

    echo "ERROR: Database schema is not up to date or not reachable."
    echo "ERROR: DJANGO_AUTO_MIGRATE=false in production; apply migrations explicitly with a one-shot container before starting services."
    sed -n '1,80p' "${check_log}"
    rm -f "${check_log}"
    exit 1
}

ensure_roles() {
    echo "--> Ensuring user roles exist..."
    run_as_app_user "python manage.py shell -c \"from core.auth import create_user_roles; create_user_roles()\""
}

run_seed_if_enabled() {
    if [ "${SEED_ON_START:-false}" != "true" ]; then
        return 0
    fi

    echo "--> Running seed_initial_exams (idempotent)..."
    run_as_app_user "python manage.py seed_initial_exams"
}

# Drop privileges if running as root
exec_as_app_user() {
    echo "Args passed: $*"
    echo "Arg count: $#"

    if [ "$(id -u)" = "0" ]; then
        echo "--> Dropping to user korrigo..."
        if [ "$#" -gt 0 ]; then
            exec su -s /bin/bash korrigo -c "$*"
        fi
        echo "--> Starting Gunicorn..."
        exec su -s /bin/bash korrigo -c "gunicorn core.wsgi:application -c gunicorn_config.py"
    fi

    if [ "$#" -gt 0 ]; then
        exec "$@"
    fi
    echo "--> Starting Gunicorn..."
    exec gunicorn core.wsgi:application -c gunicorn_config.py
}

prepare_volumes
collect_static_best_effort

if is_explicit_migration_command "$@"; then
    echo "--> Skipping schema invariant checks for explicit migration command"
    exec_as_app_user "$@"
fi

run_auto_migrations_if_enabled
ensure_schema_ready
ensure_roles
run_seed_if_enabled
exec_as_app_user "$@"
