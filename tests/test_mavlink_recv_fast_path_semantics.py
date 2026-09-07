import unittest


class MavlinkFastPathSemanticsTest(unittest.TestCase):
    def test_needed_types_filter_is_set_based(self):
        needed_messages = {"HEARTBEAT", "ATTITUDE", "STATUSTEXT"}
        stream = ["HEARTBEAT", "GPS_RAW_INT", "ATTITUDE", "NAMED_VALUE_FLOAT", "STATUSTEXT"]
        processed = [msg_type for msg_type in stream if msg_type in needed_messages]
        self.assertEqual(processed, ["HEARTBEAT", "ATTITUDE", "STATUSTEXT"])


if __name__ == "__main__":
    unittest.main()
