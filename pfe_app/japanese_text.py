"""
Japanese text rendering support.
Uses pyxel-universal-font to display Japanese text in Pyxel.

Note: PyxelUniversalFont is lazy-imported (to reduce startup time due to numpy dependency)
"""

import pyxel
import os
from pfe_app.debug import debug_print

# Global variables for lazy import
_puf_module = None
_puf_import_attempted = False


def _get_puf():
    """Lazy import PyxelUniversalFont module"""
    global _puf_module, _puf_import_attempted

    if _puf_import_attempted:
        return _puf_module

    _puf_import_attempted = True
    try:
        debug_print("[Font] Lazy importing PyxelUniversalFont...")
        import PyxelUniversalFont as puf
        _puf_module = puf
        debug_print("[Font] PyxelUniversalFont imported successfully")
    except ImportError:
        debug_print("[Font] Warning: pyxel-universal-font not installed. Falling back to ASCII only.")
        _puf_module = None

    return _puf_module


def _default_bdf_font_path() -> str:
    """Find a bundled pixel BDF font if one is available."""
    candidates = [
        "assets/fonts/umplus_j10r.bdf",
        "assets/fonts/misaki_gothic.bdf",
    ]
    try:
        pyxel_dir = os.path.dirname(pyxel.__file__)
        candidates.extend([
            os.path.join(pyxel_dir, "examples", "assets", "umplus_j10r.bdf"),
            os.path.join(pyxel_dir, "examples", "assets", "umplus_j12r.bdf"),
        ])
    except Exception:
        pass

    for path in candidates:
        if path and os.path.exists(path):
            return path
    return ""


class JapaneseText:
    """Japanese text rendering helper"""

    def __init__(self, font_path=None, backend="auto", bdf_font_path=None, lazy_init=True):
        self.writer = None
        self.bdf_font = None
        self.font_path = font_path
        self.backend = (backend or "auto").lower()
        self.bdf_font_path = bdf_font_path
        self.font_size = 8
        self._initialized = False
        self._lazy_init = lazy_init

        # Initialize immediately if lazy_init=False
        if not lazy_init:
            self._ensure_initialized()

    def _ensure_initialized(self):
        """Initialize font if necessary"""
        if self._initialized:
            return

        self._initialized = True

        if self.backend in ("auto", "bdf") and self._init_bdf_font():
            return

        if self.backend == "bdf":
            debug_print("[Font] BDF backend requested but unavailable, using Pyxel default font")
            return

        puf = _get_puf()
        if puf is not None:
            self._init_universal_font(puf)
        else:
            debug_print("[Font] Universal font not available, using Pyxel default font")

    def _init_bdf_font(self) -> bool:
        """Initialize Pyxel BDF font."""
        font_path = self.bdf_font_path or _default_bdf_font_path()
        if not font_path:
            debug_print("[Font] No BDF font found")
            return False

        try:
            self.bdf_font = pyxel.Font(font_path)
            debug_print(f"[Font] BDF font loaded: {font_path}")
            return True
        except Exception as e:
            debug_print(f"[Font] Failed to initialize BDF font: {e}")
            self.bdf_font = None
            return False

    def _init_universal_font(self, puf):
        """Initialize PyxelUniversalFont"""
        try:
            # Use specified font path if provided
            if self.font_path and os.path.exists(self.font_path):
                self.writer = puf.Writer(self.font_path)
                debug_print(f"[Font] Universal font loaded: {self.font_path}")
            else:
                # Use default font
                # Look for PyxelUniversalFont's default fonts
                try:
                    # Try built-in fonts like misaki_gothic
                    self.writer = puf.Writer("misaki_gothic.ttf")
                    debug_print("[Font] Universal font loaded: misaki_gothic.ttf")
                except:
                    # Fallback: use first available font
                    try:
                        available = puf.get_available_fonts()
                        if available:
                            first_font = available[0]
                            self.writer = puf.Writer(first_font)
                            debug_print(f"[Font] Universal font loaded: {first_font}")
                        else:
                            debug_print("[Font] No fonts available, using Pyxel default")
                            self.writer = None
                    except:
                        debug_print("[Font] Failed to load any universal font")
                        self.writer = None
        except Exception as e:
            debug_print(f"[Font] Failed to initialize universal font: {e}")
            self.writer = None

    def draw_text(self, x: int, y: int, text: str, color: int):
        """
        Draw Japanese text

        Args:
            x: X coordinate
            y: Y coordinate
            text: Text to display
            color: Pyxel color (0-15)
        """
        if not text:
            return

        # Lazy initialization
        self._ensure_initialized()

        if self.bdf_font:
            try:
                pyxel.text(x, y, text, color, self.bdf_font)
                return
            except Exception as e:
                debug_print(f"[Font] Error drawing text with BDF font: {e}")

        # If Universal font is available
        if self.writer:
            try:
                # PyxelUniversalFont.Writer.draw(x, y, text, size, color)
                self.writer.draw(x, y, text, self.font_size, color)
                return
            except Exception as e:
                debug_print(f"[Font] Error drawing text with universal font: {e}")
                # Fallback

        # Fallback: Pyxel's default font (ASCII only)
        pyxel.text(x, y, text, color)

    def get_text_width(self, text: str) -> int:
        """Get text width"""
        if not text:
            return 0

        # Lazy initialization
        self._ensure_initialized()

        if self.bdf_font:
            try:
                return self.bdf_font.text_width(text)
            except Exception:
                pass

        # If Universal font is available
        if self.writer:
            try:
                # 4 pixels per character for ASCII only
                if all(ord(c) < 128 for c in text):
                    return len(text) * 4
                else:
                    # 8 pixels per character (font size) for Japanese text
                    return len(text) * self.font_size
            except:
                pass

        # Fallback: Pyxel default (4 pixels per character)
        return len(text) * 4


# Global instance
_japanese_text = None
_font_path_config = None
_font_backend_config = "auto"
_bdf_font_path_config = None
_small_writer = None
_small_writer_attempted = False


def init_japanese_text(font_path=None, backend="auto", bdf_font_path=None):
    """
    Initialize Japanese text system (only saves config, actual initialization is deferred)

    Args:
        font_path: Path to font file (optional)
        backend: auto, bdf, or ttf
        bdf_font_path: Path to BDF font file (optional)
    """
    global _japanese_text, _font_path_config, _font_backend_config, _bdf_font_path_config
    global _small_writer, _small_writer_attempted
    _font_path_config = font_path
    _font_backend_config = backend or "auto"
    _bdf_font_path_config = bdf_font_path
    _small_writer = None
    _small_writer_attempted = False
    # Lazy initialization: create instance but defer font loading
    _japanese_text = JapaneseText(
        font_path=font_path,
        backend=_font_backend_config,
        bdf_font_path=bdf_font_path,
        lazy_init=True,
    )
    return _japanese_text


def draw_japanese_text(x: int, y: int, text: str, color: int):
    """Draw Japanese text (global function)"""
    global _japanese_text, _font_path_config, _font_backend_config, _bdf_font_path_config
    if _japanese_text is None:
        _japanese_text = JapaneseText(
            font_path=_font_path_config,
            backend=_font_backend_config,
            bdf_font_path=_bdf_font_path_config,
            lazy_init=True,
        )
    _japanese_text.draw_text(x, y, text, color)


def get_japanese_text_width(text: str) -> int:
    """Get Japanese text width (global function)"""
    global _japanese_text, _font_path_config, _font_backend_config, _bdf_font_path_config
    if _japanese_text is None:
        _japanese_text = JapaneseText(
            font_path=_font_path_config,
            backend=_font_backend_config,
            bdf_font_path=_bdf_font_path_config,
            lazy_init=True,
        )
    return _japanese_text.get_text_width(text)


def _get_small_writer():
    """Return a small TTF writer for compact labels when non-ASCII text is needed."""
    global _small_writer, _small_writer_attempted
    if _small_writer_attempted:
        return _small_writer

    _small_writer_attempted = True
    puf = _get_puf()
    if puf is None:
        return None

    candidates = []
    if _font_path_config and os.path.exists(_font_path_config):
        candidates.append(_font_path_config)
    candidates.extend(["misaki_gothic.ttf", "IPA_Gothic.ttf"])

    for candidate in candidates:
        try:
            _small_writer = puf.Writer(candidate)
            return _small_writer
        except Exception:
            continue
    return None


def draw_japanese_text_small(x: int, y: int, text: str, color: int, size: int = 6):
    """Draw compact text. ASCII uses Pyxel's small font; Japanese uses PUF if available."""
    if not text:
        return

    if all(ord(c) < 128 for c in text):
        pyxel.text(x, y, text, color)
        return

    writer = _get_small_writer()
    if writer:
        try:
            writer.draw(x, y, text, size, color)
            return
        except Exception as e:
            debug_print(f"[Font] Error drawing small text: {e}")

    draw_japanese_text(x, y, text, color)


def get_japanese_text_width_small(text: str, size: int = 6) -> int:
    """Estimate compact text width."""
    if not text:
        return 0
    width = 0
    for char in text:
        width += 4 if ord(char) < 128 else size
    return width
