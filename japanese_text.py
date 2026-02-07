"""
Japanese text rendering support.
Uses pyxel-universal-font to display Japanese text in Pyxel.

Note: PyxelUniversalFont is lazy-imported (to reduce startup time due to numpy dependency)
"""

import pyxel
import os
from debug import debug_print

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


class JapaneseText:
    """Japanese text rendering helper"""

    def __init__(self, font_path=None, lazy_init=True):
        self.writer = None
        self.font_path = font_path
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
        puf = _get_puf()

        if puf is not None:
            self._init_universal_font(puf)
        else:
            debug_print("[Font] Universal font not available, using Pyxel default font")

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


def init_japanese_text(font_path=None):
    """
    Initialize Japanese text system (only saves config, actual initialization is deferred)

    Args:
        font_path: Path to font file (optional)
    """
    global _japanese_text, _font_path_config
    _font_path_config = font_path
    # Lazy initialization: create instance but defer font loading
    if _japanese_text is None:
        _japanese_text = JapaneseText(font_path=font_path, lazy_init=True)
    return _japanese_text


def draw_japanese_text(x: int, y: int, text: str, color: int):
    """Draw Japanese text (global function)"""
    global _japanese_text, _font_path_config
    if _japanese_text is None:
        _japanese_text = JapaneseText(font_path=_font_path_config, lazy_init=True)
    _japanese_text.draw_text(x, y, text, color)


def get_japanese_text_width(text: str) -> int:
    """Get Japanese text width (global function)"""
    global _japanese_text, _font_path_config
    if _japanese_text is None:
        _japanese_text = JapaneseText(font_path=_font_path_config, lazy_init=True)
    return _japanese_text.get_text_width(text)
