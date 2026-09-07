from pathlib import Path
import unittest


class MavlinkRecvFastPathContractTest(unittest.TestCase):
    def test_analyzer_uses_direct_recv_msg_and_set_filter(self):
        text = Path("backend/main.py").read_text(encoding="utf-8")

        self.assertIn("MAVLINK_RECV_FAST_PATH_V1", text)
        self.assertIn("needed_messages = {", text)
        self.assertIn("msg = mav.recv_msg()", text)
        self.assertIn("if msg_type not in needed_messages:", text)
        self.assertNotIn("mav.recv_match(type=needed_messages", text)


if __name__ == "__main__":
    unittest.main()
