import struct


VFR_HUD_MSG_ID = 74
VFR_HUD_PAYLOAD_LEN = 20


def decode_vfr_hud_payload(payload):
    """Decode the fixed VFR_HUD wire payload without creating a pymavlink message object."""
    raw = bytes(payload or b"")
    if len(raw) > VFR_HUD_PAYLOAD_LEN:
        raw = raw[:VFR_HUD_PAYLOAD_LEN]
    if len(raw) < VFR_HUD_PAYLOAD_LEN:
        raw = raw + bytes(VFR_HUD_PAYLOAD_LEN - len(raw))
    airspeed, groundspeed, alt, climb, heading, throttle = struct.unpack("<ffffhH", raw)
    return {
        "airspeed": float(airspeed),
        "groundspeed": float(groundspeed),
        "alt": float(alt),
        "climb": float(climb),
        "heading": int(heading),
        "throttle": int(throttle),
    }


def _raw_payload_at(data_map, offset, expected_msg_id):
    offset = int(offset)
    if offset < 0 or offset + 18 > len(data_map):
        return None

    marker = data_map[offset + 8]
    if not isinstance(marker, int):
        marker = ord(marker)
    payload_len = data_map[offset + 9]
    if not isinstance(payload_len, int):
        payload_len = ord(payload_len)

    if marker == 0xFE:
        msg_id = data_map[offset + 13]
        if not isinstance(msg_id, int):
            msg_id = ord(msg_id)
        payload_start = offset + 14
    elif marker == 0xFD:
        b0 = data_map[offset + 15]
        b1 = data_map[offset + 16]
        b2 = data_map[offset + 17]
        if not isinstance(b0, int):
            b0 = ord(b0)
            b1 = ord(b1)
            b2 = ord(b2)
        msg_id = b0 | (b1 << 8) | (b2 << 16)
        payload_start = offset + 18
    else:
        return None

    if msg_id != int(expected_msg_id):
        return None
    payload_end = payload_start + int(payload_len)
    if payload_end > len(data_map):
        return None
    return bytes(data_map[payload_start:payload_end])


def build_raw_vfr_hud_series_from_reader(reader):
    """Return every VFR_HUD sample from an already-indexed pymavlink mmap reader."""
    if not all(hasattr(reader, attr) for attr in ("offsets", "name_to_id", "data_map")):
        return None
    if reader.data_map is None:
        return None

    msg_id = reader.name_to_id.get("VFR_HUD")
    if msg_id is None:
        return {"samples": [], "input_count": 0, "decoded_count": 0}

    samples = []
    offsets = list(reader.offsets.get(msg_id, []))
    for offset in offsets:
        try:
            (tusec,) = struct.unpack(">Q", reader.data_map[int(offset):int(offset) + 8])
            payload = _raw_payload_at(reader.data_map, offset, msg_id)
            if payload is None:
                continue
            row = decode_vfr_hud_payload(payload)
            row["timestamp"] = tusec * 1.0e-6
            samples.append(row)
        except (struct.error, TypeError, ValueError, IndexError):
            continue

    return {
        "samples": samples,
        "input_count": len(offsets),
        "decoded_count": len(samples),
    }
