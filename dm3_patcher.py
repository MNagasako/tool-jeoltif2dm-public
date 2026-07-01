import struct
import re
import numpy as np
import sys

def patch_simple_tag(data, sig, payload_bytes, match_index=None):
    matches = list(re.finditer(sig, data))
    if not matches:
        return data, 0
        
    old_payload_len = len(payload_bytes)
    
    if match_index is not None:
        matches = [matches[match_index]]
        
    for m in reversed(matches):
        idx = m.end()
        data = data[:idx] + payload_bytes + data[idx+old_payload_len:]
    return data, 0

def patch_array_tag(data, sig, old_bpe, new_arr_len, new_payload, match_index=None, new_dt_byte=None):
    matches = list(re.finditer(sig, data))
    if not matches:
        return data, 0
        
    if match_index is not None:
        matches = [matches[match_index]]
        
    total_diff = 0
    for m in reversed(matches):
        idx = m.end()
        old_arr_len = struct.unpack('>I', data[idx:idx+4])[0]
        old_payload_size = old_arr_len * old_bpe
        
        before = data[:idx]
        if new_dt_byte is not None:
            before = before[:-1] + bytes([new_dt_byte])
            
        after = data[idx+4+old_payload_size:]
        data = before + struct.pack('>I', new_arr_len) + new_payload + after
        
        diff = (4 + len(new_payload)) - (4 + old_payload_size)
        total_diff += diff
        
    return data, total_diff

def update_rootlen(data, total_diff):
    if total_diff == 0:
        return data
    old_rootlen = struct.unpack('>I', data[4:8])[0]
    new_rootlen = old_rootlen + total_diff
    return data[:4] + struct.pack('>I', new_rootlen) + data[8:]

def patch_template(template_path, output_path, image_array, scale_x, scale_y, unit, magnification=1, voltage=0.0, contrast_low=None, contrast_high=None, scalebar_enabled=True, markers_enabled=False, metadata_enabled=False, annotations_list=None, metadata_dict=None, disable_ast=False, output_format='dm3', disable_auto_survey=False):
    with open(template_path, 'rb') as f:
        data = f.read()

    total_diff = 0
    
    # 1. Patch Data Array
    dtype_to_gms = {
        np.dtype('int8'): (9, 1, 9, 'b'),
        np.dtype('uint8'): (6, 1, 10, 'B'), # DT_OCTET=10
        np.dtype('int16'): (1, 2, 2, 'h'), # DT_SHORT=2
        np.dtype('uint16'): (10, 2, 4, 'H'), # DT_USHORT=4
        np.dtype('int32'): (7, 4, 3, 'i'), # DT_LONG=3
        np.dtype('uint32'): (11, 4, 5, 'I'), # DT_ULONG=5
        np.dtype('float32'): (2, 4, 6, 'f'), # DT_FLOAT=6
        np.dtype('float64'): (12, 8, 7, 'd'), # DT_DOUBLE=7
    }
    
    if image_array.dtype not in dtype_to_gms:
        image_array = image_array.astype(np.float32)
        
    gms_type, pixel_depth, dt_byte, fmt = dtype_to_gms[image_array.dtype]
    bpe = pixel_depth
    
    flat = image_array.ravel()
    if flat.dtype.byteorder == '>' or (flat.dtype.byteorder == '=' and sys.byteorder == 'big'):
        flat = flat.byteswap()
    new_payload = flat.tobytes()
    new_arr_len = len(flat)
    
    # Template has DT_FLOAT (6) and old_bpe = 4
    sig_data = b'Data\x25\x25\x25\x25\x00\x00\x00\x03\x00\x00\x00\x14\x00\x00\x00\x06'
    data, diff = patch_array_tag(data, sig_data, 4, new_arr_len, new_payload, match_index=-1, new_dt_byte=dt_byte)
    total_diff += diff

    # 2. Patch Dimensions
    height, width = image_array.shape
    # Width
    sig_dim_w = b'\x14\x00\x0aDimensions\x00\x00\x00\x00\x00\x02\x15\x00\x00\x25\x25\x25\x25\x00\x00\x00\x01\x00\x00\x00\x05'
    data, diff = patch_simple_tag(data, sig_dim_w, struct.pack('<I', width), match_index=-1)
    # Height (need to find it via width offset)
    m = list(re.finditer(sig_dim_w, data))[-1]
    idx_w = m.end()
    idx_h_start = data.find(b'\x15\x00\x00\x25\x25\x25\x25\x00\x00\x00\x01\x00\x00\x00\x05', idx_w)
    idx_h = idx_h_start + 15
    data = data[:idx_h] + struct.pack('<I', height) + data[idx_h+4:]

    # 3. Patch DataType & PixelDepth
    sig_dt = b'\x15\x00\x08DataType\x25\x25\x25\x25\x00\x00\x00\x01\x00\x00\x00\x05' # It's ULONG=5 in template
    data, _ = patch_simple_tag(data, sig_dt, struct.pack('<I', gms_type), match_index=-1)
    
    sig_pd = b'\x15\x00\x0aPixelDepth\x25\x25\x25\x25\x00\x00\x00\x01\x00\x00\x00\x05'
    data, _ = patch_simple_tag(data, sig_pd, struct.pack('<I', pixel_depth), match_index=-1)

    # 4. Patch Scale & Origin (Patch all)
    sig_scale = b'\x15\x00\x05Scale\x25\x25\x25\x25\x00\x00\x00\x01\x00\x00\x00\x06'
    data, _ = patch_simple_tag(data, sig_scale, struct.pack('<f', scale_x))
    
    sig_origin = b'\x15\x00\x06Origin\x25\x25\x25\x25\x00\x00\x00\x01\x00\x00\x00\x06'
    data, _ = patch_simple_tag(data, sig_origin, struct.pack('<f', 0.0))

    # 5. Patch Units (Array of USHORT=4) - Patch all
    sig_units = b'\x15\x00\x05Units\x25\x25\x25\x25\x00\x00\x00\x03\x00\x00\x00\x14\x00\x00\x00\x04'
    val_bytes = str(unit).encode('utf-16-le')
    arr_len = len(val_bytes) // 2
    
    # We must patch them manually one by one by reading the actual array lengths in template.dm3
    # Wait, patch_array_tag iterates correctly and calculates old_payload_size for each!
    data, diff = patch_array_tag(data, sig_units, 2, arr_len, val_bytes)
    total_diff += diff

    # 6. Patch Voltage & Magnification (DOUBLE=7) - Patch all
    sig_volt = b'\x15\x00\x07Voltage\x25\x25\x25\x25\x00\x00\x00\x01\x00\x00\x00\x07'
    data, _ = patch_simple_tag(data, sig_volt, struct.pack('<d', float(voltage)))
    
    sig_ind_mag = b'\x15\x00\x17Indicated Magnification\x25\x25\x25\x25\x00\x00\x00\x01\x00\x00\x00\x07'
    mag_val = 1.0
    if isinstance(magnification, (int, float)):
        mag_val = float(magnification)
    else:
        m = re.search(r'[\d\.]+', str(magnification))
        if m:
            mag_val = float(m.group(0))
            
    data, _ = patch_simple_tag(data, sig_ind_mag, struct.pack('<d', mag_val))
    
    sig_act_mag = b'\x15\x00\x14Actual Magnification\x25\x25\x25\x25\x00\x00\x00\x01\x00\x00\x00\x07'
    data, _ = patch_simple_tag(data, sig_act_mag, struct.pack('<d', mag_val))

    # 6b. Patch display contrast (LowLimit/HighLimit + EstimatedMin/Max) so GMS's initial
    # histogram/contrast window matches what the source TIFF showed in SightX Viewer, instead
    # of the template's stale leftover range (which belongs to whatever image the template was
    # captured from and has no relation to the real pixel data being patched in here).
    if contrast_low is not None and contrast_high is not None:
        sig_low = b'\x15\x00\x08LowLimit\x25\x25\x25\x25\x00\x00\x00\x01\x00\x00\x00\x06'
        data, _ = patch_simple_tag(data, sig_low, struct.pack('<f', contrast_low))
        sig_high = b'\x15\x00\x09HighLimit\x25\x25\x25\x25\x00\x00\x00\x01\x00\x00\x00\x06'
        data, _ = patch_simple_tag(data, sig_high, struct.pack('<f', contrast_high))
        sig_est_min = b'\x15\x00\x0cEstimatedMin\x25\x25\x25\x25\x00\x00\x00\x01\x00\x00\x00\x06'
        data, _ = patch_simple_tag(data, sig_est_min, struct.pack('<f', contrast_low))
        sig_est_max = b'\x15\x00\x0cEstimatedMax\x25\x25\x25\x25\x00\x00\x00\x01\x00\x00\x00\x06'
        data, _ = patch_simple_tag(data, sig_est_max, struct.pack('<f', contrast_high))
        # Caller (convert_jeol_to_dm.py) always passes disable_auto_survey=True whenever
        # contrast_low/contrast_high are set: GMS's own AutoSurvey, if left on, re-surveys
        # the raw pixel range at open time and — empirically, in real DigitalMicrograph —
        # frequently collapses LowLimit to equal HighLimit (a flat/blank-looking image) or
        # (for diffraction) reverts to the full 0-65535 sensor range, making spots invisible.
        # Disabling it makes the limits patched above the ones GMS actually displays, always.
        if disable_auto_survey:
            sig_auto_survey = b'\x15\x00\x0cDoAutoSurvey\x25\x25\x25\x25\x00\x00\x00\x01\x00\x00\x00\x08'
            data, _ = patch_simple_tag(data, sig_auto_survey, struct.pack('<b', 0))

    # 7. Patch Scale Bar Rectangle Position
    sig_rect = b'\x15\x00\x09Rectangle\x25\x25\x25\x25\x00\x00\x00\x0b\x00\x00\x00\x0f\x00\x00\x00\x00\x00\x00\x00\x04\x00\x00\x00\x00\x00\x00\x00\x06\x00\x00\x00\x00\x00\x00\x00\x06\x00\x00\x00\x00\x00\x00\x00\x06\x00\x00\x00\x00\x00\x00\x00\x06'
    new_bottom = height - 167.0
    new_top = height - 313.125
    new_left = 167.0
    new_right = 916.0
    rect_payload = struct.pack('<ffff', new_top, new_left, new_bottom, new_right)
    # The scale bar is the FIRST Rectangle in the document (match_index=0)
    data, _ = patch_simple_tag(data, sig_rect, rect_payload, match_index=0)

    # 8. Update Rootlen
    data = update_rootlen(data, total_diff)

    if disable_ast and output_format == 'dm3':
        with open(output_path, 'wb') as f:
            f.write(data)
        return data

    # 9. AST-based edits for Annotations and Metadata (also required to re-emit as DM4, since
    # the DM4 container format is rebuilt from this same tag tree - see dm3_editor.serialize_dm4).
    from dm3_editor import parse_dm3, inject_annotations, inject_metadata, find_group, DMData, serialize_dm3_file, serialize_dm4_file

    try:
        root, _ = parse_dm3(data)

        if not disable_ast:
            # Handle Scalebar visibility
            if not scalebar_enabled:
                # find AnnotationGroupList
                anno_list_grp = find_group(root, b"AnnotationGroupList")
                if anno_list_grp and len(anno_list_grp.tags) > 0:
                    # the first annotation is the default scale bar
                    scalebar_grp = anno_list_grp.tags[0]
                    # set IsVisible to 0
                    for child in scalebar_grp.tags:
                        if isinstance(child, DMData) and child.name_bytes == b"IsVisible":
                            child.payload = struct.pack('<b', 0)

            # Inject XML markers
            if markers_enabled and annotations_list:
                inject_annotations(root, annotations_list)

            # Inject XML metadata
            if metadata_enabled and metadata_dict:
                inject_metadata(root, metadata_dict)

        # Serialize back in the requested container format
        if output_format == 'dm4':
            data = serialize_dm4_file(root)
        else:
            data = serialize_dm3_file(root)

    except Exception as e:
        print(f"  [Warning] AST processing failed: {e}")
        import traceback
        traceback.print_exc()

    with open(output_path, 'wb') as f:
        f.write(data)
