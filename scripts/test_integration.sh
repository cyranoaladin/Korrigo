#!/usr/bin/env bash
set -euo pipefail

echo "================================================"
echo "Running Integration Tests (API + DB)"
echo "================================================"

cd "$(dirname "$0")/../backend"

pytest -n 4 -m api --dist=loadscope -v

echo "================================================"
echo "✓ Integration tests passed"
echo "================================================"
