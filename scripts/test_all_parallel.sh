#!/usr/bin/env bash
set -euo pipefail

echo "================================================"
echo "Running All Test Suites in Parallel Mode"
echo "================================================"

SCRIPT_DIR="$(dirname "$0")"

echo ""
echo ">>> Running Unit Tests..."
bash "$SCRIPT_DIR/test_unit_fast.sh"

echo ""
echo ">>> Running Integration Tests..."
bash "$SCRIPT_DIR/test_integration.sh"

echo ""
echo ">>> Running Processing Tests..."
bash "$SCRIPT_DIR/test_processing.sh"

echo ""
echo "================================================"
echo "✓ All test suites passed successfully"
echo "================================================"
