import struct
import unittest

from backend.indexed_tlog import select_last_offsets_per_bucket


class IndexedTlogSelectorTest(unittest.TestCase):
    def test_selects_last_offset_in_each_200ms_bucket(self):
        timestamps = [100.01, 100.05, 100.19, 100.21, 100.39, 100.41]
        offsets = []
        raw = bytearray()

        for ts in timestamps:
            offsets.append(len(raw))
            raw.extend(struct.pack(">Q", int(round(ts * 1_000_000))))
            raw.extend(b"X")

        selected = select_last_offsets_per_bucket(raw, offsets, interval_s=0.2)

        self.assertEqual(selected, [offsets[2], offsets[4], offsets[5]])

    def test_empty_offsets_returns_empty_list(self):
        self.assertEqual(select_last_offsets_per_bucket(b"", [], interval_s=0.2), [])


if __name__ == "__main__":
    unittest.main()
