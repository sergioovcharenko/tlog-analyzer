import struct
import unittest

from backend.raw_vfr import decode_vfr_hud_payload


class VfrRawFastPathTest(unittest.TestCase):
    def test_decodes_vfr_hud_wire_payload(self):
        payload = struct.pack('<ffffhH', 12.5, 18.25, 123.75, -2.5, 271, 67)
        row = decode_vfr_hud_payload(payload)
        self.assertAlmostEqual(row['airspeed'], 12.5, places=4)
        self.assertAlmostEqual(row['groundspeed'], 18.25, places=4)
        self.assertAlmostEqual(row['alt'], 123.75, places=4)
        self.assertAlmostEqual(row['climb'], -2.5, places=4)
        self.assertEqual(row['heading'], 271)
        self.assertEqual(row['throttle'], 67)

    def test_zero_truncated_v2_payload_is_padded(self):
        full = struct.pack('<ffffhH', 1.0, 2.0, 3.0, 4.0, 0, 0)
        row = decode_vfr_hud_payload(full.rstrip(b'\x00'))
        self.assertEqual(row['heading'], 0)
        self.assertEqual(row['throttle'], 0)


if __name__ == '__main__':
    unittest.main()
