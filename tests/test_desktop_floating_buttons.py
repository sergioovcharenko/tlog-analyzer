from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
INDEX = (ROOT / "index.html").read_text(encoding="utf-8")


class DesktopFloatingButtonsTest(unittest.TestCase):
    def test_graph_and_scroll_top_buttons_have_separate_desktop_positions(self):
        self.assertIn("DESKTOP_FLOATING_BUTTONS_V1", INDEX)
        self.assertIn("#graphViewerBtn{right:22px!important;bottom:22px!important}", INDEX)
        self.assertIn("#scrollTopBtn{right:22px!important;bottom:82px!important}", INDEX)


if __name__ == "__main__":
    unittest.main()
