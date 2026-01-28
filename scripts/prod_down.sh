#!/usr/bin/env bash
set -euo pipefail

echo "WARNING: this will remove volumes (-v) and delete the local postgres data."
docker compose -f infra/docker/docker-compose.prod.yml down -v
