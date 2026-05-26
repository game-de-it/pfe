"""
256-color palette support for PFE.

The first 16 colors are kept compatible with Pyxel's default UI palette.
Image conversion uses the full 0-255 Pyxel palette, so screenshots can use
far more color detail without changing existing theme indices.
"""

from __future__ import annotations

import hashlib
import os
from typing import Iterable

import pyxel

from pfe_app.debug import debug_print


_DEFAULT_PYXEL_16 = [
    0x000000, 0x2B335F, 0x7E2072, 0x19959C,
    0x8B4852, 0x395C98, 0xA9C1FF, 0xEEEEEE,
    0xD4186C, 0xD38441, 0xE9C35B, 0x70C6A9,
    0x7696DE, 0xA3A3A3, 0xFF9798, 0xEDC7B0,
]

_palette_rgb: list[tuple[int, int, int]] | None = None
_palette_hash = ""


def _rgb_tuple(value: int) -> tuple[int, int, int]:
    return ((value >> 16) & 0xFF, (value >> 8) & 0xFF, value & 0xFF)


def _rgb_int(rgb: tuple[int, int, int]) -> int:
    return (int(rgb[0]) << 16) | (int(rgb[1]) << 8) | int(rgb[2])


def _current_ui_colors() -> list[tuple[int, int, int]]:
    colors = []
    for i in range(16):
        try:
            colors.append(_rgb_tuple(int(pyxel.colors[i])))
        except Exception:
            colors.append(_rgb_tuple(_DEFAULT_PYXEL_16[i]))
    return colors


def _generated_image_colors() -> list[tuple[int, int, int]]:
    """Generate 240 RGB colors for image slots 16-255."""
    colors: list[tuple[int, int, int]] = []
    # 6 x 8 x 5 = 240 colors. This is a compact, even color cube.
    for r_i in range(6):
        for g_i in range(8):
            for b_i in range(5):
                r = round(r_i * 255 / 5)
                g = round(g_i * 255 / 7)
                b = round(b_i * 255 / 4)
                colors.append((r, g, b))
    return colors[:240]


def _read_pyxpal(path: str) -> list[tuple[int, int, int]] | None:
    try:
        colors: list[tuple[int, int, int]] = []
        with open(path, encoding="utf-8") as f:
            for line in f:
                text = line.strip().lstrip("#")
                if not text or text.startswith(";"):
                    continue
                if len(text) < 6:
                    continue
                value = int(text[:6], 16)
                colors.append(_rgb_tuple(value))
                if len(colors) >= 256:
                    break
        if not colors:
            return None
        while len(colors) < 256:
            colors.append((0, 0, 0))
        return colors[:256]
    except Exception as e:
        debug_print(f"[Palette] Failed to read palette {path}: {e}")
        return None


def _write_pyxpal(path: str, colors: Iterable[tuple[int, int, int]]) -> None:
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for r, g, b in list(colors)[:256]:
            f.write(f"{int(r) & 0xFF:02x}{int(g) & 0xFF:02x}{int(b) & 0xFF:02x}\n")


def _build_default_palette() -> list[tuple[int, int, int]]:
    return _current_ui_colors() + _generated_image_colors()


def _apply_palette(colors: list[tuple[int, int, int]]) -> None:
    if len(pyxel.colors) < 256:
        for _ in range(256 - len(pyxel.colors)):
            pyxel.colors.append(0)
    for i, rgb in enumerate(colors[:256]):
        pyxel.colors[i] = _rgb_int(rgb)


def init_palette(config=None) -> list[tuple[int, int, int]]:
    """Initialize pyxel.colors with a 256-color palette and return RGB tuples."""
    global _palette_rgb, _palette_hash

    palette_path = ""
    preserve_ui = True
    if config is not None:
        palette_path = getattr(config, "get_palette_path", lambda: "")() or ""
        preserve_ui = getattr(config, "preserve_ui_palette", lambda: True)()

    colors = None
    if palette_path:
        resolved = palette_path if os.path.isabs(palette_path) else os.path.abspath(palette_path)
        colors = _read_pyxpal(resolved)
        if colors:
            debug_print(f"[Palette] Loaded palette: {resolved}")

    if colors is None:
        colors = _build_default_palette()
        default_path = palette_path or "data/pfe_generated.pyxpal"
        try:
            _write_pyxpal(default_path, colors)
            debug_print(f"[Palette] Generated default palette: {default_path}")
        except Exception as e:
            debug_print(f"[Palette] Failed to write generated palette: {e}")

    if preserve_ui:
        colors = _current_ui_colors() + colors[16:256]

    while len(colors) < 256:
        colors.append((0, 0, 0))
    colors = colors[:256]

    _apply_palette(colors)
    payload = bytes(channel for rgb in colors for channel in rgb)
    _palette_hash = hashlib.md5(payload).hexdigest()[:8]
    _palette_rgb = colors
    debug_print(f"[Palette] Active palette hash={_palette_hash} colors={len(colors)}")
    return colors


def get_palette_rgb() -> list[tuple[int, int, int]]:
    global _palette_rgb
    if _palette_rgb is None:
        _palette_rgb = _build_default_palette()
    return _palette_rgb


def get_palette_hash() -> str:
    return _palette_hash or "default"


def get_pillow_palette_image():
    """Return a Pillow palette image suitable for fixed-palette quantize()."""
    from PIL import Image

    flat: list[int] = []
    for r, g, b in get_palette_rgb()[:256]:
        flat.extend([int(r) & 0xFF, int(g) & 0xFF, int(b) & 0xFF])
    while len(flat) < 256 * 3:
        flat.append(0)
    pal_img = Image.new("P", (1, 1))
    pal_img.putpalette(flat)
    return pal_img
