#!/usr/bin/env bash
set -euo pipefail

# Supported dependency versions must pass the security check without CVE
# suppressions. Preserve pip-audit's exit status so findings block CI.
exec pip-audit -r requirements.txt
