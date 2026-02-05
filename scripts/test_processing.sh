#!/usr/bin/env bash
set -euo pipefail

echo "================================================"
echo "Running Processing Tests (Heavy I/O)"
echo "================================================"

cd "$(dirname "$0")/../backend"

pytest -n 2 -m processing --dist=loadscope -v

echo "================================================"
echo "✓ Processing tests passed"
echo "================================================"
