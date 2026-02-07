# PFE Theme Configuration Guide

## Pyxelカラーパレット

Pyxelは16色のパレットを使用します。各色には0〜15の番号が割り当てられています。

| 番号 | 色名 | RGB値 | 16進数 | 説明 |
|------|------|--------|--------|------|
| 0 | Black | (0, 0, 0) | #000000 | 黒 |
| 1 | Dark Blue | (43, 51, 95) | #2B335F | 濃い青 |
| 2 | Dark Purple | (126, 32, 114) | #7E2072 | 濃い紫 |
| 3 | Dark Green | (25, 149, 156) | #19959C | 濃い緑 |
| 4 | Brown | (139, 72, 82) | #8B4852 | 茶色 |
| 5 | Dark Gray | (57, 92, 152) | #395C98 | 濃いグレー |
| 6 | Light Gray | (169, 193, 255) | #A9C1FF | 明るいグレー |
| 7 | White | (238, 238, 238) | #EEEEEE | 白 |
| 8 | Red | (212, 24, 108) | #D4186C | 赤 |
| 9 | Orange | (211, 132, 65) | #D38441 | オレンジ |
| 10 | Yellow | (233, 195, 91) | #E9C35B | 黄色 |
| 11 | Green | (112, 198, 169) | #70C6A9 | 緑 |
| 12 | Blue | (118, 150, 222) | #7696DE | 青 |
| 13 | Indigo | (163, 163, 163) | #A3A3A3 | 藍色/グレー |
| 14 | Pink | (255, 151, 152) | #FF9798 | ピンク |
| 15 | Peach | (237, 199, 176) | #EDC7B0 | ピーチ |

## テーマファイル形式

テーマファイルは `assets/themes/` ディレクトリに配置されるJSONファイルです。

### ファイル命名規則

- ファイル名: `{theme_id}.json` （例: `dark.json`, `my_custom_theme.json`）
- theme_idは英小文字とアンダースコアのみ使用可能
- ファイル名がテーマIDとして使用されます

### テーマファイルの構造

```json
{
  "name": "テーマ名",
  "colors": {
    "background": 0,
    "text": 7,
    "text_selected": 10,
    "border": 7,
    "border_accent": 11,
    "scrollbar": 11,
    "status_bg": 1,
    "help_bg": 1,
    "error": 8,
    "success": 11,
    "info": 12
  }
}
```

### カラーキー一覧

| キー | 用途 | 使用場所 |
|------|------|----------|
| `background` | 背景色 | 画面全体の背景 |
| `text` | 通常テキスト色 | 非選択時のテキスト |
| `text_selected` | 選択テキスト色 | 選択中のアイテム、カテゴリ名、タイトル |
| `border` | 枠線色 | ウィンドウの枠線、境界線 |
| `border_accent` | 枠線アクセント色 | 強調する枠線（現在未使用） |
| `scrollbar` | スクロールバー色 | リスト画面のスクロールバー |
| `status_bg` | ステータスバー背景色 | 画面下部のステータスバー背景 |
| `help_bg` | ヘルプバー背景色 | ヘルプテキストの背景 |
| `error` | エラー色 | エラーメッセージ（現在未使用） |
| `success` | 成功色 | 成功メッセージ（現在未使用） |
| `info` | 情報色 | 情報メッセージ（現在未使用） |

## 組み込みテーマ

### Dark（ダークテーマ）

黒背景に白文字の標準的なダークテーマ。

```json
{
  "name": "Dark",
  "colors": {
    "background": 0,
    "text": 7,
    "text_selected": 10,
    "border": 7,
    "border_accent": 11,
    "scrollbar": 11,
    "status_bg": 1,
    "help_bg": 1,
    "error": 8,
    "success": 11,
    "info": 12
  }
}
```

### Light（ライトテーマ）

白背景に黒文字の明るいテーマ。

```json
{
  "name": "Light",
  "colors": {
    "background": 7,
    "text": 0,
    "text_selected": 8,
    "border": 0,
    "border_accent": 12,
    "scrollbar": 12,
    "status_bg": 13,
    "help_bg": 13,
    "error": 8,
    "success": 11,
    "info": 12
  }
}
```

### Retro（レトロテーマ）

Game Boy風のレトロなグリーンテーマ。

```json
{
  "name": "Retro",
  "colors": {
    "background": 3,
    "text": 11,
    "text_selected": 10,
    "border": 11,
    "border_accent": 10,
    "scrollbar": 10,
    "status_bg": 4,
    "help_bg": 4,
    "error": 8,
    "success": 11,
    "info": 11
  }
}
```

### Neon（ネオンテーマ）

黒背景にピンクとシアンのサイバーパンク風テーマ。

```json
{
  "name": "Neon",
  "colors": {
    "background": 0,
    "text": 14,
    "text_selected": 6,
    "border": 14,
    "border_accent": 6,
    "scrollbar": 6,
    "status_bg": 1,
    "help_bg": 1,
    "error": 8,
    "success": 11,
    "info": 6
  }
}
```

## カスタムテーマの作成

### 手順

1. `assets/themes/` ディレクトリに新しいJSONファイルを作成
   ```bash
   touch assets/themes/my_theme.json
   ```

2. 上記の形式でテーマを定義
   ```json
   {
     "name": "My Custom Theme",
     "colors": {
       "background": 1,
       "text": 6,
       "text_selected": 14,
       "border": 12,
       "border_accent": 6,
       "scrollbar": 12,
       "status_bg": 2,
       "help_bg": 2,
       "error": 8,
       "success": 11,
       "info": 12
     }
   }
   ```

3. PFEを再起動してテーマを読み込み

4. Settings画面でテーマを選択

### テーマ作成のヒント

#### 視認性の確保
- `background` と `text` は十分なコントラストを確保
- `text_selected` は `text` より目立つ色を選択
- スクロールバーは背景から明確に区別できる色に

#### 推奨カラー組み合わせ

**ダーク系:**
- 背景: 0 (黒), 1 (濃い青), 2 (濃い紫), 3 (濃い緑)
- テキスト: 7 (白), 6 (明るいグレー), 14 (ピンク), 10 (黄色)

**ライト系:**
- 背景: 7 (白), 6 (明るいグレー), 15 (ピーチ)
- テキスト: 0 (黒), 1 (濃い青), 4 (茶色)

**アクセントカラー:**
- 強調: 8 (赤), 10 (黄色), 14 (ピンク)
- 落ち着いた: 12 (青), 11 (緑), 9 (オレンジ)

#### テスト
- 各画面（メインメニュー、ファイルリスト、設定など）で確認
- リストモードとギャラリーモードの両方でテスト
- スクリーンショット表示時の視認性を確認

## トラブルシューティング

### テーマが表示されない
- ファイル名が `.json` で終わっているか確認
- JSONの構文が正しいか確認（カンマ、括弧など）
- `assets/themes/` ディレクトリに配置されているか確認

### 色が正しく表示されない
- カラー番号が0〜15の範囲内か確認
- すべてのカラーキーが定義されているか確認

### テーマ選択後に反映されない
- PFEを再起動
- Settings画面でテーマを再選択

## 例: カスタムテーマ集

### Ocean（オーシャンテーマ）
```json
{
  "name": "Ocean",
  "colors": {
    "background": 1,
    "text": 6,
    "text_selected": 12,
    "border": 12,
    "border_accent": 6,
    "scrollbar": 12,
    "status_bg": 5,
    "help_bg": 5,
    "error": 8,
    "success": 11,
    "info": 12
  }
}
```

### Sunset（サンセットテーマ）
```json
{
  "name": "Sunset",
  "colors": {
    "background": 4,
    "text": 15,
    "text_selected": 9,
    "border": 9,
    "border_accent": 10,
    "scrollbar": 9,
    "status_bg": 2,
    "help_bg": 2,
    "error": 8,
    "success": 11,
    "info": 9
  }
}
```

### Forest（フォレストテーマ）
```json
{
  "name": "Forest",
  "colors": {
    "background": 3,
    "text": 7,
    "text_selected": 10,
    "border": 11,
    "border_accent": 10,
    "scrollbar": 11,
    "status_bg": 5,
    "help_bg": 5,
    "error": 8,
    "success": 11,
    "info": 11
  }
}
```

### Monochrome（モノクロームテーマ）
```json
{
  "name": "Monochrome",
  "colors": {
    "background": 0,
    "text": 13,
    "text_selected": 7,
    "border": 13,
    "border_accent": 7,
    "scrollbar": 13,
    "status_bg": 5,
    "help_bg": 5,
    "error": 13,
    "success": 7,
    "info": 13
  }
}
```

### Kawaii（カワイイテーマ）
```json
{
  "name": "Kawaii",
  "colors": {
    "background": 15,
    "text": 8,
    "text_selected": 14,
    "border": 14,
    "border_accent": 10,
    "scrollbar": 14,
    "status_bg": 7,
    "help_bg": 7,
    "error": 8,
    "success": 11,
    "info": 14
  }
}
```

## 参考リンク

- [Pyxel公式ドキュメント](https://github.com/kitao/pyxel)
- PFE設定ガイド: `data/pfe.cfg.example`
