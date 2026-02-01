#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if [[ -x "${ROOT_DIR}/backend/venv/bin/python" ]]; then
  PY="${ROOT_DIR}/backend/venv/bin/python"
elif [[ -x "${ROOT_DIR}/venv/bin/python" ]]; then
  PY="${ROOT_DIR}/venv/bin/python"
else
  echo "ERROR: no venv python found. Expected backend/venv/bin/python or venv/bin/python" >&2
  exit 1
fi

export PYTHONDONTWRITEBYTECODE=1

# DRF accesses Django settings at import time (api_settings). Configure settings
# explicitly to make the import proof reproducible.
export DJANGO_SETTINGS_MODULE="core.settings_test"

"${PY}" -c "import os,sys; sys.path.insert(0,'${ROOT_DIR}/backend'); import django; django.setup(); import grading.views_draft as m; print('OK import views_draft')"
"${PY}" -c "import os,sys; sys.path.insert(0,'${ROOT_DIR}/backend'); import django; django.setup(); import grading.views_lock as m; print('OK import views_lock')"
"${PY}" -c "import os,sys; sys.path.insert(0,'${ROOT_DIR}/backend'); import django; django.setup(); import grading.views as m; print('OK import views')"
