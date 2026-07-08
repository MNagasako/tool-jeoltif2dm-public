import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import re
import tkinter as tk
from tkinter import messagebox, filedialog, scrolledtext, ttk
import threading
import queue as _queue
import webbrowser
import numpy as np
import tifffile
import argparse
from dm3_patcher import patch_template
from dm3_editor import create_annotation_group

try:
    import windnd
    _HAS_WINDND = True
except ImportError:
    _HAS_WINDND = False

APP_NAME    = "J2DM"
APP_VERSION = "1.6.10"
APP_SUBTITLE = "JEOL SightSky TIFF to Gatan DM3/DM4 Converter"
GITHUB_URL  = "https://github.com/MNagasako/tool-jeoltif2dm-public"

# ── i18n ──────────────────────────────────────────────────────────────────────
_UI_LANG = ['en']  # mutable so closures can mutate it

STRINGS = {
    'en': {
        'window_title':   "J2DM v{version}",
        'app_subtitle':   "JEOL SightSky TIFF to Gatan DM3/DM4 Converter",
        'drop_empty':     "Drop files / folders here\n(.tif / .tiff files or folders, multiple OK)",
        'drop_hint':      "Drop to add more\n{n} TIF file(s) ready",
        'count_label':    "Queued: {n} file(s)",
        'browse':         "Browse...",
        'file_list_btn':  "File List",
        'output_format':  "Output Format",
        'options':        "Options",
        'scalebar_cb':    "Add scale bar  (PNG/JPG: burned into image)",
        'bar_size':       "Bar size:",
        'font_size_lbl':  "Font size:",
        'markers_cb':     "Markers/annotations  (DM3/DM4 only)",
        'metadata_cb':    "Extended metadata  (DM3/DM4 only)",
        'convert_btn':    "Convert",
        'cancel_btn':     "Cancel",
        'toggle_lang':    "日本語",
        'no_files':       "No TIF/TIFF files selected.\nPlease drop or browse for files.",
        'filelist_title': "Files to Convert ({n} files)",
        'close_btn':      "Close",
        'usage_title':    "J2DM v{version} — Usage",
        'about_title':    "About J2DM",
        'about_body': (
            "J2DM  v{version}\n"
            "JEOL SightSky TIFF to Gatan DM3/DM4 Converter\n\n"
            "[Description]\n"
            "Converts TIF images from JEOL SightSky into\n"
            "Gatan DigitalMicrograph (DM3/DM4) format.\n"
            "PNG / JPG output with scale bar burn-in is also supported.\n\n"
            "[Disclaimer]\n"
            "This software is provided WITHOUT ANY WARRANTY.\n"
            "The author assumes no responsibility for any damage,\n"
            "data loss, or equipment failure arising from its use.\n\n"
            "[Known Issues]\n"
            "· Some annotation types may not convert accurately\n"
            "· Log-scale diffraction images use approximate conversion\n"
            "· Freehand annotations are approximated as polylines"
        ),
        'complete_ok':       "Conversion complete: {ok} succeeded / {fail} failed",
        'complete_fail_hdr': "Failed files:",
        'complete_log':      "Log: {path}",
        'complete_title':    "J2DM v{version}",
        'licenses_btn':      "Third-Party Notices",
        'licenses_title':    "Third-Party Notices",
        'progress_title':    "Converting...",
        'progress_label':    "Converting: {n} / {total}",
        'cancelling':        "Cancelling...",
        'cancelled_msg':     "Conversion cancelled.  ({ok} of {total} files completed)",
    },
    'ja': {
        'window_title':   "J2DM v{version}",
        'app_subtitle':   "JEOL SightSky TIFF → Gatan DM3/DM4 変換ツール",
        'drop_empty':     "ここにファイル / フォルダをドロップしてください\n(.tif / .tiff ファイルまたはフォルダ、複数可)",
        'drop_hint':      "ドロップでさらに追加できます\n現在 {n} 件の TIF ファイルが登録されています",
        'count_label':    "追加済み: {n} 件",
        'browse':         "参照...",
        'file_list_btn':  "ファイルリスト確認",
        'output_format':  "出力フォーマット",
        'options':        "オプション",
        'scalebar_cb':    "スケールバーを追加  (PNG/JPG は画像内に焼き付け)",
        'bar_size':       "バーサイズ:",
        'font_size_lbl':  "フォントサイズ:",
        'markers_cb':     "アノテーション/マーカーを含める  (DM3/DM4 のみ)",
        'metadata_cb':    "拡張メタデータを含める  (DM3/DM4 のみ)",
        'convert_btn':    "変換開始",
        'cancel_btn':     "キャンセル",
        'toggle_lang':    "English",
        'no_files':       "TIF/TIFFファイルが見つかりません。\nファイルまたはフォルダを追加してください。",
        'filelist_title': "変換対象ファイル ({n} 件)",
        'close_btn':      "閉じる",
        'usage_title':    "J2DM v{version} - 使い方",
        'about_title':    "J2DM について",
        'about_body': (
            "J2DM  v{version}\n"
            "JEOL SightSky TIFF → Gatan DM3/DM4 変換ツール\n\n"
            "《説明》\n"
            "JEOL SightSky で撮影した TIF 画像を\n"
            "Gatan DigitalMicrograph (DM3/DM4) 形式に変換するツールです。\n"
            "PNG / JPG へのスケールバー焼き付き出力も可能です。\n\n"
            "《免責事項》\n"
            "本ソフトウェアは完全に無保証です。\n"
            "このツールを使用して生じたいかなる損害、データの損失、\n"
            "機器の不具合等についても一切の責任を負いません。\n\n"
            "《既知の不具合》\n"
            "・一部のアノテーション種別は正確に変換されない場合があります\n"
            "・対数スケール表示の回折図形は近似変換です\n"
            "・手書きアノテーション (FreeHand) は折れ線近似されます"
        ),
        'complete_ok':       "変換完了: 成功 {ok} 件 / 失敗 {fail} 件",
        'complete_fail_hdr': "失敗したファイル:",
        'complete_log':      "詳細ログ: {path}",
        'complete_title':    "J2DM v{version}",
        'licenses_btn':      "サードパーティ表示",
        'licenses_title':    "サードパーティ表示",
        'progress_title':    "変換中...",
        'progress_label':    "変換中: {n} / {total}",
        'cancelling':        "中止中...",
        'cancelled_msg':     "変換を中止しました。({total} 件中 {ok} 件完了)",
    },
}

def _t(key, **kw):
    s = STRINGS.get(_UI_LANG[0], STRINGS['en']).get(key, f'[{key}]')
    return s.format(**kw) if kw else s

def read_tag270_text(tif, tag):
    """
    Read TIFF Tag 270 (ImageDescription) as raw bytes and decode as UTF-8 ourselves.
    JEOL writes the XML payload as UTF-8 (including Japanese annotation text such as
    "テスト"), but the tag is declared as plain ASCII per the TIFF spec; tifffile's own
    str-decoded tag.value mis-decodes any non-ASCII byte as U+FFFD, irreversibly corrupting
    every Japanese character in the XML (verified: tag.value yields "�e�X�g"
    for what the raw bytes show is valid UTF-8 b'\xe3\x83\x86...' == "テスト"). Re-reading the
    raw bytes from the file and decoding as UTF-8 here avoids that corruption entirely.
    """
    fh = tif.filehandle
    fh.seek(tag.valueoffset)
    raw = fh.read(tag.count)
    raw = raw.split(b'\x00', 1)[0]
    return raw.decode('utf-8', errors='replace')

def clean_xml(xml_data):
    cleaned = re.sub(r'&#x[0-9a-fA-F]+;', '', xml_data)
    # Preserve the WCF polymorphism discriminator (e.g. <c:AnnotationReporter i:type="c:LineReporter">)
    # BEFORE the generic prefixed-attribute strip below removes it. This is JEOL's own authoritative
    # annotation-kind tag (LineReporter/EllipseReporter/ROIReporter/TextReporter/CustomAreaLUTReporter/
    # InstrumentInfoReporter/...) - far more reliable than guessing the shape from which child tags
    # happen to be present (verified: several real annotations carry no shape-specific child tag at
    # all and were previously silently dropped or misclassified). Renamed to a plain (non-prefixed)
    # attribute so it survives the later strip and is queryable as anno.get('AnnoType').
    cleaned = re.sub(r' i:type="[a-zA-Z0-9]+:([A-Za-z0-9]+)"', r' AnnoType="\1"', cleaned)
    cleaned = re.sub(r' xmlns(:[a-zA-Z0-9]+)?="[^"]+"', '', cleaned)
    cleaned = re.sub(r'<([a-zA-Z0-9]+):', '<', cleaned)
    cleaned = re.sub(r'</([a-zA-Z0-9]+):', '</', cleaned)
    cleaned = re.sub(r' [a-zA-Z0-9]+:[a-zA-Z0-9]+="[^"]*"', '', cleaned)
    return cleaned

def _find_micronbar_pixel_size(root):
    """Derive pixel_size from SightX's own scale-bar measurement:
    MicronbarValue (the number SightX displays) divided by the
    MicronbarRectangleReporter annotation's on-canvas pixel width. Returns None if
    either value is missing or not physically valid (<=0), so callers can fall back
    to LengthPerPixel/GratingSpacePerPixel."""
    value_node = root.find('.//MicronbarValue')
    if value_node is None or not value_node.text:
        return None
    try:
        value = float(value_node.text)
    except ValueError:
        return None
    if value <= 0:
        return None
    for anno in root.findall('.//AnnotationReporter'):
        if anno.get('AnnoType') == 'MicronbarRectangleReporter':
            w_node = anno.find('./BorderSize/width')
            if w_node is not None and w_node.text:
                try:
                    width = float(w_node.text)
                except ValueError:
                    continue
                if width > 0:
                    return value / width
            break
    return None

def extract_metadata(xml_data, img_shape=None):
    """
    Extract relevant JEOL metadata and annotations from the XML string.
    """
    metadata = {
        'pixel_size': 1.0,
        'unit': 'px',
        'voltage': 0.0,
        'magnification': 1.0,
        'microscope_info': {},
        'annotations': [],
        'contrast': None
    }
    
    cleaned = clean_xml(xml_data)
    import xml.etree.ElementTree as ET
    
    try:
        root = ET.fromstring(cleaned)
    except ET.ParseError as e:
        print(f"  [Warning] XML Parse Error: {e}. Falling back to limited regex extraction.")
        # fallback for pixel size
        match_scale = re.search(r'<[^>]*LengthPerPixel[^>]*>([\d\.]+)</[^>]*LengthPerPixel>', xml_data)
        if match_scale: metadata['pixel_size'] = float(match_scale.group(1))
        match_unit = re.search(r'<[^>]*MicronbarUnit[^>]*>(.*?)</[^>]*MicronbarUnit>', xml_data)
        if match_unit: metadata['unit'] = match_unit.group(1).strip()
        match_volt = re.search(r'<[^>]*AccVoltage[^>]*>([\d\.]+)</[^>]*AccVoltage>', xml_data)
        if match_volt: metadata['voltage'] = float(match_volt.group(1))
        return metadata

    # 1. Pixel Size
    length_node = root.find('.//MeasureLengthPerPixelReporter/LengthPerPixel')
    if length_node is not None and length_node.text:
        metadata['pixel_size'] = float(length_node.text)

    # Unit
    unit_node = root.find('.//MicronbarUnit')
    if unit_node is None:
        unit_node = root.find('.//MeasureTextUnit')
    if unit_node is not None and unit_node.text:
        unit = unit_node.text.strip()
        if unit.lower() in ["nanometer", "nm"]: unit = "nm"
        elif unit.lower() in ["micrometer", "um", "micron", "\xb5m"]: unit = "um"
        elif "nm" in unit and ("\u207b" in unit or "-1" in unit): unit = "1/nm"
        elif "1/nm" in unit or "NanometerInv" in unit: unit = "1/nm"
        metadata['unit'] = unit

    if metadata.get('unit') == '1/nm':
        grating_node = root.find('.//GratingSpacePerPixel')
        if grating_node is not None and grating_node.text and float(grating_node.text) > 0:
            metadata['pixel_size'] = 1.0 / float(grating_node.text)

    # 1b. Prefer SightX's own rendered scale-bar measurement over LengthPerPixel/
    # GratingSpacePerPixel when available. Verified against real acquisitions (camera
    # length 8/12/20/30/50/80cm at 160kV) that GratingSpacePerPixel can be wrong by a
    # consistent ~64x factor for some acquisition conditions while being correct for
    # others (25cm/200kV) - a real JEOL/SightX metadata inconsistency. MicronbarValue/
    # BorderSize.width is the exact number SightX itself used to draw its own scale
    # bar, so it can't disagree with what the user sees there.
    micronbar_pixel_size = _find_micronbar_pixel_size(root)
    if micronbar_pixel_size is not None:
        metadata['pixel_size'] = micronbar_pixel_size

    # 2. Voltage
    volt_node = root.find('.//MeasurementReporter/AccVoltage')
    if volt_node is not None and volt_node.text:
        metadata['voltage'] = float(volt_node.text)
        
    # 3. Magnification and Microscope Info
    inst_node = root.find('.//InstrumentInfoReporter')
    if inst_node is not None:
        mag_node = inst_node.find('MagCamLengthString')
        if mag_node is not None and mag_node.text:
            mag_str = mag_node.text
            clean_mag = mag_str.upper().replace('X', '').replace('K', '000').strip()
            try: metadata['magnification'] = float(clean_mag)
            except ValueError: metadata['magnification'] = mag_str
            metadata['microscope_info']['Indicated Magnification'] = metadata['magnification']
            
        inst_name = inst_node.find('InstrumentString')
        if inst_name is not None and inst_name.text:
            metadata['microscope_info']['Name'] = inst_name.text
            
        op_name = inst_node.find('Operator')
        if op_name is not None and op_name.text:
            metadata['microscope_info']['Operator'] = op_name.text
            
        spec_name = inst_node.find('Specimen')
        if spec_name is not None and spec_name.text:
            metadata['microscope_info']['Specimen'] = spec_name.text
            
        exp_time = inst_node.find('ExposureTimeString')
        if exp_time is not None and exp_time.text:
            # SIGHTSKY exports "499 msec", DM expects seconds sometimes, we can put it as string in a generic field or skip.
            # But we can also look for ObservationReporter ExposureTimeValue
            pass
            
    # Exposure time from detector
    det_node = root.find('.//DetectorReporter')
    if det_node is not None:
        exp_val = det_node.find('ExposureTimeValue')
        if exp_val is not None and exp_val.text:
            try:
                # SIGHTSKY seems to store us or ns? If '499418' is 499 msec, then it's microseconds!
                exp_s = float(exp_val.text) / 1000000.0
                metadata['microscope_info']['Exposure Time (s)'] = exp_s
            except: pass

    # 3b. Display contrast (LUT) - mirrors what SightX Viewer shows for this image so the
    # converted DM's histogram/contrast window matches the source TIFF.
    # SightX stores this under ImageProcessReporter/ImageLookupTableReporter:
    #   LUT_AutoAdjust=true  -> contrast is a percentile-trimmed auto-stretch of the real pixel
    #                           histogram (LUT_Lower/UpperThreshHold are the trim percentages).
    #   LUT_AutoAdjust=false -> contrast is the fixed [LUT_LowerLimit, LUT_UpperLimit] range
    #                           (observed on diffraction/log-scale images, full uint16 range).
    lut_node = root.find('.//ImageLookupTableReporter')
    if lut_node is not None:
        def _lut_val(tag, cast):
            n = lut_node.find(tag)
            if n is not None and n.text is not None:
                try: return cast(n.text)
                except ValueError: pass
            return None
        auto_adjust = (lut_node.find('LUT_AutoAdjust').text == 'true') if lut_node.find('LUT_AutoAdjust') is not None else True
        is_log = (lut_node.find('IsLogScale').text == 'true') if lut_node.find('IsLogScale') is not None else False
        metadata['contrast'] = {
            'auto_adjust': auto_adjust,
            'is_log_scale': is_log,
            'lower_limit': _lut_val('LUT_LowerLimit', float),
            'upper_limit': _lut_val('LUT_UpperLimit', float),
            'lower_trim_pct': _lut_val('LUT_LowerThreshHold', float) or 0.0,
            'upper_trim_pct': _lut_val('LUT_UpperThreshHold', float) or 0.0,
        }

    # 4. Extract Annotations
    # JEOL's XML repeats the *same* logical annotation as multiple separate AnnotationReporter
    # elements (verified: in one real test file, 27 AnnotationReporter elements collapsed to
    # only 11 distinct IdentifyGuid values - e.g. one DerivedNo rectangle appeared 4 times,
    # one Text label appeared twice, byte-for-byte identical each time). Processing every
    # occurrence drew stacked duplicate shapes; dedupe by IdentifyGuid so each real annotation
    # is emitted once.
    #
    # The primary discriminator is the WCF polymorphism type JEOL itself writes for every
    # AnnotationReporter (preserved by clean_xml() as the AnnoType attribute - e.g.
    # LineReporter/EllipseReporter/ROIReporter/TextReporter/CustomAreaLUTReporter/
    # InstrumentInfoReporter). An earlier version of this code guessed the shape from which
    # child tags happened to be present, which is fragile: several real annotation kinds (a
    # plain line, a plain ellipse) carry no shape-specific child tag at all and were silently
    # dropped or misclassified that way (verified via a real-app GMS/SightX-Viewer side-by-side
    # comparison and a full field dump of the source XML - see CURRENT_STATUS.md). The old
    # heuristics are kept as a fallback for any AnnoType not in the table below, since only two
    # real annotation-bearing files have been exhaustively catalogued so far.
    img_h, img_w = (img_shape[0], img_shape[1]) if img_shape else (None, None)

    def _parse_color(color_node):
        if color_node is not None:
            try:
                r = int(color_node.find('Red').text)
                g = int(color_node.find('Green').text)
                b = int(color_node.find('Blue').text)
                return (r, g, b)
            except Exception: pass
        return None

    def _replace_vars(anno, text):
        def replace_var(match):
            var_name = match.group(1)
            aliases = {'MagCameraLength': 'MagCamLengthString'}
            search_names = [var_name, var_name + 'String']
            if var_name in aliases:
                search_names.append(aliases[var_name])
            for name in search_names:
                tag_node = anno.find(name)
                if tag_node is not None:
                    return tag_node.text if tag_node.text else ""
            return match.group(0)
        return re.sub(r'\$\((.*?)\)', replace_var, text)

    # SightX measurement-length unit names -> (display suffix, scale relative to the image's own
    # calibrated unit). metadata['pixel_size']/['unit'] are always normalized to nm or 1/nm
    # (see Unit handling above), so these scale factors are relative to that nm/1-over-nm base;
    # inverse units (diffraction) need the *reciprocal* of the plain-length scale factor.
    _MEASURE_UNIT_SCALE = {
        'Nanometer': ('nm', 1.0), 'NanometerInv': ('nm⁻¹', 1.0),
        'Micrometer': ('µm', 1e-3), 'MicrometerInv': ('µm⁻¹', 1e3),
        'Millimeter': ('mm', 1e-6), 'MillimeterInv': ('mm⁻¹', 1e6),
    }

    def _auto_size_from_text(text, font_size, fallback_w=300.0, fallback_h=50.0):
        if not text:
            return fallback_w, fallback_h
        lines = text.split('\n')
        num_lines = len(lines)
        max_len = max(len(l) for l in lines)
        return float(max(200, max_len * font_size * 0.8)), float(max(50, num_lines * font_size * 1.5))

    def _norm_rect(x, y, w, h):
        top, bottom = min(y, y + h), max(y, y + h)
        left, right = min(x, x + w), max(x, x + w)
        return (top, left, bottom, right)

    seen_guids = set()
    for anno in root.findall('.//AnnotationReporter'):
        guid_node = anno.find('IdentifyGuid')
        if guid_node is not None and guid_node.text:
            if guid_node.text in seen_guids:
                continue
            seen_guids.add(guid_node.text)

        x_node = anno.find('./DisplayLocation/x')
        y_node = anno.find('./DisplayLocation/y')
        w_node = anno.find('./BorderSize/width')
        h_node = anno.find('./BorderSize/height')
        if x_node is None or y_node is None or w_node is None or h_node is None:
            continue

        anno_type = anno.get('AnnoType')
        x, y = float(x_node.text), float(y_node.text)
        w, h = float(w_node.text), float(h_node.text)

        font_size = 14
        fs_node = anno.find('.//TextFontSize')
        if fs_node is None:
            fs_node = anno.find('.//FontSize')
        if fs_node is not None:
            font_size = int(float(fs_node.text))

        fg_color = _parse_color(anno.find('TextForegroundColor')) or (255, 255, 0)
        # FillColor matches SightX's actual rendered shape color for every kind seen so far -
        # verified against a real CustomAreaLUTReporter where PenColor=(255,165,0) orange is used
        # only for its center-cross guide lines (drawn explicitly with pen_color_raw below) while
        # FillColor=(0,255,0) green is what SightX uses for the shape itself.
        fill_color = _parse_color(anno.find('FillColor')) or (0, 255, 0)
        pen_color_raw = _parse_color(anno.find('PenColor')) or fill_color
        shape_color = fill_color

        fill_node = anno.find('FillBackfround')
        is_filled = fill_node is not None and fill_node.text == 'true'

        # ---- LineReporter: a real directional line segment. BorderSize's sign encodes slope
        # (e.g. a negative height means the line rises left-to-right) - NOT a degenerate/zero-
        # size box, as the old child-tag-presence heuristic effectively treated it (this type
        # carries no shape-discriminator child tag at all, so it fell through to a fallback that
        # required an arrow/cross visibility flag to be true, which real LineReporter entries
        # never have - the arrow-type fields only select an arrowhead style, "None" just means a
        # plain line). This was silently dropping every plain line in real files.
        if anno_type == 'LineReporter':
            dm_anno = create_annotation_group(2, (y, x, y + h, x + w), text_color=shape_color)
            metadata['annotations'].append(dm_anno)

            mtr = anno.find('./MeasurementTextReporters/MeasurementTextReporter')
            if (mtr is not None and mtr.find('IsVisible') is not None
                    and mtr.find('IsVisible').text == 'true'):
                unit_node = mtr.find('MeasureTextUnit')
                decimals_node = mtr.find('MeasureTextNumberOfDecimal')
                suffix, scale = _MEASURE_UNIT_SCALE.get(unit_node.text if unit_node is not None else None, ('', 1.0))
                decimals = int(decimals_node.text) if decimals_node is not None else 2
                length_val = ((w ** 2 + h ** 2) ** 0.5) * metadata['pixel_size'] * scale
                mtext = f"{length_val:.{decimals}f} {suffix}".strip()
                mt_x = float(mtr.find('./DisplayLocation/x').text)
                mt_y = float(mtr.find('./DisplayLocation/y').text)
                mt_w = float(mtr.find('./BorderSize/width').text)
                mt_h = float(mtr.find('./BorderSize/height').text)
                if mt_w < 1 or mt_h < 1:
                    mt_w, mt_h = _auto_size_from_text(mtext, font_size)
                m_color = _parse_color(mtr.find('TextForegroundColor')) or shape_color
                dm_text = create_annotation_group(34, _norm_rect(mt_x, mt_y, mt_w, mt_h), text=mtext,
                                                   text_color=m_color, font_size=font_size)
                metadata['annotations'].append(dm_text)
            continue

        # ---- EllipseReporter: a real oval/circle annotation - also carries no shape-
        # discriminator child tag, so it previously fell through to the same dropped fallback as
        # LineReporter above.
        if anno_type == 'EllipseReporter':
            dm_anno = create_annotation_group(6, _norm_rect(x, y, w, h), text_color=shape_color, filled=is_filled)
            metadata['annotations'].append(dm_anno)
            continue

        # ---- FreeHandReporter: a hand-drawn curve, stored as a <Vertices> point list (each
        # <Point> is a _x/_y offset relative to DisplayLocation, confirmed by their range matching
        # BorderSize exactly). GMS has no verified native polyline/freehand AnnotationType (see
        # CURRENT_STATUS.md AnnotationType table), so this approximates the curve with one Line(2)
        # segment per consecutive vertex pair - real recorded point data, not a guessed shape.
        if anno_type == 'FreeHandReporter':
            points = anno.findall('./Vertices/Point')
            prev = None
            for pt in points:
                px_node, py_node = pt.find('_x'), pt.find('_y')
                if px_node is None or py_node is None:
                    continue
                cur = (x + float(px_node.text), y + float(py_node.text))
                if prev is not None:
                    seg_rect = (prev[1], prev[0], cur[1], cur[0])
                    dm_anno = create_annotation_group(2, seg_rect, text_color=shape_color)
                    metadata['annotations'].append(dm_anno)
                prev = cur
            continue

        # ---- ROIReporter: source-region rectangle for a derived view (e.g. FFT), labeled by
        # SightX as "ROI"+DerivedNo. That exact string is never stored in the XML (confirmed by
        # exhaustive grep) - it's synthesized client-side from the type+index, so the label is
        # generated here rather than read.
        if anno_type == 'ROIReporter':
            rect = _norm_rect(x, y, w, h)
            dm_anno = create_annotation_group(5, rect, text_color=shape_color, filled=is_filled)
            metadata['annotations'].append(dm_anno)
            dn_node = anno.find('DerivedNo')
            if dn_node is not None and dn_node.text:
                label = f"ROI{dn_node.text}"
                lbl_h = max(30.0, font_size * 1.8)
                label_rect = (rect[0] - lbl_h, rect[1], rect[0], rect[1] + max(w, len(label) * font_size))
                dm_label = create_annotation_group(34, label_rect, text=label, text_color=shape_color,
                                                    font_size=font_size)
                metadata['annotations'].append(dm_label)
            continue

        # ---- TextReporter: plain free-text user label (e.g. "テスト"), distinct from the
        # templated FormatText/TextInfo/ScaleTextInfo variants handled in the fallback below.
        if anno_type == 'TextReporter':
            text_node = anno.find('Text')
            text = text_node.text.strip() if text_node is not None and text_node.text else None
            if text:
                rect_w, rect_h = (w, h) if w >= 1 and h >= 1 else _auto_size_from_text(text, font_size)
                dm_anno = create_annotation_group(34, _norm_rect(x, y, rect_w, rect_h), text=text,
                                                   text_color=fg_color, font_size=font_size)
                metadata['annotations'].append(dm_anno)
            continue

        # ---- InstrumentInfoReporter: the "HT/Magnification/Specimen/Comment" info block.
        # Always reported at DisplayLocation (0,0) with a near-zero BorderSize - an earlier
        # version of this code treated that signature as "never actually placed on the canvas"
        # and skipped it, on the theory that it was UI chrome already covered by --metadata's
        # Microscope Info injection. A real-app side-by-side comparison showed SightX actually
        # does draw this block on the image canvas, anchored at the top-left corner - (0,0) is a
        # literal anchor for this type, not a "not placed" signal. Kept in addition to
        # --metadata's injection since that's a separate DM tag (not an on-canvas annotation).
        if anno_type == 'InstrumentInfoReporter':
            format_node = anno.find('FormatText')
            if format_node is not None and format_node.text:
                text = _replace_vars(anno, format_node.text)
                rect_w, rect_h = (w, h) if w >= 1 and h >= 1 else _auto_size_from_text(text, font_size)
                dm_anno = create_annotation_group(34, _norm_rect(x, y, rect_w, rect_h), text=text,
                                                   text_color=fg_color, font_size=font_size)
                metadata['annotations'].append(dm_anno)
            continue

        # ---- CustomAreaLUTReporter: the "set contrast/LUT from this area" tool. Its own oval
        # outline does not appear to be persisted in SightX's static view (no oval is visible at
        # the position this annotation's box reports - always centered exactly on the image, in
        # both real test files, which is not where the real visible circle in either file sits).
        # What *is* visible is a full-canvas crosshair through the box's center, in PenColor, when
        # both Diagonal_TL_BR/Diagonal_TR_BL are true. An earlier version of this code (wrongly)
        # drew a 45-degree diagonal confined to the box itself for these flags and was removed for
        # not matching SightX; this is the corrected interpretation - verified against the box
        # being centered exactly on (img_w/2, img_h/2) in both samples and the real GMS/SightX
        # screenshots showing edge-to-edge axis-aligned guide lines, not a diagonal confined to a
        # small box.
        if anno_type == 'CustomAreaLUTReporter':
            diag_tl = anno.find('Diagonal_TL_BR')
            diag_tr = anno.find('Diagonal_TR_BL')
            if (diag_tl is not None and diag_tl.text == 'true' and
                    diag_tr is not None and diag_tr.text == 'true' and img_w and img_h):
                cx, cy = x + w / 2.0, y + h / 2.0
                dm_h = create_annotation_group(2, (cy, 0.0, cy, float(img_w)), text_color=pen_color_raw)
                dm_v = create_annotation_group(2, (0.0, cx, float(img_h), cx), text_color=pen_color_raw)
                metadata['annotations'].append(dm_h)
                metadata['annotations'].append(dm_v)
            continue

        # ---- Scale-bar family: the native scale bar (template) and MicronbarRect/MicronbarValue
        # handling in the fallback below already represent these visually; FOVReporter's box is
        # degenerate-sized chrome with no visible counterpart in either real sample.
        if anno_type in ('ScaleReporter', 'FOVReporter'):
            continue

        # ---- Fallback (older child-tag heuristic) for any AnnoType not covered above - kept for
        # robustness against annotation kinds outside the two real files this was verified
        # against (e.g. MicronbarRectangleReporter/MicronbarTextReporter, or an unrecognized
        # AnnoType if a file doesn't carry the i:type attribute at all).
        text = None
        val_node = anno.find('./TextInfo/MicronbarValue')
        if val_node is not None:
            unit_node_anno = anno.find('./TextInfo/MicronbarUnit')
            text = f"{val_node.text} {unit_node_anno.text if unit_node_anno is not None else ''}".strip()
        else:
            format_node = anno.find('FormatText')
            if format_node is not None and format_node.text:
                text = format_node.text
            else:
                plain_text_node = anno.find('Text')
                if plain_text_node is not None and plain_text_node.text:
                    text = plain_text_node.text.strip()

        sl_w = anno.find('.//LatestStringLayoutSize/width')
        sl_h = anno.find('.//LatestStringLayoutSize/height')
        if sl_w is not None and sl_h is not None:
            w, h = float(sl_w.text), float(sl_h.text)

        if (w < 1 or h < 1) and x == 0 and y == 0:
            continue
        elif w < 1 or h < 1:
            w, h = _auto_size_from_text(text, font_size)

        rect = _norm_rect(x, y, w, h)

        is_text = (anno.find('FormatText') is not None or anno.find('TextInfo') is not None
                   or anno.find('ScaleTextInfo') is not None or anno.find('Text') is not None)
        is_circle = anno.find('CenterCircle') is not None
        is_rect = anno.find('RectangleInfo') is not None or anno.find('MicronbarRect') is not None
        is_line = anno.find('LineInfo') is not None
        is_derived_region = anno.find('DerivedNo') is not None

        if anno.find('ScaleInfo') is not None:
            continue

        if is_text and text:
            text = _replace_vars(anno, text)
            dm_anno = create_annotation_group(34, rect, text=text, text_color=fg_color, font_size=font_size)
            metadata['annotations'].append(dm_anno)
        elif is_circle:
            dm_anno = create_annotation_group(6, rect, text_color=shape_color, filled=is_filled)
            metadata['annotations'].append(dm_anno)
        elif is_line:
            dm_anno = create_annotation_group(2, rect, text_color=shape_color)
            metadata['annotations'].append(dm_anno)
        elif is_rect or is_derived_region:
            dm_anno = create_annotation_group(5, rect, text_color=shape_color, filled=is_filled)
            metadata['annotations'].append(dm_anno)
        elif w >= 1 and h >= 1 and anno.find('DataInfo') is None:
            is_cross_visible = any(
                anno.find(tag) is not None and anno.find(tag).text == 'true'
                for tag in ('IsCenterCrossLineVisible', 'IsHorizontalAuxiliaryLineVisible',
                            'IsVerticalAuxiliaryLineVisible')
            )
            has_arrow = any(
                anno.find(tag) is not None and anno.find(tag).text not in (None, 'None')
                for tag in ('BeginArrowType', 'EndArrowType', 'HorizontalArrowType', 'VerticalArrowType')
            )
            if is_cross_visible or has_arrow:
                dm_anno = create_annotation_group(5, rect, text_color=shape_color, filled=False)
                metadata['annotations'].append(dm_anno)

    return metadata

def compute_contrast_limits(image_data, contrast_info):
    """
    Derive the (LowLimit, HighLimit) display-range values GMS should use, matching what
    SightX Viewer would show for this same pixel data (see ImageLookupTableReporter notes
    in extract_metadata). Falls back to a plain min/max stretch if no LUT info was found.

    Diffraction patterns (`is_log_scale`) are displayed log-compressed in SightX. GMS has no
    native log-scale toggle, and JEOL's declared LUT range for these files is the full
    0-65535 sensor range, which - applied linearly - crushes every diffraction spot to black
    except the saturated direct beam (its real dynamic range is a ~30-300 count background vs.
    a ~65535 direct beam). Approximated instead by clipping HighLimit to the 99.9th percentile
    of the *actual* pixel data (not the declared range) - empirically verified in real
    DigitalMicrograph against two real diffraction files to make every spot visible again (see
    docs/CURRENT_STATUS.md section 13).

    `ImageDisplayInfo/Gamma` was also tried (clipping HighLimit alone still left things a little
    flat) but real-GMS testing showed it is *not* a "1.0 = neutral" curve: the template ships
    with `Gamma=0.5`, and that value (not 1.0) is what reproduces a plain linear stretch on
    screen - explicitly patching `Gamma=1.0` instead washed the whole image to near-white in
    real DigitalMicrograph. Since 0.5 is already the template's default, it's left untouched
    rather than patched.
    """
    if not contrast_info:
        return float(image_data.min()), float(image_data.max())

    if contrast_info.get('is_log_scale'):
        low = float(image_data.min())
        high = float(np.percentile(image_data, 99.9))
        if high <= low:
            high = low + 1.0
        return low, high

    if contrast_info['auto_adjust']:
        lo_pct = contrast_info['lower_trim_pct']
        hi_pct = 100.0 - contrast_info['upper_trim_pct']
        low = float(np.percentile(image_data, lo_pct))
        high = float(np.percentile(image_data, hi_pct))
    else:
        low = contrast_info['lower_limit']
        high = contrast_info['upper_limit']
        if low is None: low = float(image_data.min())
        if high is None: high = float(image_data.max())

    if high <= low:
        high = low + 1.0
    return low, high

def _scalebar_length_px(image_width_px, pixel_size, unit):
    """Return (bar_px, label_str) for a 'nice' scale bar ~15% of image width, or (None,None)."""
    if pixel_size <= 0 or unit in ('px', ''):
        return None, None
    target = image_width_px * pixel_size * 0.15
    # Generate candidates: 1,2,5 × 10^n
    candidates = []
    for exp in range(-4, 7):
        for m in (1, 2, 5):
            candidates.append(m * (10 ** exp))
    best = min(candidates, key=lambda v: abs(v - target))
    bar_px = best / pixel_size
    if bar_px < 5 or bar_px > image_width_px * 0.8:
        return None, None
    # Format label
    if unit == 'nm':
        if best >= 1000:
            label = f"{best/1000:.4g} μm"
        elif best < 1:
            label = f"{best*1000:.4g} pm"
        else:
            label = f"{best:.4g} nm"
    elif unit == 'um':
        if best >= 1000:
            label = f"{best/1000:.4g} mm"
        elif best < 0.001:
            label = f"{best*1e6:.4g} pm"
        else:
            label = f"{best:.4g} μm"
    elif unit == '1/nm':
        label = f"{best:.4g} 1/nm"
    else:
        label = f"{best:.4g} {unit}"
    return int(round(bar_px)), label


def _burn_scalebar(img, pixel_size, unit, bar_scale=1.0, font_scale=1.0):
    """Draw a scale bar with label onto a Pillow L-mode (8-bit grayscale) image. Modifies in-place."""
    from PIL import ImageDraw, ImageFont
    w, h = img.size
    bar_px, label = _scalebar_length_px(w, pixel_size, unit)
    if bar_px is None:
        return
    draw = ImageDraw.Draw(img)
    margin = max(12, w // 40)
    bar_thick = max(2, int(h // 120 * bar_scale))
    bar_y1 = h - margin - bar_thick
    bar_y2 = h - margin
    bar_x1 = margin
    bar_x2 = bar_x1 + bar_px
    # Black outline then white fill for visibility on any image
    outline = max(1, bar_thick // 3)
    draw.rectangle([bar_x1 - outline, bar_y1 - outline, bar_x2 + outline, bar_y2 + outline], fill=0)
    draw.rectangle([bar_x1, bar_y1, bar_x2, bar_y2], fill=255)
    # Text label centred above the bar
    font_size = max(6, int(h // 50 * font_scale))
    font = None
    for fname in ("arialbd.ttf", "Arial Bold.ttf", "DejaVuSans-Bold.ttf", "DejaVuSans.ttf"):
        try:
            font = ImageFont.truetype(fname, font_size)
            break
        except OSError:
            continue
    if font is None:
        font = ImageFont.load_default()
    bbox = draw.textbbox((0, 0), label, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    tx = bar_x1 + (bar_px - tw) // 2 - bbox[0]
    ty = bar_y1 - th - max(3, bar_thick // 2) - bbox[1]
    draw.text((tx + 1, ty + 1), label, fill=0, font=font)
    draw.text((tx, ty), label, fill=255, font=font)


def convert_file_to_raster(src_path, dst_path, fmt, image_data, lo, hi,
                            pixel_size=1.0, unit='px', scalebar=False,
                            bar_scale=1.0, font_scale=1.0):
    from PIL import Image
    range_ = max(float(hi) - float(lo), 1.0)
    clipped = np.clip(image_data.astype(np.float32), lo, hi)
    norm = ((clipped - lo) / range_ * 255.0).astype(np.uint8)
    img = Image.fromarray(norm)
    if scalebar:
        _burn_scalebar(img, pixel_size, unit, bar_scale, font_scale)
    if fmt == 'jpg':
        img.save(dst_path, format='JPEG', quality=95)
    else:
        img.save(dst_path, format='PNG')

def convert_file(tif_path, output_path=None, scalebar=True, markers=False, metadata_ext=False, output_format='dm3', bar_scale=1.0, font_scale=1.0):
    if output_path:
        # An explicit --output extension (.dm3/.dm4) always wins over --format.
        ext = os.path.splitext(output_path)[1].lstrip(".").lower()
        if ext in ('dm3', 'dm4'):
            output_format = ext
    else:
        base, _ = os.path.splitext(tif_path)
        output_path = base + "." + output_format


    print(f"Reading: {tif_path}")
    
    with tifffile.TiffFile(tif_path) as tif:
        page = tif.pages[0]
        image_data = page.asarray()
        tags = page.tags
        metadata = {}
        if 270 in tags:
            xml_data = read_tag270_text(tif, page.tags[270])
            print("Found XML metadata in Tag 270")
            xml_data = clean_xml(xml_data)
            metadata = extract_metadata(xml_data, img_shape=image_data.shape)
            print(f"Extracted Metadata: {metadata}")
                
    scale = metadata.get('pixel_size', 1.0)
    unit = metadata.get('unit', 'px')
    mag = metadata.get('magnification', 1)
    volt = metadata.get('voltage', 0.0)

    annotations_list = metadata.get('annotations', []) if markers else []
    metadata_dict = metadata.get('microscope_info', {}) if metadata_ext else {}
    contrast_info = metadata.get('contrast')
    contrast_low, contrast_high = compute_contrast_limits(image_data, contrast_info)

    # Always disable GMS AutoSurvey (DoAutoSurvey=0) once we've patched an explicit
    # LowLimit/HighLimit. GMS runs its own sparse-pixel AutoSurvey synchronously at open
    # time when DoAutoSurvey=1, and — empirically reproduced via a scripted open/close
    # loop in real DigitalMicrograph (see docs/CURRENT_STATUS.md) — that survey collapses
    # LowLimit to equal HighLimit in the large majority of opens (~87% in an 8-open test),
    # since its sparse sample often fails to catch any pixel near the low end of a narrow
    # percentile-trimmed range. A collapsed (Low == High) range is a degenerate contrast
    # window GMS renders as a single flat color across the whole image, matching the
    # intermittent "image opens blank/flat, reopening looks fine" bug reports. Disabling
    # AutoSurvey removes GMS's own contrast computation from the picture entirely, so the
    # values we compute and patch are what gets displayed, deterministically, every time.
    disable_auto_survey = True

    is_log_scale = (contrast_info or {}).get('is_log_scale', False)

    if is_log_scale:
        # For diffraction/log-scale images, apply log1p transform to the raw pixel data
        # instead of linear clipping. This replicates SightX's log-scale display (storing
        # log values + linear GMS LUT gives the same visual result as linear values + log
        # LUT) — GMS has no native log-scale toggle, so this is the only way to approximate
        # that appearance. (This used to also double as an AutoSurvey-reliability aid; that
        # reasoning no longer applies now that AutoSurvey is always disabled above, but the
        # transform itself is still needed for the log-scale visual approximation.)
        log_data = np.log1p(image_data.astype(np.float64))
        log_max = float(log_data.max())
        if log_max > 0:
            image_data = (log_data / log_max * 65535.0).clip(0, 65535).astype(np.uint16)
        else:
            image_data = np.zeros(image_data.shape, dtype=np.uint16)
        contrast_low = 0.0
        contrast_high = 65535.0
    # Real-space images: LowLimit/HighLimit (patched below) control the initial display
    # window on their own; the pixel data itself is left at its full original dynamic
    # range (not clipped to [contrast_low, contrast_high]) so widening the contrast
    # sliders in GMS can still recover highlight/shadow detail instead of clipped/lost data.

    if output_format in ('jpg', 'png'):
        print(f"  Saving raster image to: {output_path}")
        try:
            convert_file_to_raster(tif_path, output_path, output_format, image_data,
                                   contrast_low, contrast_high,
                                   pixel_size=scale, unit=unit, scalebar=scalebar,
                                   bar_scale=bar_scale, font_scale=font_scale)
            print(f"  Done saving {output_format.upper()}.")
        except Exception as e:
            print(f"  [Error] Failed to save {output_format.upper()}: {e}")
            import traceback
            traceback.print_exc()
        return

    if unit == '1/nm': template_name = 'template_diff.dm3'
    else: template_name = 'template_image.dm3'

    try: base_path = sys._MEIPASS
    except Exception: base_path = os.path.dirname(os.path.abspath(__file__))

    template_path = os.path.join(base_path, 'templates', template_name)

    if not os.path.exists(template_path):
        print(f"Error: {template_name} not found at {template_path}")
        return

    print(f"  Attempting to save to: {output_path}")
    try:
        patch_template(
            template_path,
            output_path,
            image_data,
            scale,
            scale,
            unit,
            magnification=mag,
            voltage=volt,
            contrast_low=contrast_low,
            contrast_high=contrast_high,
            scalebar_enabled=scalebar,
            markers_enabled=markers,
            metadata_enabled=metadata_ext,
            annotations_list=annotations_list,
            metadata_dict=metadata_dict,
            output_format=output_format,
            disable_auto_survey=disable_auto_survey,
        )
        print(f"  Done saving {output_format.upper()}.")
    except Exception as e:
        print(f"  [Error] Failed to save {output_format.upper()}: {e}")
        import traceback
        traceback.print_exc()

def _center_near(win, ref_x=None, ref_y=None):
    """Position win centred on (ref_x, ref_y); defaults to primary screen centre."""
    win.update_idletasks()
    w, h = win.winfo_reqwidth(), win.winfo_reqheight()
    if ref_x is None:
        ref_x = win.winfo_screenwidth() // 2
    if ref_y is None:
        ref_y = win.winfo_screenheight() // 3
    win.geometry(f"+{max(0, ref_x - w // 2)}+{max(0, ref_y - h // 2)}")
    win.lift()
    win.attributes('-topmost', True)
    win.after(200, lambda: win.attributes('-topmost', False))

def _center_window(win):
    _center_near(win)

def _win_center(win):
    """Return the screen centre (x, y) of an already-visible window."""
    win.update_idletasks()
    return win.winfo_x() + win.winfo_width() // 2, win.winfo_y() + win.winfo_height() // 2

def show_usage_dialog(parser):
    usage_text = parser.format_help()
    top = tk.Toplevel()
    top.title(_t('usage_title', version=APP_VERSION))
    top.resizable(True, True)
    st = scrolledtext.ScrolledText(top, width=72, height=20, wrap=tk.WORD, font=("Courier", 9))
    st.pack(fill="both", expand=True, padx=8, pady=8)
    st.insert("1.0", usage_text)
    st.configure(state="disabled")
    tk.Button(top, text=_t('close_btn'), command=top.destroy, width=10).pack(pady=(0, 8))
    _center_near(top)

def show_file_list_dialog(parent, files):
    top = tk.Toplevel(parent)
    top.title(_t('filelist_title', n=len(files)))
    top.resizable(True, True)
    st = scrolledtext.ScrolledText(top, width=80, height=20, wrap=tk.NONE, font=("Courier", 9))
    st.pack(fill="both", expand=True, padx=8, pady=8)
    for f in files:
        st.insert("end", f + "\n")
    st.configure(state="disabled")
    tk.Button(top, text=_t('close_btn'), command=top.destroy, width=10).pack(pady=(0, 8))
    _center_near(top, *_win_center(parent))

def _get_bundled_path(filename):
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, filename)
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), filename)

def show_licenses_dialog(parent=None):
    top = tk.Toplevel(parent)
    top.title(_t('licenses_title'))
    top.geometry("700x520")
    top.resizable(True, True)
    st = scrolledtext.ScrolledText(top, wrap="word", font=("Courier", 9))
    st.pack(fill="both", expand=True, padx=8, pady=(8, 4))
    path = _get_bundled_path('THIRD_PARTY_NOTICES.txt')
    try:
        with open(path, encoding='utf-8') as f:
            st.insert("end", f.read())
    except Exception as e:
        st.insert("end", f"Could not load notice file: {e}\n\nExpected: {path}")
    st.configure(state="disabled")
    tk.Button(top, text=_t('close_btn'), command=top.destroy, width=10).pack(pady=(0, 8))
    _center_near(top, *(_win_center(parent) if parent else (None, None)))

def show_about_dialog(parent=None):
    top = tk.Toplevel(parent)
    top.title(_t('about_title'))
    top.resizable(False, False)
    tk.Label(top, text=_t('about_body', version=APP_VERSION),
             justify="left", padx=16, pady=8, font=("", 10)).pack(anchor="w")
    link = tk.Label(top, text=GITHUB_URL, fg="blue", cursor="hand2",
                    padx=16, font=("", 9, "underline"))
    link.pack(anchor="w")
    link.bind("<Button-1>", lambda _: webbrowser.open(GITHUB_URL))
    btn_frame = tk.Frame(top)
    btn_frame.pack(pady=(8, 12))
    tk.Button(btn_frame, text=_t('licenses_btn'),
              command=lambda: show_licenses_dialog(top), width=20).pack(side="left", padx=4)
    tk.Button(btn_frame, text=_t('close_btn'), command=top.destroy, width=10).pack(side="left", padx=4)
    _center_near(top, *(_win_center(parent) if parent else (None, None)))

def show_launcher_dialog(initial_files=None, parser=None):
    """
    Main launcher dialog with EN/JA toggle and adjustable scale bar controls.
    Returns (file_list, opts_dict) or None if cancelled.
    """
    queued = list(initial_files) if initial_files else []
    result = {}

    root = tk.Tk()
    root.resizable(False, False)

    # StringVars for all translatable text
    sv_subtitle  = tk.StringVar()
    sv_drop      = tk.StringVar()
    sv_count     = tk.StringVar()
    sv_browse    = tk.StringVar()
    sv_filelist  = tk.StringVar()
    sv_scalebar  = tk.StringVar()
    sv_bar_lbl   = tk.StringVar()
    sv_font_lbl  = tk.StringVar()
    sv_markers   = tk.StringVar()
    sv_metadata  = tk.StringVar()
    sv_convert   = tk.StringVar()
    sv_cancel    = tk.StringVar()
    sv_lang_btn  = tk.StringVar()

    # Value vars
    fmt_var        = tk.StringVar(value="dm3")
    scalebar_var   = tk.BooleanVar(value=True)
    markers_var    = tk.BooleanVar(value=True)
    metadata_var   = tk.BooleanVar(value=True)
    bar_scale_str  = tk.StringVar(value="1.0")
    font_scale_str = tk.StringVar(value="1.0")

    # ── Header ──────────────────────────────────────────────────
    hdr = tk.Frame(root, bg="#1a2a4a", pady=6)
    hdr.pack(fill="x")
    lang_btn = tk.Button(hdr, textvariable=sv_lang_btn,
                         bg="#2a4a6a", fg="white", relief="flat", bd=0,
                         padx=6, pady=2, font=("", 8),
                         command=lambda: _toggle_lang())
    lang_btn.pack(side="right", padx=10, pady=4, anchor="n")
    left_hdr = tk.Frame(hdr, bg="#1a2a4a")
    left_hdr.pack(side="left", padx=14, pady=2)
    tk.Label(left_hdr, text=f"{APP_NAME}  v{APP_VERSION}", bg="#1a2a4a", fg="white",
             font=("", 13, "bold")).pack(anchor="w")
    tk.Label(left_hdr, textvariable=sv_subtitle, bg="#1a2a4a", fg="#80c8e8",
             font=("", 9)).pack(anchor="w")

    # ── Drop zone ────────────────────────────────────────────────
    dz_outer = tk.Frame(root, padx=12, pady=8)
    dz_outer.pack(fill="x")
    dz = tk.Frame(dz_outer, relief="groove", bd=2, bg="#f0f4f8", height=72, cursor="target")
    dz.pack(fill="x")
    dz.pack_propagate(False)
    tk.Label(dz, textvariable=sv_drop, bg="#f0f4f8", fg="#4a6080",
             justify="center", font=("", 9)).place(relx=0.5, rely=0.5, anchor="center")

    # ── Count row ────────────────────────────────────────────────
    row_count = tk.Frame(root, padx=12)
    row_count.pack(fill="x", pady=2)
    tk.Label(row_count, textvariable=sv_count, anchor="w").pack(side="left")
    tk.Button(row_count, textvariable=sv_browse,
              command=lambda: _browse(), width=10).pack(side="right", padx=4)
    tk.Button(row_count, textvariable=sv_filelist,
              command=lambda: show_file_list_dialog(root, collect_tif_files(queued)),
              width=14).pack(side="right")

    # ── Format selector ──────────────────────────────────────────
    fmt_frame = tk.LabelFrame(root, padx=8, pady=4)
    fmt_frame.pack(fill="x", padx=12, pady=4)
    for val, lbl in [("dm3", "DM3"), ("dm4", "DM4"), ("png", "PNG"), ("jpg", "JPG")]:
        tk.Radiobutton(fmt_frame, text=lbl, variable=fmt_var, value=val).pack(side="left", padx=6)

    # ── Options ──────────────────────────────────────────────────
    opt_frame = tk.LabelFrame(root, padx=8, pady=4)
    opt_frame.pack(fill="x", padx=12, pady=4)

    tk.Checkbutton(opt_frame, textvariable=sv_scalebar, variable=scalebar_var).pack(anchor="w")

    # Scale bar size controls
    sb_sz = tk.Frame(opt_frame, padx=16)
    sb_sz.pack(fill="x", pady=2)
    tk.Label(sb_sz, textvariable=sv_bar_lbl, anchor="e", width=12).grid(row=0, column=0, sticky="e")
    tk.Spinbox(sb_sz, textvariable=bar_scale_str, width=5,
               values=("0.5", "1.0", "1.5", "2.0", "3.0")).grid(row=0, column=1, padx=(4, 2), sticky="w")
    tk.Label(sb_sz, text="×").grid(row=0, column=2, padx=(0, 12))
    tk.Label(sb_sz, textvariable=sv_font_lbl, anchor="e", width=12).grid(row=0, column=3, sticky="e")
    tk.Spinbox(sb_sz, textvariable=font_scale_str, width=5,
               values=("0.5", "1.0", "1.5", "2.0", "3.0")).grid(row=0, column=4, padx=(4, 2), sticky="w")
    tk.Label(sb_sz, text="×").grid(row=0, column=5)
    # Spinbox with values= defaults to first item; re-assert the textvariable value.
    bar_scale_str.set("1.0")
    font_scale_str.set("1.0")

    tk.Checkbutton(opt_frame, textvariable=sv_markers, variable=markers_var).pack(anchor="w")
    tk.Checkbutton(opt_frame, textvariable=sv_metadata, variable=metadata_var).pack(anchor="w")

    # ── Buttons ──────────────────────────────────────────────────
    btn_frame = tk.Frame(root, padx=12, pady=10)
    btn_frame.pack(fill="x")

    def on_ok():
        files = collect_tif_files(queued)
        if not files:
            messagebox.showwarning(APP_NAME, _t('no_files'), parent=root)
            return
        result['files']      = files
        result['format']     = fmt_var.get()
        result['scalebar']   = scalebar_var.get()
        result['bar_scale']  = float(bar_scale_str.get())
        result['font_scale'] = float(font_scale_str.get())
        result['markers']    = markers_var.get()
        result['metadata']   = metadata_var.get()
        root.update_idletasks()
        result['ref_x'] = root.winfo_x() + root.winfo_width() // 2
        result['ref_y'] = root.winfo_y() + root.winfo_height() // 2
        root.destroy()

    def on_cancel():
        result.clear()
        root.destroy()

    tk.Button(btn_frame, textvariable=sv_convert, command=on_ok,
              width=10, bg="#2a6a9a", fg="white", font=("", 10, "bold")).pack(side="left")
    tk.Button(btn_frame, text="USAGE", width=7,
              command=lambda: show_usage_dialog(parser) if parser else None).pack(side="left", padx=(8, 0))
    tk.Button(btn_frame, text="ABOUT", width=7,
              command=lambda: show_about_dialog(root)).pack(side="left", padx=4)
    tk.Button(btn_frame, textvariable=sv_cancel, command=on_cancel, width=9).pack(side="right")

    # ── DnD ──────────────────────────────────────────────────────
    if _HAS_WINDND:
        def _on_drop(files):
            for f in files:
                queued.append(f.decode('mbcs') if isinstance(f, bytes) else f)
            _apply_lang()
        windnd.hook_dropfiles(dz,   func=_on_drop)
        windnd.hook_dropfiles(root, func=_on_drop)

    def _browse():
        paths = filedialog.askopenfilenames(
            parent=root, title="Select TIF files",
            filetypes=[("TIF/TIFF files", "*.tif *.tiff"), ("All files", "*.*")])
        if paths:
            queued.extend(paths)
            _apply_lang()

    # ── Language helpers ──────────────────────────────────────────
    def _apply_lang():
        n = len(collect_tif_files(queued))
        root.title(_t('window_title', version=APP_VERSION))
        sv_subtitle.set(_t('app_subtitle'))
        sv_drop.set(_t('drop_hint', n=n) if n else _t('drop_empty'))
        sv_count.set(_t('count_label', n=n))
        sv_browse.set(_t('browse'))
        sv_filelist.set(_t('file_list_btn'))
        fmt_frame.config(text=_t('output_format'))
        opt_frame.config(text=_t('options'))
        sv_scalebar.set(_t('scalebar_cb'))
        sv_bar_lbl.set(_t('bar_size'))
        sv_font_lbl.set(_t('font_size_lbl'))
        sv_markers.set(_t('markers_cb'))
        sv_metadata.set(_t('metadata_cb'))
        sv_convert.set(_t('convert_btn'))
        sv_cancel.set(_t('cancel_btn'))
        sv_lang_btn.set(_t('toggle_lang'))

    def _toggle_lang():
        _UI_LANG[0] = 'ja' if _UI_LANG[0] == 'en' else 'en'
        _apply_lang()

    _apply_lang()
    root.protocol("WM_DELETE_WINDOW", on_cancel)
    _center_window(root)
    root.mainloop()

    if result.get('files'):
        files = result['files']
        choice = {k: result[k] for k in ('format', 'scalebar', 'bar_scale', 'font_scale', 'markers', 'metadata')}
        return files, choice, (result.get('ref_x'), result.get('ref_y'))
    return None

def collect_tif_files(paths):
    """
    Expand a list of dropped/CLI paths (files and/or directories, any mix) into a flat,
    de-duplicated, order-preserving list of .tif/.tiff file paths. Directories are scanned
    recursively (os.walk) so dropping a whole folder tree converts everything inside it.
    """
    seen = set()
    files = []
    for p in paths:
        if os.path.isfile(p):
            if p.lower().endswith(('.tif', '.tiff')):
                real = os.path.abspath(p)
                if real not in seen:
                    seen.add(real)
                    files.append(p)
        elif os.path.isdir(p):
            for dirpath, _dirnames, filenames in os.walk(p):
                for f in sorted(filenames):
                    if f.lower().endswith(('.tif', '.tiff')):
                        full = os.path.join(dirpath, f)
                        real = os.path.abspath(full)
                        if real not in seen:
                            seen.add(real)
                            files.append(full)
    return files

def show_options_popup(file_count):
    """
    Lightweight options dialog shown only when the tool is started by dragging files/folders
    onto the executable (i.e. there was no opportunity to pass --format/--markers/--metadata
    on a command line). Uses only tkinter (Python stdlib, bundled into the PyInstaller onefile
    binary) so it has no extra runtime/environment dependency beyond the binary itself.
    Returns a dict of chosen options, or None if the user cancelled.
    """
    result = {}

    root = tk.Tk()
    root.title(f"tool-jeoltif2dm v{APP_VERSION}")
    root.resizable(False, False)

    tk.Label(root, text=f"{file_count} 件のTIFファイルを変換します。", padx=12, pady=10).pack(anchor="w")

    fmt_var = tk.StringVar(value="dm3")
    fmt_frame = tk.LabelFrame(root, text="出力フォーマット", padx=8, pady=4)
    fmt_frame.pack(fill="x", padx=12, pady=4)
    tk.Radiobutton(fmt_frame, text="DM3", variable=fmt_var, value="dm3").pack(side="left", padx=8)
    tk.Radiobutton(fmt_frame, text="DM4", variable=fmt_var, value="dm4").pack(side="left", padx=8)

    markers_var = tk.BooleanVar(value=True)
    metadata_var = tk.BooleanVar(value=True)
    opt_frame = tk.LabelFrame(root, text="オプション", padx=8, pady=4)
    opt_frame.pack(fill="x", padx=12, pady=4)
    tk.Checkbutton(opt_frame, text="アノテーション/マーカーを含める", variable=markers_var).pack(anchor="w")
    tk.Checkbutton(opt_frame, text="拡張メタデータを含める", variable=metadata_var).pack(anchor="w")

    def on_ok():
        result['format'] = fmt_var.get()
        result['markers'] = markers_var.get()
        result['metadata'] = metadata_var.get()
        root.destroy()

    def on_cancel():
        result.clear()
        root.destroy()

    btn_frame = tk.Frame(root, padx=12, pady=12)
    btn_frame.pack(fill="x")
    tk.Button(btn_frame, text="変換開始", command=on_ok, width=12).pack(side="right", padx=4)
    tk.Button(btn_frame, text="キャンセル", command=on_cancel, width=12).pack(side="right")

    root.protocol("WM_DELETE_WINDOW", on_cancel)
    root.update_idletasks()
    sw, sh = root.winfo_screenwidth(), root.winfo_screenheight()
    w, h = root.winfo_width(), root.winfo_height()
    root.geometry(f"+{(sw - w) // 2}+{(sh - h) // 3}")
    root.lift()
    root.attributes('-topmost', True)
    root.after(200, lambda: root.attributes('-topmost', False))
    root.mainloop()

    return result or None

def show_completion_popup(summary, log_path):
    ok_count   = sum(1 for s in summary if s['ok'])
    fail_count = len(summary) - ok_count
    lines = [_t('complete_ok', ok=ok_count, fail=fail_count)]
    if fail_count:
        lines.append("")
        lines.append(_t('complete_fail_hdr'))
        for s in summary:
            if not s['ok']:
                lines.append(f"  - {os.path.basename(s['input'])}: {s['error']}")
    lines.append("")
    lines.append(_t('complete_log', path=log_path))

    root = tk.Tk()
    root.withdraw()
    title = _t('complete_title', version=APP_VERSION)
    if fail_count:
        messagebox.showwarning(title, "\n".join(lines))
    else:
        messagebox.showinfo(title, "\n".join(lines))
    root.destroy()

def run_batch(files, output_format, markers, metadata_ext, scalebar=True, log_path=None,
              bar_scale=1.0, font_scale=1.0):
    """
    Convert every file in `files` with the same options, never aborting the whole batch on a
    single failure. Success is verified by checking the expected output file actually exists
    afterward, since convert_file() catches and merely prints/logs its own internal errors
    rather than raising them.
    """
    summary = []
    log_lines = [
        f"{APP_NAME} v{APP_VERSION} batch run",
        f"format={output_format} markers={markers} metadata={metadata_ext} scalebar={scalebar}",
        f"bar_scale={bar_scale} font_scale={font_scale}",
        f"{len(files)} file(s)",
        "",
    ]
    for f in files:
        base, _ = os.path.splitext(f)
        expected_output = base + "." + output_format
        entry = {'input': f, 'output': expected_output, 'ok': False, 'error': None}
        try:
            convert_file(f, scalebar=scalebar, markers=markers, metadata_ext=metadata_ext,
                         output_format=output_format, bar_scale=bar_scale, font_scale=font_scale)
            if os.path.exists(expected_output):
                entry['ok'] = True
                log_lines.append(f"OK: {f} -> {expected_output}")
            else:
                entry['error'] = "output file was not created"
                log_lines.append(f"FAIL: {f} -> output file was not created")
        except Exception as e:
            entry['error'] = str(e)
            log_lines.append(f"FAIL: {f} -> {e}")
        summary.append(entry)

    if log_path:
        try:
            with open(log_path, 'w', encoding='utf-8') as lf:
                lf.write('\n'.join(log_lines))
        except Exception:
            pass
    return summary

def _show_result_dialog(root, summary, log_path, ref_x, ref_y, total, cancelled=False):
    ok_count   = sum(1 for s in summary if s['ok'])
    fail_count = len(summary) - ok_count

    dlg = tk.Toplevel(root)
    dlg.resizable(False, False)
    dlg.title(_t('complete_title', version=APP_VERSION))
    dlg.protocol("WM_DELETE_WINDOW", root.destroy)

    if cancelled:
        lines = [_t('cancelled_msg', ok=ok_count, total=total)]
        if ok_count < total and fail_count:
            lines.append("")
            lines.append(_t('complete_fail_hdr'))
            for s in summary:
                if not s['ok']:
                    lines.append(f"  - {os.path.basename(s['input'])}: {s['error']}")
    else:
        lines = [_t('complete_ok', ok=ok_count, fail=fail_count)]
        if fail_count:
            lines.append("")
            lines.append(_t('complete_fail_hdr'))
            for s in summary:
                if not s['ok']:
                    lines.append(f"  - {os.path.basename(s['input'])}: {s['error']}")

    if log_path:
        lines.append("")
        lines.append(_t('complete_log', path=log_path))

    tk.Label(dlg, text="\n".join(lines), justify="left", padx=16, pady=12,
             font=("", 10)).pack(anchor="w")
    tk.Button(dlg, text=_t('close_btn'), command=root.destroy, width=10).pack(pady=(0, 12))

    _center_near(dlg, ref_x, ref_y)
    dlg.focus_set()

def run_with_progress(files, choice, log_path, ref_x=None, ref_y=None):
    """Show a progress dialog and run conversion in a background thread with cancel support."""
    progress_q   = _queue.Queue()
    cancel_event = threading.Event()
    total        = len(files)

    root = tk.Tk()
    root.withdraw()

    top = tk.Toplevel(root)
    top.title(_t('progress_title'))
    top.resizable(False, False)
    top.protocol("WM_DELETE_WINDOW", lambda: None)

    sv_status = tk.StringVar(value=_t('progress_label', n=0, total=total))
    tk.Label(top, textvariable=sv_status, font=("", 10), anchor="w",
             padx=16).pack(fill="x", pady=(12, 2))

    sv_file = tk.StringVar(value="")
    tk.Label(top, textvariable=sv_file, font=("", 9), fg="#555555",
             anchor="w", padx=16, pady=2, wraplength=380).pack(fill="x")

    bar_frame = tk.Frame(top, padx=16, pady=6)
    bar_frame.pack(fill="x")
    pb = ttk.Progressbar(bar_frame, length=400, maximum=max(total, 1), mode='determinate')
    pb.pack(fill="x")

    sv_cancel_btn = tk.StringVar(value=_t('cancel_btn'))
    btn_cancel = tk.Button(top, textvariable=sv_cancel_btn, width=12,
                           command=lambda: _do_cancel())
    btn_cancel.pack(pady=(4, 14))

    def _do_cancel():
        cancel_event.set()
        sv_cancel_btn.set(_t('cancelling'))
        btn_cancel.config(state='disabled')

    _center_near(top, ref_x, ref_y)

    result_holder    = [None]
    cancelled_holder = [False]

    def worker():
        summary   = []
        log_lines = [
            f"{APP_NAME} v{APP_VERSION} batch run",
            f"format={choice['format']} markers={choice['markers']} "
            f"metadata={choice['metadata']} scalebar={choice['scalebar']}",
            f"bar_scale={choice['bar_scale']} font_scale={choice['font_scale']}",
            f"{total} file(s)",
            "",
        ]
        for i, f in enumerate(files):
            if cancel_event.is_set():
                progress_q.put(('cancelled', i, f, summary, log_lines))
                return
            progress_q.put(('progress', i, f, None, None))
            base, _ = os.path.splitext(f)
            expected = base + "." + choice['format']
            entry = {'input': f, 'output': expected, 'ok': False, 'error': None}
            try:
                convert_file(f, scalebar=choice['scalebar'], markers=choice['markers'],
                             metadata_ext=choice['metadata'], output_format=choice['format'],
                             bar_scale=choice['bar_scale'], font_scale=choice['font_scale'])
                if os.path.exists(expected):
                    entry['ok'] = True
                    log_lines.append(f"OK: {f} -> {expected}")
                else:
                    entry['error'] = "output file was not created"
                    log_lines.append(f"FAIL: {f} -> output file was not created")
            except Exception as e:
                entry['error'] = str(e)
                log_lines.append(f"FAIL: {f} -> {e}")
            summary.append(entry)
        progress_q.put(('done', total, None, summary, log_lines))

    def _write_log(log_lines):
        if log_path:
            try:
                with open(log_path, 'w', encoding='utf-8') as lf:
                    lf.write('\n'.join(log_lines))
            except Exception:
                pass

    def poll():
        try:
            while True:
                kind, idx, fname, summary, log_lines = progress_q.get_nowait()
                if kind == 'progress':
                    sv_status.set(_t('progress_label', n=idx + 1, total=total))
                    sv_file.set(os.path.basename(fname) if fname else "")
                    pb['value'] = idx
                elif kind == 'done':
                    pb['value'] = total
                    _write_log(log_lines)
                    result_holder[0]    = summary
                    cancelled_holder[0] = False
                    root.after(200, finish)
                    return
                elif kind == 'cancelled':
                    _write_log(log_lines)
                    result_holder[0]    = summary
                    cancelled_holder[0] = True
                    root.after(200, finish)
                    return
        except _queue.Empty:
            pass
        root.after(50, poll)

    def finish():
        top.destroy()
        _show_result_dialog(root, result_holder[0], log_path, ref_x, ref_y, total,
                            cancelled=cancelled_holder[0])

    threading.Thread(target=worker, daemon=True).start()
    root.after(50, poll)
    root.mainloop()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description=f"{APP_NAME} v{APP_VERSION} - {APP_SUBTITLE}")
    parser.add_argument("inputs", nargs='*',
                         help="Target TIF file(s) and/or directory(ies) - multiple allowed, can be drag-and-dropped")
    parser.add_argument("--output", help="Path to the output file (single-input mode only)")
    parser.add_argument("--format", choices=["dm3", "dm4", "png", "jpg"], default="dm3",
                         help="Output format (default: dm3). Overridden by --output's extension.")
    parser.add_argument("--scalebar", action="store_true", help="Enable scale bar (DM3/DM4: annotation; PNG/JPG: burned into image)")
    parser.add_argument("--markers", action="store_true", help="Enable marker/annotation extraction (DM3/DM4 only)")
    parser.add_argument("--metadata", action="store_true", help="Extract and include extended microscope metadata (DM3/DM4 only)")
    parser.add_argument("--version", action="version", version=f"{APP_NAME} {APP_VERSION}")

    # Explicit option flags used by scripted/E2E invocations bypass the GUI dialog.
    explicit_flags = any(flag in sys.argv for flag in ('--format', '--markers', '--metadata', '--scalebar', '--output'))

    if len(sys.argv) == 1 or (not explicit_flags and not any(a for a in sys.argv[1:] if not a.startswith('-'))):
        # No files and no flags: show the launcher dialog for interactive use.
        res = show_launcher_dialog([], parser=parser)
        if not res:
            sys.exit(0)
        files, choice, ref_pos = res
        first_dir = os.path.dirname(os.path.abspath(files[0]))
        log_path = os.path.join(first_dir, f"{APP_NAME}_conversion_log.txt")
        run_with_progress(files, choice, log_path, *ref_pos)
        sys.exit(0)

    args = parser.parse_args()

    if explicit_flags:
        files = collect_tif_files(args.inputs)
        if not files:
            print("No .tif/.tiff files found in the given path(s).")
            sys.exit(1)
        if args.output and len(files) == 1:
            convert_file(files[0], args.output, scalebar=args.scalebar, markers=args.markers,
                         metadata_ext=args.metadata, output_format=args.format)
        else:
            if args.output and len(files) > 1:
                print("Note: --output is ignored when multiple files are given; each file is saved next to its source.")
            for f in files:
                convert_file(f, scalebar=args.scalebar, markers=args.markers,
                             metadata_ext=args.metadata, output_format=args.format)
    else:
        # Files were dropped / passed without explicit flags: show launcher pre-populated.
        res = show_launcher_dialog(args.inputs, parser=parser)
        if not res:
            sys.exit(0)
        files, choice, ref_pos = res
        first_dir = os.path.dirname(os.path.abspath(files[0]))
        log_path = os.path.join(first_dir, f"{APP_NAME}_conversion_log.txt")
        run_with_progress(files, choice, log_path, *ref_pos)

