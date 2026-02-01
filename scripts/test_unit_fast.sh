#!/usr/bin/env bash
set -euo pipefail

echo "================================================"
echo "Running Unit Tests (Fast, No DB)"
echo "================================================"

cd "$(dirname "$0")/../backend"

pytest -n 8 -m unit --dist=loadscope -v

echo "================================================"
echo "✓ Unit tests passed"
echo "================================================"
