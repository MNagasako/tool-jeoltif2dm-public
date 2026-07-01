# Notes

Supplementary information about this project that doesn't belong in the top-level `README.md`
(overview / usage / build / tech stack only). See the [README](README.md) for those.

## Architecture

### 1. Metadata Extraction

The tool reads `Tag 270 (ImageDescription)` from the TIFF file, which JEOL populates with XML metadata. It extracts:

- `LengthPerPixel` and `MeasureTextUnit` (scale and units)
- `AccVoltage` (acceleration voltage)
- `MagCamLengthString` (magnification or camera length)

### 2. Binary Patching (`dm3_patcher.py`)

GMS `.dm3` files have complex proprietary document layouts that crash if generated incorrectly. The tool loads
a pre-configured template (`templates/template_image.dm3` or `templates/template_diff.dm3`) into memory, and
searches for specific byte signatures to overwrite:

- Image pixel data arrays
- Calibration dimensions, units, scale, origins
- Voltage and Actual/Indicated Magnification
- Scale bar `Rectangle` bounding boxes

It then recalculates the `RootLen` offset byte so the file size structurally validates. Structural additions
(annotations, extended metadata) are made via an in-house DM3 tag-tree (AST) parser/serializer
(`dm3_editor.py`), which also handles native DM4 serialization.

## AIエージェントを活用した開発について

このプロジェクトは実装・調査・ドキュメント整備の多くをAIコーディングエージェントを使用して行っています。
Claude Code・Gemini・Codex を作業内容や状況に応じて使い分けており、複数のエージェントを併用している主な理由は
各サービスのエントリープラン(低価格帯プラン)のレートリミットを分散して回避するためです。
実機(DigitalMicrograph / SightX-Viewer)での目視検証が必要な箇所は、エージェント任せにせず人力で必ず確認しています。
