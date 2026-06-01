"""Pygame image cache helpers."""

from __future__ import annotations

from pathlib import Path

import pygame as pg

_FIG_DIR: Path = Path("assets") / "fig"
_IMAGE_CACHE: dict[tuple[str, tuple[int, int]], pg.Surface] = {}


def load_scaled_image(image_name: str, image_size: tuple[int, int]) -> pg.Surface:
    """Load and scale an image from assets/fig only once."""
    cache_key = (image_name, image_size)
    cached = _IMAGE_CACHE.get(cache_key)
    if cached is None:
        image = pg.image.load(_FIG_DIR / image_name)
        cached = pg.transform.scale(image, image_size)
        _IMAGE_CACHE[cache_key] = cached
    return cached
