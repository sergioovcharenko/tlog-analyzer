from pathlib import Path
import unittest


class MavlinkInnerProfileContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = Path("backend/main.py").read_text(encoding="utf-8")

    def test_exposes_recv_match_time(self):
        self.assertIn('"recv_match_ms"', self.text)

    def test_exposes_message_type_profile(self):
        self.assertIn('"mavlink_profile"', self.text)
        self.assertIn('_perf_msg_type_ms', self.text)
        self.assertIn('_perf_msg_type_count', self.text)

    def test_ai_shows_inner_profile(self):
        self.assertIn('MAVLink профіль', self.text)


if __name__ == "__main__":
    unittest.main()
