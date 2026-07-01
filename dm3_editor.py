import struct
import sys

class DMData:
    def __init__(self, name_bytes, types, payload):
        self.name_bytes = name_bytes
        self.name = name_bytes.decode('ascii', errors='ignore') if name_bytes else ""
        self.types = types
        self.payload = payload

    def serialize(self):
        buf = bytearray()
        buf.append(21)
        buf.extend(struct.pack('>H', len(self.name_bytes)))
        buf.extend(self.name_bytes)
        buf.extend(b'%%%%')
        buf.extend(struct.pack('>I', len(self.types)))
        buf.extend(struct.pack('>' + 'I'*len(self.types), *self.types))
        buf.extend(self.payload)
        return buf

    def serialize_dm4(self):
        # DM4 widens every definition-array entry (the "types" ints) to 8 bytes, EXCEPT the
        # char-count of a native String tag (encodedType 18), which ncempy's reference reader
        # always reads as a hardcoded 4-byte field regardless of dm3/dm4 (verified against
        # ncempy.io.dm._readTagType; our templates/injections never emit type 18, so this path
        # is untested against a real file - kept for spec completeness).
        body = bytearray()
        body.extend(b'%%%%')
        body.extend(struct.pack('>Q', len(self.types)))
        if self.types[0] == 18 and len(self.types) == 2:
            body.extend(struct.pack('>Q', self.types[0]))
            body.extend(struct.pack('>I', self.types[1]))
        else:
            body.extend(struct.pack('>' + 'Q'*len(self.types), *self.types))
        body.extend(self.payload)

        buf = bytearray()
        buf.append(21)
        buf.extend(struct.pack('>H', len(self.name_bytes)))
        buf.extend(self.name_bytes)
        buf.extend(struct.pack('>Q', len(body)))
        buf.extend(body)
        return buf

class DMGroup:
    def __init__(self, name_bytes, sortf=0, closef=0):
        self.name_bytes = name_bytes
        self.name = name_bytes.decode('ascii', errors='ignore') if name_bytes else ""
        self.tags = []
        self.sortf = sortf
        self.closef = closef

    def serialize(self, is_root=False):
        buf = bytearray()
        if not is_root:
            buf.append(20)
            buf.extend(struct.pack('>H', len(self.name_bytes)))
            buf.extend(self.name_bytes)
        buf.append(self.sortf)
        buf.append(self.closef)
        buf.extend(struct.pack('>I', len(self.tags)))
        
        tags_to_write = self.tags
        # Removed automatic sorting to preserve original exact byte order for GMS compatibility
            
        for tag in tags_to_write:
            buf.extend(tag.serialize())
        return buf

    def serialize_dm4(self, is_root=False):
        body = bytearray()
        body.append(self.sortf)
        body.append(self.closef)
        body.extend(struct.pack('>Q', len(self.tags)))
        for tag in self.tags:
            body.extend(tag.serialize_dm4())

        if is_root:
            return body

        buf = bytearray()
        buf.append(20)
        buf.extend(struct.pack('>H', len(self.name_bytes)))
        buf.extend(self.name_bytes)
        buf.extend(struct.pack('>Q', len(body)))
        buf.extend(body)
        return buf

def parse_dm3(data):
    version, rootlen, byteord = struct.unpack('>III', data[:12])
    
    def get_size(types, idx=0):
        t0 = types[idx]
        sz_map = {2:2,3:4,4:2,5:4,6:4,7:8,8:1,9:1,10:1,11:8,12:8}
        if t0 in sz_map:
            return sz_map[t0]
        elif t0 == 18: # String
            return types[idx+1]
        elif t0 == 20: # Array
            t1 = types[idx+1]
            if t1 == 15: # Array of structs
                # types: 20, 15, name_len, num_fields, [name_len, field_type]...
                # wait, actually the array length is the LAST element!
                # For an array, the format is:
                # 20, <element_type_group> ..., arr_len
                # Let's find arr_len!
                # In DM3, types for Array is: 20, element_type_info, array_length
                # This is tricky without a recursive type reader.
                return 0 # we'll implement full later if needed
            else:
                arr_len = types[idx+2]
                return sz_map.get(t1, 1) * arr_len
        elif t0 == 15: # Struct
            name_len = types[idx+1]
            num_fields = types[idx+2]
            return sum(sz_map.get(types[idx+3 + i*2 + 1], 1) for i in range(num_fields))
        return 0

    def read_tag(offset, is_root=False):
        if is_root:
            name_bytes = b""
            sortf = data[offset]; closef = data[offset+1]; offset += 2
            ntags = struct.unpack('>I', data[offset:offset+4])[0]; offset += 4
            group = DMGroup(name_bytes, sortf, closef)
            for _ in range(ntags):
                child, offset = read_tag(offset)
                if child:
                    group.tags.append(child)
            return group, offset

        tag_id = data[offset]; offset += 1
        is_group = (tag_id == 20)
        is_data = (tag_id == 21)
        
        ltname = struct.unpack('>H', data[offset:offset+2])[0]; offset += 2
        name_bytes = data[offset:offset+ltname]
        offset += ltname
        if is_group:
            sortf = data[offset]; closef = data[offset+1]; offset += 2
            ntags = struct.unpack('>I', data[offset:offset+4])[0]; offset += 4
            group = DMGroup(name_bytes, sortf, closef)
            for _ in range(ntags):
                child, offset = read_tag(offset)
                if child:
                    group.tags.append(child)
            return group, offset
            
        elif is_data:
            offset += 4 # %%%%
            def_len = struct.unpack('>I', data[offset:offset+4])[0]; offset += 4
            types_bytes = data[offset:offset+4*def_len]
            types = struct.unpack('>'+'I'*def_len, types_bytes)
            offset += 4*def_len
            
            # recursive type reader to find size and array lengths
            def read_type(idx):
                t0 = types[idx]
                sz_map = {2:2,3:4,4:2,5:4,6:4,7:8,8:1,9:1,10:1,11:8,12:8}
                if t0 in sz_map:
                    return sz_map[t0], idx+1
                elif t0 == 18:
                    return types[idx+1], idx+2
                elif t0 == 15: # Struct
                    n_len = types[idx+1]
                    n_fields = types[idx+2]
                    sz = 0
                    curr_idx = idx+3
                    for _ in range(n_fields):
                        curr_idx += 1 # skip field name length
                        f_sz, curr_idx = read_type(curr_idx)
                        sz += f_sz
                    return sz, curr_idx
                elif t0 == 20: # Array
                    elem_sz, curr_idx = read_type(idx+1)
                    arr_len = types[curr_idx]
                    return elem_sz * arr_len, curr_idx+1
                else:
                    return 0, idx+1
                    
            size, _ = read_type(0)
            payload = data[offset:offset+size]
            offset += size
            return DMData(name_bytes, types, payload), offset

    root, final_offset = read_tag(12, is_root=True)
    print("Parsed up to offset:", final_offset)
    return root, final_offset

if __name__ == "__main__":
    import sys
    test_file = sys.argv[1] if len(sys.argv) > 1 else r"templates/template_image.dm3"
    with open(test_file, "rb") as f:
        data = f.read()

    root, _ = parse_dm3(data)
    
    new_data = root.serialize(is_root=True)
    new_data = struct.pack('>III', 3, len(new_data), 1) + new_data + (b'\x00' * 8)
    
    if data == new_data:
        print("Roundtrip successful! Bytes exactly match.")
    else:
        print("Roundtrip failed! Bytes differ.")
        
    pass

def serialize_dm3_file(root):
    payload = root.serialize(is_root=True)
    return struct.pack('>III', 3, len(payload), 1) + payload + (b'\x00' * 8)

def serialize_dm4_file(root):
    payload = root.serialize_dm4(is_root=True)
    header = struct.pack('>I', 4) + struct.pack('>Q', len(payload)) + struct.pack('>I', 1)
    return header + payload + (b'\x00' * 8)

def create_scalar(name, t0, fmt, val):
    payload = struct.pack(fmt, val)
    return DMData(name.encode('ascii') if name else b"", (t0,), payload)

def create_string(name, val):
    val_bytes = val.encode('utf-16le') # DM3 usually stores string tags as utf-16le
    # Wait, some are utf-16le, some are ascii? Let's stick to utf-16le if the type requires it. 
    # Actually, GMS usually uses utf-16le for strings (type 20 with type 2? no, type 20 with type 4).
    # Let's check what type text usually is. It might be an array of USHORTs!
    pass

def create_annotation_group(anno_type, rect_tuple, text=None, text_color=None, bg_color=None, font_size=14, filled=False):
    grp = DMGroup(b"", sortf=1)
    grp.tags.append(create_scalar("AnnotationType", 3, '<i', anno_type))

    # BackgroundColor: 15, 0, 3, 0, 2, 0, 2, 0, 2 -> 3 SHORTs
    bg = bg_color or (255, 255, 255) # white
    bg_payload = struct.pack('<HHH', int(bg[0]*257), int(bg[1]*257), int(bg[2]*257))
    grp.tags.append(DMData(b"BackgroundColor", (15, 0, 3, 0, 2, 0, 2, 0, 2), bg_payload))

    # Verified empirically against real GMS 3.63: BackgroundMode=FillMode=1 renders as a SOLID
    # FILL (not "transparent" as the field names suggest). Outline-only needs BackgroundMode=0/
    # FillMode=0/HasBackground=0; opaque fill needs HasBackground=1/BackgroundMode=2/FillMode=2
    # (matches the native scale-bar annotation in templates/template_*.dm3).
    if filled:
        has_background, bmode = 1, 2
    else:
        has_background, bmode = 0, 0
    grp.tags.append(create_scalar("BackgroundMode", 2, '<h', bmode))
    grp.tags.append(create_scalar("FillMode", 2, '<h', bmode))

    # ForegroundColor
    fg = text_color or (0, 0, 0)
    fg_payload = struct.pack('<HHH', int(fg[0]*257), int(fg[1]*257), int(fg[2]*257))
    grp.tags.append(DMData(b"ForegroundColor", (15, 0, 3, 0, 2, 0, 2, 0, 2), fg_payload))

    grp.tags.append(create_scalar("HasBackground", 8, '<b', has_background))
    grp.tags.append(create_scalar("IsMoveable", 8, '<b', 1))
    grp.tags.append(create_scalar("IsResizable", 8, '<b', 1))
    grp.tags.append(create_scalar("IsSelectable", 8, '<b', 1))
    grp.tags.append(create_scalar("IsTransferrable", 8, '<b', 1))
    grp.tags.append(create_scalar("IsTranslatable", 8, '<b', 1))
    grp.tags.append(create_scalar("IsVisible", 8, '<b', 1))
    
    # Rectangle: Top, Left, Bottom, Right
    rect_payload = struct.pack('<ffff', rect_tuple[0], rect_tuple[1], rect_tuple[2], rect_tuple[3])
    grp.tags.append(DMData(b"Rectangle", (15, 0, 4, 0, 6, 0, 6, 0, 6, 0, 6), rect_payload))
    
    if text:
        # String is usually Array of USHORT (20, 4, len)
        text_arr = [ord(c) for c in text]
        text_payload = struct.pack('<' + 'H'*len(text_arr), *text_arr)
        grp.tags.append(DMData(b"Text", (20, 4, len(text_arr)), text_payload))
        # ResizeStyle: 2 = Size to text (keeps font size constant and adapts box size)
        grp.tags.append(create_scalar("ResizeStyle", 5, '<I', 2))
        
    # Font Group
    font_grp = DMGroup(b"Font", sortf=1)
    font_grp.tags.append(create_scalar("Attributes", 5, '<I', 0))
    fname = "Arial"
    fname_arr = [ord(c) for c in fname]
    font_grp.tags.append(DMData(b"FamilyName", (20, 4, len(fname_arr)), struct.pack('<' + 'H'*len(fname_arr), *fname_arr)))
    font_grp.tags.append(create_scalar("Size", 5, '<I', font_size))
    grp.tags.append(font_grp)
    
    # ObjectTags (Empty Group)
    grp.tags.append(DMGroup(b"ObjectTags", sortf=1))
    
    import random
    grp.tags.append(create_scalar("UniqueID", 5, '<I', random.randint(1000000, 9999999)))
        
    grp.tags = sorted(grp.tags, key=lambda t: t.name_bytes.decode('ascii', 'ignore').lower())
    return grp

def find_group(node, target_name):
    if isinstance(node, DMGroup):
        if node.name == target_name or node.name_bytes == target_name:
            return node
        for child in node.tags:
            res = find_group(child, target_name)
            if res: return res
    return None

def inject_annotations(root, annotations_list):
    anno_list_grp = find_group(root, b"AnnotationGroupList")
    if anno_list_grp:
        for anno in annotations_list:
            anno_list_grp.tags.append(anno)
            
def inject_metadata(root, metadata_dict):
    info_grp = find_group(root, b"Microscope Info")
    if not info_grp:
        return
    for k, v in metadata_dict.items():
        # Remove existing tag with same name to avoid duplicates
        k_bytes = k.encode('ascii')
        for i in range(len(info_grp.tags)-1, -1, -1):
            t = info_grp.tags[i]
            if (isinstance(t, DMData) or isinstance(t, DMGroup)) and getattr(t, 'name_bytes', b'') == k_bytes:
                del info_grp.tags[i]
                
        if isinstance(v, float):
            info_grp.tags.append(create_scalar(k, 6, '<f', v))
        elif isinstance(v, str):
            text_arr = [ord(c) for c in v]
            text_payload = struct.pack('<' + 'H'*len(text_arr), *text_arr)
            info_grp.tags.append(DMData(k_bytes, (20, 4, len(text_arr)), text_payload))
            
    # GMS requires sortf=1 groups to be sorted alphabetically (case-insensitive)
    info_grp.tags = sorted(info_grp.tags, key=lambda t: t.name_bytes.decode('ascii', 'ignore').lower())
            


