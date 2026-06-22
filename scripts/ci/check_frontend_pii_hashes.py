#!/usr/bin/env python3
"""Fail if known real PII reappears in the frontend bundle sources.

The denylist stores only SHA-256 hashes of normalized values. Do not add raw
names or emails here; compute their normalized hash offline and store the hash.
"""

from __future__ import annotations

import argparse
import hashlib
import re
import sys
import unicodedata
from pathlib import Path


DENY_HASHES = {
    "04af2ff21ede3322abb962892cc0e65c083a4d89691fbfa807e30a9376a91130": "person_name",
    "87b5277e9430319f0d4f9b953fd9ae673dbf3d30e6cb3abb33aaa2a6ce317598": "person_name",
    "ed1b1c34ebd2356bcf7bd27b852c391405a3819ca4d1769ba1e5fb56d3a12b15": "person_name",
    "b7d436a5e53291fdb55662ac9ebc0cb98921b7809c263e8a2959470a6b9f6a0c": "person_name",
    "343de1a755a6b8da8979c8b65e734fc4cbc20a20fcf87ec39fd50e7edfd2c02f": "person_name",
    "ee02be8e97d3e4215738f2d7d640b7fd777bc0b3bd7dabbf17d3d7ae30b6e568": "person_name",
    "118033b0d5b1174c72607bfed7a154dc15bd0b2773ede68891ee3a8717eec72f": "person_name",
    "647515845079c96c51697ab45879cc6463b0d0d83467e2b3174b4a2a641a5a34": "person_name",
    "8f68ce1fe00e602fd742e3e6142290019075e0763ed762ab6fa654bb74bb6ea4": "person_name",
    "1ea31c0ec0f64b1bbcf311f8c7e049457e533c69684ff5fa5f8a833f760c1efb": "person_name",
    "f1e9cb2b7b545a9a9211644bd65cd40e4b454f2ba33479b230d217c4b804d8bb": "person_name",
    "dbcac5553cc7ce9a7e24f19ff2834b2b06243ba76313292678fb25d727fb94ae": "person_name",
    "6a242b7c8c4523ecfb53d88579a42e5a7731decf71072aaa89cc3d87156da51e": "person_name",
    "0783e121e74b90e587c059801f8661163a81d72f020f5a806c564c7b0d443686": "person_name",
    "a22d8d0d8b2a75fb76333a95223ec2e45ec89e24f47dd2bec3f6e371240f280b": "person_name",
    "aa8fe06d2512e4f980a797b5331542e179c795b807eac265f54f07ab5c474676": "person_name",
    "dd886c78bf0a379e061536fbf47ecf23744ad756066222e4792e73a3f3dde4bd": "person_name",
    "b3587be6cc451fa3559f8d01d7d2c365476510d231ec642f0c59dd5cabe98cb1": "person_name",
    "2586725330c7dbab471345e7d4cf96fa3a088955c35cc6ae11675eaa4a9530b3": "person_name",
    "3842d34bbcfaa585469d1f225fd8f55d4ddd83275674c7d57f2cb7ab33fc252b": "person_name",
    "2e06ddf1da3b9c54093f494fb7c6df2ed3848f03c7dc9e25929278388bbdabf3": "person_name",
    "324656142133897b1189d1231744df4a817d9cf5135c15d37fed4a321761df1d": "direction_email",
    "aed02e4d0af7bcb334dc50690243a247d42329e313480645e09446d2eae022d3": "direction_email",
    "f3c7e693d77e48e517563e4e1220309c52c1acd1a491148fa840cb9a76f1edd0": "direction_email",
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


def digest(value: str) -> str:
    return hashlib.sha256(normalize(value).encode("utf-8")).hexdigest()


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
        if any(part in {"node_modules", "dist", "coverage"} for part in path.parts):
            continue
        yield path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", nargs="?", default="frontend/src")
    args = parser.parse_args()

    root = Path(args.root)
    matches: list[tuple[Path, int, str]] = []
    for path in iter_source_files(root):
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except UnicodeDecodeError:
            continue
        for line_no, line in enumerate(lines, 1):
            for candidate in candidate_values(line):
                kind = DENY_HASHES.get(digest(candidate))
                if kind:
                    matches.append((path, line_no, kind))
                    break

    print(f"PII_HASH_MATCH_COUNT={len(matches)}")
    for path, line_no, kind in matches:
        print(f"{path}:{line_no}: {kind}")
    return 1 if matches else 0


if __name__ == "__main__":
    raise SystemExit(main())
