#!/usr/bin/env bash
# Use the canonical private environment rather than an implicit working-directory .env.
set -euo pipefail

repo_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
runtime_env="${KORRIGO_ENV_FILE:-/etc/korrigo-ops/runtime.env}"
if [[ ! -f "$runtime_env" || ! -r "$runtime_env" ]]; then
    printf 'Production environment file is missing or unreadable; set KORRIGO_ENV_FILE.\n' >&2
    exit 1
fi

exec docker compose --env-file "$runtime_env" \
    -f "$repo_root/infra/docker/docker-compose.prod.yml" "$@"
