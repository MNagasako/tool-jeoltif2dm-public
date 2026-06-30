# J2DM — JEOL SightSky TIFF → Gatan DM3/DM4 Converter

**J2DM** は JEOL SightSky で保存した TIFF 画像を、Gatan DigitalMicrograph (GMS 3) ネイティブの `.dm3` / `.dm4` ファイルに変換するスタンドアロンツールです。

**J2DM** is a standalone tool that converts TIFF images saved by JEOL SightSky into Gatan DigitalMicrograph (GMS 3) native `.dm3` / `.dm4` files.

---

## ダウンロード / Download

**[最新版リリースはこちら / Latest Release](../../releases/latest)**

| ファイル / File | 説明 / Description |
|----------------|-------------------|
| `J2DM-vX.Y.Z.exe` | Windows x64 スタンドアロン実行ファイル / Standalone executable (no Python required) |
| `SHA256SUMS.txt` | SHA256 チェックサム / SHA256 checksum |

---

## 動作環境 / System Requirements

- Windows 10 / 11 (x64)
- Python 不要 / No Python installation required

---

## 使い方 / Usage

### GUI モード（ドラッグ＆ドロップ）/ GUI Mode (Drag & Drop)

`.exe` に `.tif` ファイルまたはフォルダをドラッグ＆ドロップすると、変換オプションダイアログが表示されます。

Drag and drop `.tif` files or folders onto the `.exe` to open the conversion options dialog.

### コマンドラインモード / Command-Line Mode

```
J2DM-vX.Y.Z.exe [file or folder ...] [options]

Options:
  --format dm3|dm4    Output format (default: dm3)
  --markers           Include annotations/markers
  --metadata          Include extended metadata
  --scalebar          Add scale bar
  --output PATH       Specify output path
```

---

## 主な機能 / Features

| | 日本語 | English |
|-|--------|---------|
| **互換性** | GMS 3 ネイティブ互換（バイナリテンプレート注入方式）| GMS 3 native compatibility via binary template injection |
| **モード自動判別** | メタデータから実空間 (nm) / 逆空間 (1/nm) を自動検出 | Auto-detects real-space (nm) vs. reciprocal-space (1/nm) from metadata |
| **コントラスト** | SightSky Viewer と同等のコントラスト範囲を再現 | Reproduces SightSky Viewer's display contrast range |
| **バッチ変換** | 複数ファイル・フォルダの一括変換 | Batch conversion of multiple files and folders |
| **PNG/JPG 出力** | スケールバー焼き込み画像出力に対応 | Image export with scale bar burn-in |

---

## 免責事項 / Disclaimer

本ソフトウェアは現状のまま提供されます。使用により生じたいかなる損害・データ損失・機器障害についても、作者は一切の責任を負いません。

This software is provided "as is" without any warranty. The author assumes no responsibility for any damage, data loss, or equipment failure arising from its use.

---

## ソースコード / Source Code

ソースコードは非公開です。このリポジトリはバイナリ配布専用です。

The source code is not publicly available. This repository is for binary distribution only.
