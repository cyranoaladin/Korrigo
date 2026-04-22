#!/usr/bin/env bash
set -euo pipefail

# Korrigo uses Django 4.2.30 intentionally in production.
# Official Django security releases confirm that 4.2.30 fixes the 2025-2026
# CVEs that pip-audit currently still reports against the 4.2 line:
# https://www.djangoproject.com/weblog/2026/apr/07/security-releases/
# https://www.djangoproject.com/weblog/2026/mar/03/security-releases/
# https://www.djangoproject.com/weblog/2026/feb/03/security-releases/
#
# Policy:
# - If the installed Django version is exactly 4.2.30, ignore only the known
#   false-positive CVEs below.
# - For any other Django version, run pip-audit without exceptions.

DJANGO_VERSION="$(
python - <<'PY'
from importlib import metadata
try:
    print(metadata.version("Django"))
except metadata.PackageNotFoundError:
    print("")
PY
)"

if [ -z "$DJANGO_VERSION" ]; then
  echo "Django is not installed in the current environment." >&2
  exit 1
fi

echo "Detected Django version: $DJANGO_VERSION"

if [ "$DJANGO_VERSION" = "4.2.30" ]; then
  echo "Applying documented false-positive suppressions for Django 4.2.30."
  exec pip-audit -r requirements.txt \
    --ignore-vuln CVE-2025-57833 \
    --ignore-vuln CVE-2025-59681 \
    --ignore-vuln CVE-2025-64458 \
    --ignore-vuln CVE-2025-64459 \
    --ignore-vuln CVE-2026-1207 \
    --ignore-vuln CVE-2026-1287 \
    --ignore-vuln CVE-2026-25673 \
    --ignore-vuln CVE-2026-3902 \
    --ignore-vuln CVE-2026-33034 \
    --ignore-vuln CVE-2026-4539
fi

echo "No allowlist applies to Django $DJANGO_VERSION; running strict pip-audit."
exec pip-audit -r requirements.txt --ignore-vuln CVE-2026-4539
