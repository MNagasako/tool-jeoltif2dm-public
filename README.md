# J2DM — JEOL TIF to DM3/DM4 Converter

This tool converts JEOL SIGHTSKY TIFF images (which contain embedded XML metadata) into Gatan DigitalMicrograph (GMS 3) compatible `.dm3` / `.dm4` files.

This repository is a **build-minimal source snapshot** matching the compiled `.exe` published alongside it in
[Releases](../../releases): only the files needed to run or rebuild the converter are included (no test fixtures,
no development-only tooling/history). Development happens in a separate private repository.

## Features

- **100% GMS 3 Native Compatibility:** Rather than writing raw data, this tool uses a "Binary Template Injection" architecture. It bundles a tiny footprint of a perfect native GMS 3 workspace document UI and dynamically patches it. This ensures all UI layout features, thumbnails, and window bounding boxes are identical to files saved directly from GMS.
- **DM3 and DM4 output:** `--format dm3|dm4` (or just use a `.dm4` `--output` path). Both formats are produced from the same patched/injected tag tree.
- **Matching display contrast:** Reproduces SightX Viewer's actual contrast/histogram range (percentile-trimmed auto-stretch or fixed range, per the source TIFF's own LUT settings) instead of leaving GMS's default/stale range, so the histogram in GMS matches what you saw in SightX.
- **Dynamic Mode Detection:** Automatically detects real space (`nm`/`um`) vs reciprocal space (`1/nm`) units from the TIF metadata and selects the appropriate GMS template (IMAGING vs DIFFRACTION modes).
- **Scale Bar Positioning:** Dynamically calculates the accurate position for the scale bar relative to the lower-left corner of the image, regardless of the input resolution.
- **Batch conversion:** Pass multiple files and/or whole folders (recursively scanned for `.tif`/`.tiff`) in one invocation, from the command line or by dragging them all onto the executable at once.
- **Drag-and-drop options popup:** When started by dragging file(s)/folder(s) onto the executable directly (no command-line flags), a small native dialog (Tk/tkinter — bundled in the binary, no extra runtime needed) asks for the output format and whether to include markers/metadata before converting, then shows a summary and writes a per-batch log next to the source files.
- **Standalone Executable:** Compiled as a single, version-named `.exe` with PyInstaller `--onefile`; it bundles the Python runtime, all dependencies, and the binary templates, so it runs on a bare Windows machine with no Python install.

## Usage

### Running the Python Script

If you have Python installed, simply run the script against one or more `.tif` files and/or directories:

```bash
# Convert a single file
python convert_jeol_to_dm.py /path/to/image.tif

# Convert multiple files and/or whole directories in one call (directories are scanned recursively)
python convert_jeol_to_dm.py /path/to/image1.tif /path/to/a_directory /path/to/image2.tif --format dm4 --markers --metadata
```

### Running the Standalone Binary

Download the latest `.exe` from [Releases](../../releases). It contains the Python runtime, libraries, and binary
templates — no separate Python install is required on the target machine.

```bash
# In Windows PowerShell/CMD - same flags as the Python script
.\J2DM-vX.Y.Z.exe C:\path\to\image.tif --format dm4 --markers --metadata
```

You can also drag-and-drop one or more `.tif` files and/or whole folders onto the `.exe` in Windows Explorer. When
started this way (i.e. with no `--format`/`--markers`/`--metadata`/`--output` flags), a small popup asks for the
desired output format and options before converting everything you dropped; a completion summary and a
`J2DM_conversion_log.txt` log (written next to the first dropped file) follow once the batch finishes.

## Building the Standalone Binary from Source

To compile the script into a standalone executable, use the provided build scripts. This process uses a dedicated
virtual environment and `PyInstaller` to bundle the application and templates together cleanly. This snapshot
includes the exact `specs/*.spec` file used to build the `.exe` published alongside it.

### On Windows
Run the `build.bat` script:
```cmd
build.bat
```

### On macOS / Linux
Run the `build.sh` script:
```bash
chmod +x build.sh
./build.sh
```

The compiled executable will be located at `dist/J2DM-vX.Y.Z.exe`.

*(Note: PyInstaller is not a cross-compiler. To build a Mac binary, you must run `build.sh` on a Mac. To build a Windows binary, you must run `build.bat` on Windows.)*

## Architecture

### 1. Metadata Extraction
The tool reads `Tag 270 (ImageDescription)` from the TIFF file which JEOL populates with XML metadata. It extracts:
- `LengthPerPixel` and `MeasureTextUnit` (Scale and Units)
- `AccVoltage` (Acceleration Voltage)
- `MagCamLengthString` (Magnification or Camera Length)

### 2. Binary Patching (`dm3_patcher.py`)
GMS `.dm3` files have complex proprietary document layouts that crash if generated incorrectly.
The tool loads a pre-configured template (`templates/template_image.dm3` or `templates/template_diff.dm3`) into memory, and searches for specific byte signatures to overwrite:
- Image pixel data arrays
- Calibration dimensions, units, scale, origins
- Voltage and Actual/Indicated Magnification
- Scale bar `Rectangle` bounding boxes

It then recalculates the `RootLen` offset byte to ensure the file size structurally validates. Structural additions
(annotations, extended metadata) are made via an in-house DM3 tag-tree (AST) parser/serializer (`dm3_editor.py`),
which also handles native DM4 serialization.

---

## 技術スタック (Tech Stack)

- **言語:** Python 3.11+ (CI/リリースビルドは 3.11、開発環境は 3.13 でも動作確認済み)
- **GUI:** `tkinter` / `ttk`(標準ライブラリのみ。追加ランタイム不要でPyInstallerに同梱可能)
- **画像・数値処理:** `numpy`、`tifffile`(JEOL TIFF読み込み・Tag 270 XML抽出)、`Pillow`(PNG/JPG出力・アイコン生成)
- **ドラッグ&ドロップ:** `windnd`(Windows Shell DnDのPython実装)
- **DM3/DM4バイナリ生成:** 自前実装(`dm3_patcher.py`の正規表現バイナリパッチ + `dm3_editor.py`のASTベースタグツリー編集・シリアライザ)。外部DM3/DM4ライブラリには依存しない
- **パッケージング:** `PyInstaller`(`--onefile`。このリポジトリにはビルドに使用した`.spec`のみを同梱)

### AIエージェントを活用した開発について

このプロジェクトは実装・調査・ドキュメント整備の多くをAIコーディングエージェント経由で行っています。
Claude Code・Gemini・Codex を作業内容や状況に応じて使い分けており、複数のエージェントを併用している主な理由は
各サービスのエントリープラン(無料/低価格帯プラン)のレートリミットを分散して回避するためです(w)。
実機(DigitalMicrograph / SightX-Viewer)での目視検証が必要な箇所は、エージェント任せにせず人力で必ず確認しています。
