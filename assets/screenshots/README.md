# Screenshots Directory

このディレクトリにROMのスクリーンショットを配置してください。

## ディレクトリ構造

pfe.cfgで定義されている`-DIR=`の値ごとにサブディレクトリを作成します：

```
assets/screenshots/
├── nes/
│   ├── Akumajou Densetsu.png
│   ├── Super Mario Bros.png
│   └── ...
├── gb/
│   ├── Tetris.png
│   ├── Pokemon Red.png
│   └── ...
├── gba/
│   ├── Pokemon Emerald.png
│   └── ...
├── ps1/
│   ├── Final Fantasy VII.png
│   └── ...
└── ...
```

## pfe.cfgとの対応

pfe.cfgで以下のように定義されている場合：

```
#Game Boy Advance
-DIR=gba
-EXT=gba,zip
-TYPE=RA
-CORE=mgba
```

スクリーンショットは`assets/screenshots/gba/`に配置します。

## ファイル名規則

ROMファイル名（拡張子を除く）と同じ名前のPNGまたはJPGファイルを配置します：

```
pfe.cfg: -DIR=nes
ROM: /path/to/nes/Akumajou Densetsu.nes
Screenshot: assets/screenshots/nes/Akumajou Densetsu.png
```

または

```
Screenshot: assets/screenshots/nes/Akumajou Densetsu.jpg
```

## 推奨画像サイズ

- 144x112ピクセル以上を推奨
- より大きい画像も自動的にリサイズされます（144x112に縮小）
- 小さい画像は引き延ばされて粗くなります

## サポート形式

- PNG (.png)
- JPEG (.jpg, .jpeg)
