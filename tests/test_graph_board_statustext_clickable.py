from pathlib import Path
import unittest

from backend.mavlink_plot import build_board_messages

ROOT = Path(__file__).resolve().parents[1]
INDEX = (ROOT / "index.html").read_text(encoding="utf-8")


class GraphBoardStatustextClickableTest(unittest.TestCase):
    def test_known_ardupilot_problem_text_is_not_left_as_plain_info(self):
        rows = [
            {"timestamp": 101.0, "eventType": "SYSTEM", "system_text": "EKF variance", "severity": 6},
            {"timestamp": 102.0, "eventType": "SYSTEM", "system_text": "PreArm: Need Position Estimate", "severity": 6},
            {"timestamp": 103.0, "eventType": "SYSTEM", "system_text": "SmartRTL deactivated: bad position", "severity": 6},
        ]
        msgs = build_board_messages(rows, 100.0)
        self.assertEqual([m["text"] for m in msgs], [
            "EKF variance",
            "PreArm: Need Position Estimate",
            "SmartRTL deactivated: bad position",
        ])
        self.assertTrue(all(m["level"] in {"warning", "error"} for m in msgs))

    def test_board_messages_are_clickable_and_jump_graph_to_exact_event_time(self):
        self.assertIn('data-board-time="${Number(m.time_ms)}"', INDEX)
        self.assertIn("root.querySelectorAll('[data-board-time]').forEach", INDEX)
        self.assertIn("selectGraphTime(Number(el.dataset.boardTime))", INDEX)

    def test_board_message_styles_distinguish_problem_levels(self):
        self.assertIn('.board-message-warning', INDEX)
        self.assertIn('.board-message-error', INDEX)
        self.assertIn('.board-message[data-board-time]{cursor:pointer', INDEX)


if __name__ == "__main__":
    unittest.main()
