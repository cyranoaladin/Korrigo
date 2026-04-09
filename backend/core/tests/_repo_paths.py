from __future__ import annotations

import os
from pathlib import Path


def repo_root_from(anchor: str | Path) -> Path:
    env_root = os.environ.get("KORRIGO_REPO_ROOT")
    if env_root:
        candidate = Path(env_root).resolve()
        if _looks_like_repo_root(candidate):
            return candidate

    anchor_path = Path(anchor).resolve()
    candidates = list(anchor_path.parents) + [Path.cwd().resolve(), Path("/repo")]
    for candidate in candidates:
        if _looks_like_repo_root(candidate):
            return candidate

    raise FileNotFoundError("Could not resolve Korrigo repository root")


def _looks_like_repo_root(path: Path) -> bool:
    return (
        path.is_dir()
        and (path / "backend").is_dir()
        and (path / "infra").is_dir()
        and (path / "scripts").is_dir()
    )
