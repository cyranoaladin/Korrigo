#!/usr/bin/env python3
"""Classify plain email occurrences without printing the addresses."""

from __future__ import annotations

import re
from collections import Counter, defaultdict
from pathlib import Path


ROOTS = [Path("backend"), Path("scripts"), Path("docs"), Path(".github"), Path("frontend/src")]
EXCLUDED_PARTS = {
    ".git",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    ".venv-porte5b",
    "__pycache__",
    "coverage",
    "dist",
    "htmlcov",
    "node_modules",
}
TEXT_SUFFIXES = {
    ".cfg",
    ".conf",
    ".css",
    ".env",
    ".html",
    ".ini",
    ".js",
    ".json",
    ".md",
    ".py",
    ".ts",
    ".txt",
    ".vue",
    ".yaml",
    ".yml",
}
EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")


def is_text_candidate(path: Path) -> bool:
    if any(part in EXCLUDED_PARTS for part in path.parts):
        return False
    if not path.is_file():
        return False
    if path.suffix.lower() in TEXT_SUFFIXES:
        return True
    return path.name in {".gitignore", "Dockerfile", "Makefile"}


def category_for(path: Path, text: str) -> tuple[str, str]:
    lowered = text.lower()
    path_text = str(path).lower()
    if any(token in lowered for token in ["example.com", "example.test", "localhost"]):
        return "TEST_FIXTURE", "example-or-local-address"
    if "test" in path_text or "fixture" in path_text or "pytest" in lowered:
        return "TEST_FIXTURE", "test-path-or-test-context"
    if path.parts and path.parts[0] == "docs":
        if any(token in lowered for token in ["contact", "institution", "public"]):
            return "PUBLIC_INSTITUTIONAL", "documentation-public-contact-context"
        return "DOC_EXAMPLE", "documentation-context"
    if path.parts and path.parts[0] == ".github":
        return "TO_REVIEW", "workflow-or-ci-context"
    if any(token in lowered for token in ["password", "token", "secret", "api_key", "apikey"]):
        return "SECRET_LIKE", "secret-adjacent-context"
    if path.parts and path.parts[0] in {"backend", "scripts"}:
        return "TO_REVIEW", "runtime-or-script-context"
    return "PERSONAL_OR_UNKNOWN", "requires-human-classification"


def iter_files():
    for root in ROOTS:
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if is_text_candidate(path):
                yield path


def main() -> int:
    rows: list[tuple[str, int, str, str]] = []
    category_counts: Counter[str] = Counter()
    total_occurrences = 0

    for path in sorted(iter_files()):
        text = path.read_text(encoding="utf-8", errors="ignore")
        count = len(EMAIL_RE.findall(text))
        if not count:
            continue
        category, reason = category_for(path, text)
        rows.append((str(path), count, category, reason))
        category_counts[category] += count
        total_occurrences += count

    print(f"EMAIL_CLASSIFICATION_FILE_COUNT={len(rows)}")
    print(f"EMAIL_CLASSIFICATION_TOTAL_OCCURRENCES={total_occurrences}")
    for category in sorted(category_counts):
        print(f"EMAIL_CATEGORY_{category}={category_counts[category]}")
    print("EMAIL_CLASSIFICATION_ROWS_BEGIN")
    for path, count, category, reason in rows:
        print(f"{path}\tcount={count}\tcategory={category}\treason={reason}")
    print("EMAIL_CLASSIFICATION_ROWS_END")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
