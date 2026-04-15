from __future__ import annotations

import logging
import uuid
from pathlib import Path

from django.conf import settings
from PIL import Image

logger = logging.getLogger(__name__)


def _resolve_media_path(file_path: str) -> Path:
    candidate = Path(settings.MEDIA_ROOT) / file_path
    if candidate.exists():
        return candidate
    raw = Path(file_path)
    if raw.exists():
        return raw
    raise FileNotFoundError(f"Media file not found: {file_path}")


def _build_rotated_relative_path(source_rel_path: str) -> str:
    source = Path(source_rel_path)
    suffix = source.suffix or ".png"
    new_name = f"{source.stem}_rot180_{uuid.uuid4().hex[:8]}{suffix}"
    return str(source.with_name(new_name))


def rotate_image_file_180(file_path: str) -> str:
    """
    Rotate an image file by 180 degrees and store the rotated version next to it.

    Returns the new relative path if `file_path` is relative to MEDIA_ROOT.
    The original file is intentionally preserved.
    """
    source_path = _resolve_media_path(file_path)
    rotated_rel_path = _build_rotated_relative_path(file_path)
    rotated_path = Path(settings.MEDIA_ROOT) / rotated_rel_path
    rotated_path.parent.mkdir(parents=True, exist_ok=True)

    with Image.open(source_path) as img:
        rotate_flag = getattr(getattr(Image, "Transpose", Image), "ROTATE_180", Image.ROTATE_180)
        rotated = img.transpose(rotate_flag)
        save_kwargs = {}
        if rotated.format:
            save_kwargs["format"] = rotated.format
        elif img.format:
            save_kwargs["format"] = img.format

        if (save_kwargs.get("format") or "").upper() in {"JPEG", "JPG"} and rotated.mode in {"RGBA", "LA", "P"}:
            rotated = rotated.convert("RGB")

        rotated.save(rotated_path, **save_kwargs)

    logger.info("Rotated media file %s -> %s", file_path, rotated_rel_path)
    return rotated_rel_path
