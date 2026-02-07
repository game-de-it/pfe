# Fonts Directory

このディレクトリにカスタムフォントファイルを配置してください。

## 使用方法

1. フォントファイル（.ttf, .otfなど）をこのディレクトリに配置
2. `data/pfe.cfg` に `FONT_PATH` を設定

例：
```
FONT_PATH=assets/fonts/myfont.ttf
```

## 推奨フォント

- Noto Sans CJK
- M+ FONTS
- IPAフォント
- 美咲フォント (8x8ピクセル)

## 注意

- フォントファイルは配布物に含まれていません
- ライセンスを確認してからご使用ください
- pyxel-universal-fontモジュールが必要です: `pip install pyxel-universal-font`
