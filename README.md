# J2DM — JEOL TIF to DM3/DM4 Converter

[日本語](#日本語) ・ [English](#english)

このリポジトリには、[Releases](../../releases) で公開しているビルド済み `.exe` に対応する、ビルドに必要な最小限のソースを配置しています。アーキテクチャなど詳細な技術情報は [NOTES.md](NOTES.md) をご覧ください。
This repository contains a build-minimal source snapshot matching the compiled `.exe` published in [Releases](../../releases). See [NOTES.md](NOTES.md) for further technical details.

---

## 日本語

### 概要

JEOL SightSky TIFF画像(JEOL独自のXMLメタデータが埋め込まれたTIFF)を、Gatan DigitalMicrograph(GMS 3)互換の `.dm3` / `.dm4` ファイルに変換するツールです。実空間画像・回折(逆空間)画像の両方に対応し、スケール・電圧・倍率・コントラストをSightX Viewerの表示に合わせて再現します。

### 使用方法

**Pythonスクリプトとして実行する場合**

```bash
# ファイルを1つ変換
python convert_jeol_to_dm.py /path/to/image.tif

# 複数ファイル・フォルダをまとめて変換(フォルダは再帰的に走査)
python convert_jeol_to_dm.py /path/to/image1.tif /path/to/a_directory /path/to/image2.tif --format dm4 --markers --metadata
```

**スタンドアロン実行ファイルとして実行する場合**

[Releases](../../releases) から最新の `.exe` をダウンロードしてください。Python本体・依存ライブラリ・バイナリテンプレートを同梱しているため、変換先のマシンに別途Pythonをインストールする必要はありません。

```bash
.\J2DM-vX.Y.Z.exe C:\path\to\image.tif --format dm4 --markers --metadata
```

`.tif` ファイルやフォルダをWindows Explorer上で `.exe` に直接ドラッグ&ドロップして実行することもできます。この場合(コマンドラインオプション未指定時)は、出力形式やマーカー/メタデータ付与の有無を選べる簡易ポップアップが表示され、変換完了後にサマリー画面と `J2DM_conversion_log.txt`(最初にドロップしたファイルと同じフォルダに出力)が生成されます。

### ビルド方法

付属のビルドスクリプトを使うと、専用の仮想環境を作成した上で `PyInstaller` によりスタンドアロン実行ファイルをビルドできます。このリポジトリには、対応する [Releases](../../releases) のビルドに実際に使用した `specs/*.spec` を同梱しています。

Windowsの場合(`build.bat` を実行):

```cmd
build.bat
```

macOS / Linuxの場合(`build.sh` を実行):

```bash
chmod +x build.sh
./build.sh
```

ビルドが完了すると `dist/J2DM-vX.Y.Z.exe` に実行ファイルが生成されます。

*(注意: PyInstallerはクロスコンパイラではありません。Windows用バイナリは必ずWindows上で `build.bat` を、Mac用バイナリは必ずMac上で `build.sh` を実行してビルドしてください。)*

### 技術スタック

- **言語:** Python 3.11+
- **GUI:** `tkinter` / `ttk`(標準ライブラリのみ。追加ランタイム不要でPyInstallerに同梱可能)
- **画像・数値処理:** `numpy`、`tifffile`(JEOL TIFF読み込み・メタデータ抽出)、`Pillow`(PNG/JPG出力・アイコン生成)
- **ドラッグ&ドロップ:** `windnd`(Windows Shell DnDのPython実装)
- **DM3/DM4バイナリ生成:** 自前実装(正規表現バイナリパッチ + ASTベースのタグツリー編集・シリアライザ)。外部のDM3/DM4専用ライブラリには依存しない
- **パッケージング:** `PyInstaller`(`--onefile`。このリポジトリにはビルドに使用した `.spec` のみを同梱)

---

## English

### Overview

Converts JEOL SightSky TIFF images (which embed JEOL's own XML metadata) into Gatan DigitalMicrograph (GMS 3) compatible `.dm3` / `.dm4` files. Supports both real-space (imaging) and reciprocal-space (diffraction) images, reproducing the scale, voltage, magnification, and display contrast seen in SightX Viewer.

### Usage

**Running the Python script**

```bash
# Convert a single file
python convert_jeol_to_dm.py /path/to/image.tif

# Convert multiple files and/or whole directories in one call (directories are scanned recursively)
python convert_jeol_to_dm.py /path/to/image1.tif /path/to/a_directory /path/to/image2.tif --format dm4 --markers --metadata
```

**Running the standalone binary**

Download the latest `.exe` from [Releases](../../releases). It bundles the Python runtime, dependencies, and binary templates, so no separate Python install is required on the target machine.

```bash
.\J2DM-vX.Y.Z.exe C:\path\to\image.tif --format dm4 --markers --metadata
```

You can also drag-and-drop one or more `.tif` files and/or whole folders onto the `.exe` in Windows Explorer. When started this way (i.e. with no command-line flags), a small popup asks for the desired output format and options before converting; a completion summary and a `J2DM_conversion_log.txt` log (written next to the first dropped file) follow once the batch finishes.

### Building from Source

The provided build scripts create a dedicated virtual environment and use `PyInstaller` to bundle the application and its templates into a standalone executable. This repository includes the exact `specs/*.spec` file used to build the `.exe` published in the corresponding [Releases](../../releases) entry.

On Windows (run `build.bat`):

```cmd
build.bat
```

On macOS / Linux (run `build.sh`):

```bash
chmod +x build.sh
./build.sh
```

The compiled executable will be located at `dist/J2DM-vX.Y.Z.exe`.

*(Note: PyInstaller is not a cross-compiler. Build Windows binaries with `build.bat` on Windows, and Mac binaries with `build.sh` on a Mac.)*

### Tech Stack

- **Language:** Python 3.11+
- **GUI:** `tkinter` / `ttk` (standard library only — no extra runtime needed, bundles cleanly with PyInstaller)
- **Imaging / numerics:** `numpy`, `tifffile` (reading JEOL TIFFs and metadata), `Pillow` (PNG/JPG output, icon generation)
- **Drag-and-drop:** `windnd` (Python binding for Windows Shell drag-and-drop)
- **DM3/DM4 binary generation:** in-house implementation (regex binary patching + an AST-based tag-tree editor/serializer); no dependency on any third-party DM3/DM4 library
- **Packaging:** `PyInstaller` (`--onefile`; only the `.spec` used for this build is included here)
