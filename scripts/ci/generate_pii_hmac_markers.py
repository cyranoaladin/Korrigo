#!/usr/bin/env python3
"""Generate HMAC markers for the PII gate from non-committed input.

Usage:
  PII_GATE_PEPPER="..." python scripts/ci/generate_pii_hmac_markers.py < /local/pii_values.txt

Never commit the input file. This script prints only marker identifiers and
HMAC hex values, never the source values.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parent))
from check_frontend_pii_hashes import hmac_digest, normalize  # noqa: E402


def main() -> int:
    pepper = os.environ.get("PII_GATE_PEPPER", "")
    if not pepper:
        print("PII_GATE_STATUS=FAIL_MISSING_PEPPER")
        return 2

    markers: list[str] = []
    seen: set[str] = set()
    for raw_line in sys.stdin:
        value = normalize(raw_line)
        if not value or value in seen:
            continue
        seen.add(value)
        markers.append(hmac_digest(value, pepper))

    print("DENY_HMACS = {")
    for idx, marker in enumerate(markers, 1):
        print(f'    "{marker}": "marker_{idx:03d}",')
    print("}")
    print(f"PII_HMAC_MARKER_COUNT={len(markers)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
