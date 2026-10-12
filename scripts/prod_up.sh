#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
bash "$script_dir/prod_compose.sh" config --quiet
exec bash "$script_dir/prod_compose.sh" up --no-build --wait -d "$@"
