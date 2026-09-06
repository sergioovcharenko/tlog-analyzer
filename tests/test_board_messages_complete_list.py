from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
INDEX = (ROOT / "index.html").read_text(encoding="utf-8")


class BoardMessagesCompleteListTest(unittest.TestCase):
    def test_dashboard_event_stream_includes_initial_mode_and_timeline_board_events(self):
        self.assertIn("Початковий режим:", INDEX)
        self.assertIn("const timeline=Array.isArray(result.timeline)?result.timeline:[];", INDEX)
        self.assertIn("row?.systemText", INDEX)
        self.assertIn("['ARM','DISARM'].includes(eventType)", INDEX)

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
