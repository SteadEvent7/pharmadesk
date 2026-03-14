from __future__ import annotations

import sys
from pathlib import Path

from app.config import BASE_DIR, STORAGE_ROOT

try:
    from PIL import Image, ImageTk
except ImportError:  # pragma: no cover
    Image = None
    ImageTk = None


def _candidate_logo_paths() -> list[Path]:
    roots = [BASE_DIR, STORAGE_ROOT]
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        roots.insert(0, Path(meipass))

    candidates: list[Path] = []
    for root in roots:
        assets_dir = Path(root) / "assets"
        for extension in ("png", "jpg", "jpeg", "webp"):
            candidates.append(assets_dir / f"logo.{extension}")
    return candidates


def get_brand_logo_path() -> Path | None:
    for path in _candidate_logo_paths():
        if path.exists():
            return path
    return None


def load_brand_logo(size: tuple[int, int]):
    logo_path = get_brand_logo_path()
    if logo_path is None or Image is None or ImageTk is None:
        return None

    image = Image.open(logo_path)
    image.thumbnail(size, Image.Resampling.LANCZOS)
    return ImageTk.PhotoImage(image)