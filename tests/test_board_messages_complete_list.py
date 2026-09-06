from pathlib import Path
import unittest

from backend.mavlink_plot import build_board_messages

ROOT = Path(__file__).resolve().parents[1]
INDEX = (ROOT / "index.html").read_text(encoding="utf-8")


class BoardMessagesCompleteListTest(unittest.TestCase):
    def test_build_board_messages_accepts_direct_statustext_rows(self):
        rows = [
            {
                "timestamp": 100.25,
                "text": "Potential Thrust Loss (1)",
                "severity": 3,
                "eventType": "POTENTIAL_THRUST_LOSS",
            },
            {
                "timestamp": 101.5,
                "text": "EKF variance",
                "severity": 4,
                "eventType": "SYSTEM",
            },
        ]
        out = build_board_messages(rows, 100.0)
        self.assertEqual([m["text"] for m in out], ["Potential Thrust Loss (1)", "EKF variance"])
        self.assertEqual(out[0]["time_ms"], 250)
        self.assertEqual(out[0]["level"], "error")

    def test_graph_refreshes_board_messages_at_selected_time(self):
        self.assertIn(
            "renderGraphDockTx16(timeMs);renderGraphDockData(timeMs);renderBoardMessagesAtTime(timeMs);renderSelectedSeriesChips();",
            INDEX,
        )

    def test_board_list_has_useful_scrollable_height(self):
        self.assertIn("BOARD_MESSAGES_COMPLETE_LIST_V1", INDEX)
        self.assertIn("min-height:180px!important", INDEX)
        self.assertIn("max-height:280px!important", INDEX)


if __name__ == "__main__":
    unittest.main()
