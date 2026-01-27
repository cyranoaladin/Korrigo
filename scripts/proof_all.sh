#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

"${ROOT_DIR}/scripts/proof_imports.sh"

# LOT1 (15 tests)
PYTHONDONTWRITEBYTECODE=1 "${ROOT_DIR}/backend/venv/bin/python" -m pytest -q \
  backend/grading/tests/test_api_error_contract_scanner.py \
  backend/grading/tests/test_api_error_contract_runtime.py \
  backend/grading/tests/test_workflow_complete.py::TestWorkflowComplete::test_workflow_teacher_full_cycle_success \
  backend/grading/tests/test_error_handling.py

# LOT2 (8 tests)
PYTHONDONTWRITEBYTECODE=1 "${ROOT_DIR}/backend/venv/bin/python" -m pytest -q \
  backend/grading/tests/test_concurrency.py::TestConcurrency::test_finalize_uses_select_for_update_on_copy_and_lock \
  backend/grading/tests/test_lock_endpoints.py \
  backend/grading/tests/test_workflow.py::test_finalize_works_from_ready

# Postgres marker (must be pass or skip, never unknown marker)
PYTHONDONTWRITEBYTECODE=1 "${ROOT_DIR}/backend/venv/bin/python" -m pytest -q -m postgres \
  backend/grading/tests/test_concurrency_postgres.py
