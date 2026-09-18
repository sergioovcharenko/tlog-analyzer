import struct

from pymavlink import mavutil


def _timestamp_at(data_map, offset):
    if offset < 0 or offset + 8 > len(data_map):
        return None
    try:
        (tusec,) = struct.unpack(">Q", data_map[offset:offset + 8])
    except (struct.error, TypeError):
        return None
    return tusec * 1.0e-6


def select_last_offsets_per_bucket(data_map, offsets, interval_s=0.2):
    """Return the last TLOG offset seen in each fixed time bucket."""
    if not offsets or interval_s <= 0:
        return []

    selected = []
    current_bucket = None
    pending_offset = None

    for offset in offsets:
        ts = _timestamp_at(data_map, int(offset))
        if ts is None:
            continue

        bucket = int(ts / float(interval_s))
        if current_bucket is None:
            current_bucket = bucket
            pending_offset = int(offset)
            continue

        if bucket == current_bucket:
            pending_offset = int(offset)
            continue

        if pending_offset is not None:
            selected.append(pending_offset)
        current_bucket = bucket
        pending_offset = int(offset)

    if pending_offset is not None:
        selected.append(pending_offset)

    return selected


def build_indexed_numeric_series(filename, message_name, value_attr, interval_s=0.2):
    """Build a sampled numeric time series from pymavlink's mmap TLOG index.

    Returns None when mmap indexing is unavailable so callers can fall back to
    their existing full recv_match path.
    """
    reader = None
    try:
        reader = mavutil.mavlink_connection(filename)

        if not all(hasattr(reader, attr) for attr in ("offsets", "name_to_id", "data_map")):
            return None
        if reader.data_map is None:
            return None

        msg_id = reader.name_to_id.get(message_name)
        if msg_id is None:
            return {
                "samples": [],
                "input_count": 0,
                "decoded_count": 0,
            }

        raw_offsets = list(reader.offsets.get(msg_id, []))
        selected_offsets = select_last_offsets_per_bucket(
            reader.data_map,
            raw_offsets,
            interval_s=interval_s,
        )

        samples = []
        decoded_count = 0
        for offset in selected_offsets:
            reader.offset = int(offset)
            reader.f.seek(int(offset))
            msg = reader.recv_msg()
            if msg is None or msg.get_type() != message_name:
                continue
            value = getattr(msg, value_attr, None)
            timestamp = getattr(msg, "_timestamp", None)
            try:
                value = float(value)
                timestamp = float(timestamp)
            except (TypeError, ValueError):
                continue
            samples.append((timestamp, value))
            decoded_count += 1

        return {
            "samples": samples,
            "input_count": len(raw_offsets),
            "decoded_count": decoded_count,
        }
    except Exception:
        return None
    finally:
        if reader is not None:
            try:
                reader.close()
            except Exception:
                pass
