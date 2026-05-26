"""
Fast image loading and conversion for PFE.

This module follows the same core idea as PVNM's image path:
Pillow performs fixed-palette quantization in C, then the palette-index bytes
are copied into a pyxel.Image in one operation. It avoids per-pixel pset loops.
"""

from __future__ import annotations

import ctypes
import atexit
import hashlib
import json
import os
import time
import unicodedata
from collections import OrderedDict
from dataclasses import dataclass

import pyxel
from PIL import Image, ImageOps

from pfe_app.debug import debug_print, trace
from pfe_app.palette_manager import get_palette_hash, get_pillow_palette_image


SLOW_IMAGE_MS = 80.0


@dataclass
class CachedImage:
    image: pyxel.Image
    width: int
    height: int
    path: str
    source: str


def _existing_path_variant(path: str) -> str | None:
    if not path:
        return None
    if os.path.exists(path):
        return path
    for form in ("NFC", "NFD"):
        try:
            candidate = unicodedata.normalize(form, path)
        except Exception:
            continue
        if candidate != path and os.path.exists(candidate):
            return candidate
    return None


def _safe_int(value, default: int = 0) -> int:
    try:
        return int(value)
    except Exception:
        return default


class ImageCache:
    """Load, quantize, disk-cache, and memory-cache pyxel.Image objects."""

    def __init__(
        self,
        base_dir: str = ".",
        cache_dir: str = "data/image_cache",
        memory_limit: int = 96,
    ):
        self.base_dir = os.path.abspath(base_dir)
        self.cache_dir = os.path.abspath(cache_dir)
        self.memory_limit = max(8, int(memory_limit))
        self._memory: OrderedDict[tuple, CachedImage] = OrderedDict()
        self._source_size_cache: dict[str, tuple[str, tuple[int, int]]] = {}
        self._size_cache_path = os.path.join(self.cache_dir, "source_sizes.json")
        self._size_cache_entries: dict[str, dict] | None = None
        self._size_cache_dirty = False
        self._size_cache_updates = 0
        self.last_access_source = ""
        self.last_access_elapsed_ms = 0.0
        try:
            os.makedirs(self.cache_dir, exist_ok=True)
        except Exception as e:
            debug_print(f"[ImageCache] Failed to create cache dir: {e}")
        atexit.register(self.flush_metadata)

    def resolve(self, path: str) -> str | None:
        if not path:
            return None
        candidate = path if os.path.isabs(path) else os.path.join(self.base_dir, path)
        return _existing_path_variant(os.path.abspath(candidate))

    def source_size(self, path: str) -> tuple[int, int]:
        resolved = self.resolve(path)
        if not resolved:
            return 0, 0
        try:
            source_sig = self._source_signature(resolved)
        except Exception as e:
            debug_print(f"[ImageCache] source stat failed {resolved}: {e}")
            return 0, 0

        cached = self._source_size_cache.get(resolved)
        if cached and cached[0] == source_sig:
            return cached[1]

        persistent_size = self._get_persistent_source_size(resolved, source_sig)
        if persistent_size is not None:
            self._source_size_cache[resolved] = (source_sig, persistent_size)
            trace(
                f"[ImageCache] source_size source=metadata path={self._short_path(resolved)} "
                f"size={persistent_size[0]}x{persistent_size[1]}"
            )
            return persistent_size

        t0 = time.perf_counter()
        try:
            with Image.open(resolved) as img:
                size = (int(img.width), int(img.height))
        except Exception as e:
            debug_print(f"[ImageCache] source_size failed {resolved}: {e}")
            size = (0, 0)
        self._source_size_cache[resolved] = (source_sig, size)
        if size[0] > 0 and size[1] > 0:
            self._set_persistent_source_size(resolved, source_sig, size)
        elapsed = (time.perf_counter() - t0) * 1000.0
        trace(
            f"[ImageCache] source_size source=image path={self._short_path(resolved)} "
            f"size={size[0]}x{size[1]} total={elapsed:.1f}ms"
        )
        if elapsed >= 20.0:
            debug_print(
                f"[ImageCache] slow source_size path={self._short_path(resolved)} "
                f"size={size[0]}x{size[1]} {elapsed:.1f}ms"
            )
        return size

    def get_fit(
        self,
        path: str,
        max_width: int,
        max_height: int,
        upscale: bool = True,
    ) -> CachedImage | None:
        src_w, src_h = self.source_size(path)
        if src_w <= 0 or src_h <= 0 or max_width <= 0 or max_height <= 0:
            return None
        scale = min(max_width / src_w, max_height / src_h)
        if not upscale:
            scale = min(1.0, scale)
        width = max(1, int(src_w * scale))
        height = max(1, int(src_h * scale))
        return self.get(path, width, height)

    def get_fit_cached(
        self,
        path: str,
        max_width: int,
        max_height: int,
        upscale: bool = True,
    ) -> CachedImage | None:
        """Return a memory/disk cached fit without running Pillow conversion."""
        src_w, src_h = self.source_size(path)
        if src_w <= 0 or src_h <= 0 or max_width <= 0 or max_height <= 0:
            return None
        scale = min(max_width / src_w, max_height / src_h)
        if not upscale:
            scale = min(1.0, scale)
        width = max(1, int(src_w * scale))
        height = max(1, int(src_h * scale))
        return self.get_cached(path, width, height)

    def get_cached(self, path: str, width: int = 0, height: int = 0) -> CachedImage | None:
        """Return only memory/disk cached data; never resize or quantize the source."""
        t0 = time.perf_counter()
        resolved = self.resolve(path)
        if not resolved:
            return None

        if width <= 0 or height <= 0:
            src_w, src_h = self.source_size(resolved)
            if src_w <= 0 or src_h <= 0:
                return None
            width = src_w if width <= 0 else width
            height = src_h if height <= 0 else height

        width = max(1, _safe_int(width, 1))
        height = max(1, _safe_int(height, 1))
        source_sig, key = self._memory_key(resolved, width, height)

        cached = self._memory.get(key)
        if cached is not None:
            self._memory.move_to_end(key)
            self._trace_access("get_cached", "memory", resolved, width, height, t0)
            return cached

        disk_t0 = time.perf_counter()
        raw = self._load_raw_cache(resolved, width, height, source_sig)
        disk_ms = (time.perf_counter() - disk_t0) * 1000.0
        if raw is None:
            self._trace_access(
                "get_cached",
                "miss",
                resolved,
                width,
                height,
                t0,
                detail=f"disk={disk_ms:.1f}ms",
            )
            return None

        image_t0 = time.perf_counter()
        item = self._image_from_raw(resolved, width, height, raw, "disk")
        image_ms = (time.perf_counter() - image_t0) * 1000.0
        self._remember(key, item)
        elapsed = self._trace_access(
            "get_cached",
            "disk",
            resolved,
            width,
            height,
            t0,
            detail=f"disk={disk_ms:.1f}ms image={image_ms:.1f}ms",
        )
        self._debug_slow(resolved, width, height, "disk", elapsed, disk_ms=disk_ms, image_ms=image_ms)
        return item

    def get(self, path: str, width: int = 0, height: int = 0) -> CachedImage | None:
        t0 = time.perf_counter()
        resolved = self.resolve(path)
        if not resolved:
            debug_print(f"[ImageCache] Missing image: {path}")
            return None

        if width <= 0 or height <= 0:
            src_w, src_h = self.source_size(resolved)
            if src_w <= 0 or src_h <= 0:
                return None
            width = src_w if width <= 0 else width
            height = src_h if height <= 0 else height

        width = max(1, _safe_int(width, 1))
        height = max(1, _safe_int(height, 1))
        source_sig, key = self._memory_key(resolved, width, height)

        cached = self._memory.get(key)
        if cached is not None:
            self._memory.move_to_end(key)
            self._trace_access("get", "memory", resolved, width, height, t0)
            return cached

        disk_t0 = time.perf_counter()
        raw = self._load_raw_cache(resolved, width, height, source_sig)
        disk_ms = (time.perf_counter() - disk_t0) * 1000.0
        source = "disk"
        process_ms = 0.0
        save_ms = 0.0
        if raw is None:
            process_t0 = time.perf_counter()
            raw = self._process_to_raw(resolved, width, height)
            process_ms = (time.perf_counter() - process_t0) * 1000.0
            source = "process"
            if raw is not None:
                save_t0 = time.perf_counter()
                self._save_raw_cache(resolved, width, height, source_sig, raw)
                save_ms = (time.perf_counter() - save_t0) * 1000.0
        if raw is None:
            self._trace_access(
                "get",
                "miss",
                resolved,
                width,
                height,
                t0,
                detail=f"disk={disk_ms:.1f}ms process={process_ms:.1f}ms",
            )
            return None

        image_t0 = time.perf_counter()
        item = self._image_from_raw(resolved, width, height, raw, source)
        image_ms = (time.perf_counter() - image_t0) * 1000.0
        self._remember(key, item)

        elapsed = self._trace_access(
            "get",
            source,
            resolved,
            width,
            height,
            t0,
            detail=(
                f"disk={disk_ms:.1f}ms process={process_ms:.1f}ms "
                f"save={save_ms:.1f}ms image={image_ms:.1f}ms"
            ),
        )
        self._debug_slow(
            resolved,
            width,
            height,
            source,
            elapsed,
            disk_ms=disk_ms,
            process_ms=process_ms,
            save_ms=save_ms,
            image_ms=image_ms,
        )
        return item

    def invalidate(self, path: str) -> None:
        resolved = self.resolve(path)
        if not resolved:
            return
        for key in [key for key in self._memory if key[0] == resolved]:
            del self._memory[key]
        self._source_size_cache.pop(resolved, None)
        self._delete_persistent_source_size(resolved)

    def clear_memory(self) -> None:
        self._memory.clear()

    def flush_metadata(self) -> None:
        """Persist delayed metadata cache writes."""
        self._save_size_cache(force=True)

    def _remember(self, key: tuple, item: CachedImage) -> None:
        self._memory[key] = item
        self._memory.move_to_end(key)
        while len(self._memory) > self.memory_limit:
            self._memory.popitem(last=False)

    def _memory_key(self, resolved: str, width: int, height: int) -> tuple[str, tuple]:
        source_sig = self._source_signature(resolved)
        return source_sig, (resolved, width, height, get_palette_hash(), source_sig)

    def _source_signature(self, resolved: str) -> str:
        stat = os.stat(resolved)
        return f"{stat.st_mtime_ns:x}{stat.st_size:x}"

    def _short_path(self, resolved: str) -> str:
        try:
            rel = os.path.relpath(resolved, self.base_dir)
            if rel != ".." and not rel.startswith(".." + os.sep):
                return rel
        except Exception:
            pass
        return os.path.basename(resolved)

    def _trace_access(
        self,
        mode: str,
        source: str,
        resolved: str,
        width: int,
        height: int,
        start_time: float,
        detail: str = "",
    ) -> float:
        elapsed = (time.perf_counter() - start_time) * 1000.0
        self.last_access_source = source
        self.last_access_elapsed_ms = elapsed
        suffix = f" {detail}" if detail else ""
        trace(
            f"[ImageCache] {mode} source={source} path={self._short_path(resolved)} "
            f"size={width}x{height} total={elapsed:.1f}ms{suffix}"
        )
        return elapsed

    def _debug_slow(
        self,
        resolved: str,
        width: int,
        height: int,
        source: str,
        elapsed: float,
        **parts: float,
    ) -> None:
        if elapsed < SLOW_IMAGE_MS:
            return
        detail = " ".join(f"{name}={value:.1f}ms" for name, value in parts.items())
        debug_print(
            f"[ImageCache] slow path={self._short_path(resolved)} "
            f"{width}x{height} source={source} total={elapsed:.1f}ms {detail}"
        )

    def _cache_rel(self, resolved: str) -> str:
        return os.path.relpath(resolved, self.base_dir)

    def _source_size_cache_key(self, resolved: str) -> str:
        rel = self._cache_rel(resolved)
        return hashlib.md5(rel.encode("utf-8", "ignore")).hexdigest()

    def _load_size_cache(self) -> dict[str, dict]:
        if self._size_cache_entries is not None:
            return self._size_cache_entries

        self._size_cache_entries = self._read_size_cache_entries()
        return self._size_cache_entries

    def _save_size_cache(self, force: bool = False) -> None:
        if not self._size_cache_dirty or self._size_cache_entries is None:
            return
        if not force and self._size_cache_updates < 16:
            return

        entries = dict(self._read_size_cache_entries())
        entries.update(self._size_cache_entries)
        self._size_cache_entries = entries
        payload = {
            "version": 1,
            "entries": entries,
        }
        tmp_path = self._size_cache_path + ".tmp"
        try:
            os.makedirs(os.path.dirname(self._size_cache_path), exist_ok=True)
            with open(tmp_path, "w", encoding="utf-8") as f:
                json.dump(payload, f, ensure_ascii=False, separators=(",", ":"))
            os.replace(tmp_path, self._size_cache_path)
            self._size_cache_dirty = False
            self._size_cache_updates = 0
        except Exception as e:
            debug_print(f"[ImageCache] Failed to write size metadata: {e}")
            try:
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)
            except Exception:
                pass

    def _read_size_cache_entries(self) -> dict[str, dict]:
        try:
            with open(self._size_cache_path, "r", encoding="utf-8") as f:
                payload = json.load(f)
            if isinstance(payload, dict):
                entries = payload.get("entries", payload)
                if isinstance(entries, dict):
                    return entries
        except FileNotFoundError:
            pass
        except Exception as e:
            debug_print(f"[ImageCache] Failed to merge size metadata: {e}")
        return {}

    def _get_persistent_source_size(self, resolved: str, source_sig: str) -> tuple[int, int] | None:
        entries = self._load_size_cache()
        item = entries.get(self._source_size_cache_key(resolved))
        if not isinstance(item, dict):
            return None
        if item.get("sig") != source_sig:
            return None
        width = _safe_int(item.get("width"), 0)
        height = _safe_int(item.get("height"), 0)
        if width <= 0 or height <= 0:
            return None
        return width, height

    def _set_persistent_source_size(self, resolved: str, source_sig: str, size: tuple[int, int]) -> None:
        entries = self._load_size_cache()
        entries[self._source_size_cache_key(resolved)] = {
            "rel": self._cache_rel(resolved),
            "sig": source_sig,
            "width": int(size[0]),
            "height": int(size[1]),
        }
        self._size_cache_dirty = True
        self._size_cache_updates += 1
        self._save_size_cache(force=False)

    def _delete_persistent_source_size(self, resolved: str) -> None:
        entries = self._load_size_cache()
        key = self._source_size_cache_key(resolved)
        if key in entries:
            del entries[key]
            self._size_cache_dirty = True
            self._size_cache_updates += 1
            self._save_size_cache(force=True)

    def _image_from_raw(
        self,
        resolved: str,
        width: int,
        height: int,
        raw: bytes,
        source: str,
    ) -> CachedImage:
        pyx_img = pyxel.Image(width, height)
        self._fill_pyxel_image(pyx_img, raw, width, height)
        return CachedImage(pyx_img, width, height, resolved, source)

    def _cache_path(self, resolved: str, width: int, height: int, source_sig: str) -> str:
        rel = self._cache_rel(resolved)
        digest = hashlib.md5(rel.encode("utf-8", "ignore")).hexdigest()[:14]
        return os.path.join(
            self.cache_dir,
            f"v1_{digest}_{width}x{height}_{get_palette_hash()}_{source_sig}.idx",
        )

    def _load_raw_cache(
        self,
        resolved: str,
        width: int,
        height: int,
        source_sig: str,
    ) -> bytes | None:
        cache_path = self._cache_path(resolved, width, height, source_sig)
        try:
            with open(cache_path, "rb") as f:
                data = f.read()
            if len(data) == width * height:
                return data
        except Exception:
            return None
        return None

    def _save_raw_cache(
        self,
        resolved: str,
        width: int,
        height: int,
        source_sig: str,
        data: bytes,
    ) -> None:
        cache_path = self._cache_path(resolved, width, height, source_sig)
        try:
            with open(cache_path, "wb") as f:
                f.write(data)
        except Exception as e:
            debug_print(f"[ImageCache] Failed to write cache: {e}")

    def _process_to_raw(self, resolved: str, width: int, height: int) -> bytes | None:
        try:
            with Image.open(resolved) as src:
                src = ImageOps.exif_transpose(src)
                if "A" in src.getbands():
                    rgba = src.convert("RGBA").resize((width, height), Image.Resampling.LANCZOS)
                    bg = Image.new("RGB", (width, height), (0, 0, 0))
                    bg.paste(rgba, mask=rgba.split()[3])
                    rgb = bg
                else:
                    rgb = src.convert("RGB").resize((width, height), Image.Resampling.LANCZOS)
                pal_img = get_pillow_palette_image()
                quantized = rgb.quantize(palette=pal_img, dither=Image.Dither.NONE)
                data = quantized.tobytes()
                if len(data) != width * height:
                    return None
                return data
        except Exception as e:
            debug_print(f"[ImageCache] Process failed {resolved}: {e}")
            return None

    @staticmethod
    def _fill_pyxel_image(pyx_img: pyxel.Image, data: bytes, width: int, height: int) -> None:
        try:
            ctypes.memmove(pyx_img.data_ptr(), data, len(data))
        except Exception:
            # Compatibility fallback for older pyxel builds.
            for y in range(height):
                row = y * width
                for x in range(width):
                    pyx_img.pset(x, y, data[row + x])
