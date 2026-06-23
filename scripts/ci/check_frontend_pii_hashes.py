#!/usr/bin/env python3
"""Fail if known real PII reappears in frontend sources or built assets.

The denylist stores only HMAC-SHA256 markers of normalized values. The pepper
must be supplied through PII_GATE_PEPPER and must never be committed.

Current marker status: NEEDS_ADMIN_REGENERATION. The previous SHA-256 markers
were removed because they were pseudonymous and dictionary-searchable in a
public repository. Regenerate real markers offline with the companion generator.
"""

from __future__ import annotations

import argparse
import hashlib
import hmac
import os
import re
import sys
import unicodedata
from pathlib import Path


DENY_HMACS: dict[str, str] = {
    # Real markers intentionally omitted until the administrator regenerates
    # them offline with PII_GATE_PEPPER and generate_pii_hmac_markers.py.
}

TEXT_EXTENSIONS = {".vue", ".js", ".ts", ".jsx", ".tsx", ".html", ".css", ".json"}
EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
WORD_RE = re.compile(r"[A-Za-zÀ-ÖØ-öø-ÿ0-9._%+-]+")


def normalize(value: str) -> str:
    value = unicodedata.normalize("NFKD", value.lower().strip())
    value = "".join(ch for ch in value if unicodedata.category(ch) not in {"Cc", "Cf"})
    value = "".join(ch for ch in value if not unicodedata.combining(ch))
    value = re.sub(r"[^a-z0-9@._%+-]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def hmac_digest(value: str, pepper: str) -> str:
    normalized = normalize(value).encode("utf-8")
    key = pepper.encode("utf-8")
    return hmac.new(key, normalized, hashlib.sha256).hexdigest()


def get_pepper() -> str | None:
    pepper = os.environ.get("PII_GATE_PEPPER", "")
    return pepper if pepper else None


def candidate_values(line: str) -> set[str]:
    normalized_line = normalize(line)
    values = set(EMAIL_RE.findall(normalized_line))
    words = [normalize(w) for w in WORD_RE.findall(normalized_line)]
    words = [w for w in words if w]
    for size in range(1, 5):
        for idx in range(0, max(len(words) - size + 1, 0)):
            values.add(" ".join(words[idx : idx + size]))
    return values


def iter_source_files(root: Path):
    for path in root.rglob("*"):
        if not path.is_file() or path.suffix not in TEXT_EXTENSIONS:
            continue
        if any(part in {"node_modules", "coverage"} for part in path.parts):
            continue
        yield path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", nargs="?", default="frontend/src")
    args = parser.parse_args()

    pepper = get_pepper()
    if pepper is None:
        print("PII_GATE_STATUS=FAIL_MISSING_PEPPER")
        print("PII_HASH_MATCH_COUNT=0")
        return 2

    root = Path(args.root)
    matches: list[tuple[Path, int, str]] = []
    for path in iter_source_files(root):
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except UnicodeDecodeError:
            continue
        for line_no, line in enumerate(lines, 1):
            for candidate in candidate_values(line):
                marker = hmac_digest(candidate, pepper)
                kind = DENY_HMACS.get(marker)
                if kind:
                    matches.append((path, line_no, kind))
                    break

    print("PII_GATE_STATUS=PASS" if not matches else "PII_GATE_STATUS=FAIL_MATCH")
    print(f"PII_HASH_MATCH_COUNT={len(matches)}")
    for path, line_no, kind in matches:
        print(f"{path}:{line_no}: {kind}")
    return 1 if matches else 0


if __name__ == "__main__":
    raise SystemExit(main())
