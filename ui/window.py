"""
ドラゴンクエスト風ウインドウコンポーネント
"""

import pyxel


class DQWindow:
    """ドラゴンクエスト風のウインドウ枠を描画"""

    @staticmethod
    def draw(x: int, y: int, width: int, height: int, bg_color: int = 1, border_color: int = 7):
        """
        DQ風ウインドウを描画

        Args:
            x: X座標
            y: Y座標
            width: 幅
            height: 高さ
            bg_color: 背景色
            border_color: 枠線色
        """
        # 背景を描画
        pyxel.rect(x, y, width, height, bg_color)

        # 外枠（太い線）
        # 上
        pyxel.line(x + 2, y, x + width - 3, y, border_color)
        pyxel.line(x + 2, y + 1, x + width - 3, y + 1, border_color)
        # 下
        pyxel.line(x + 2, y + height - 1, x + width - 3, y + height - 1, border_color)
        pyxel.line(x + 2, y + height - 2, x + width - 3, y + height - 2, border_color)
        # 左
        pyxel.line(x, y + 2, x, y + height - 3, border_color)
        pyxel.line(x + 1, y + 2, x + 1, y + height - 3, border_color)
        # 右
        pyxel.line(x + width - 1, y + 2, x + width - 1, y + height - 3, border_color)
        pyxel.line(x + width - 2, y + 2, x + width - 2, y + height - 3, border_color)

        # 角（2x2ピクセル）
        # 左上
        pyxel.rect(x, y, 2, 2, border_color)
        # 右上
        pyxel.rect(x + width - 2, y, 2, 2, border_color)
        # 左下
        pyxel.rect(x, y + height - 2, 2, 2, border_color)
        # 右下
        pyxel.rect(x + width - 2, y + height - 2, 2, 2, border_color)

        # 内側の影（立体感）
        shadow_color = 0  # 黒
        # 上の影（内側）
        pyxel.line(x + 3, y + 2, x + width - 4, y + 2, shadow_color)
        # 左の影（内側）
        pyxel.line(x + 2, y + 3, x + 2, y + height - 4, shadow_color)

    @staticmethod
    def draw_simple(x: int, y: int, width: int, height: int, bg_color: int = 1, border_color: int = 7):
        """
        シンプルなウインドウ枠を描画

        Args:
            x: X座標
            y: Y座標
            width: 幅
            height: 高さ
            bg_color: 背景色
            border_color: 枠線色
        """
        # 背景
        pyxel.rect(x, y, width, height, bg_color)
        # 外枠
        pyxel.rectb(x, y, width, height, border_color)
        # 内枠（二重線）
        pyxel.rectb(x + 1, y + 1, width - 2, height - 2, border_color)
