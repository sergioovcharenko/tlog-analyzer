from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
INDEX = (ROOT / "index.html").read_text(encoding="utf-8")
BACKEND = (ROOT / "backend" / "main.py").read_text(encoding="utf-8")


class GraphInfoPanelV2Contract(unittest.TestCase):
    def test_backend_exposes_ground_speed_and_total_distance_series(self):
        self.assertIn('"ground_speed_time_ms"', BACKEND)
        self.assertIn('"ground_speed_ms"', BACKEND)
        self.assertIn('"total_distance_time_ms"', BACKEND)
        self.assertIn('"total_distance_m"', BACKEND)

    def test_dashboard_uses_requested_information_cards(self):
        for label in (
            "ПОЛІТНИЙ РЕЖИМ",
            "RSSI",
            "dBm",
            "ВИСОТА",
            "ЧАС",
            "НАПРУГА",
            "ДИСТАНЦІЯ ДО HOME",
            "ТЕМПЕРАТУРА FC",
            "СТРУМ",
            "GROUND SPEED",
            "ЗАГАЛЬНА ДИСТАНЦІЯ",
            "ENGINE LOAD",
        ):
            self.assertIn(label, INDEX)

    def test_current_warning_is_red_at_80_amps_or_more(self):
        self.assertIn("n>=80?'summary-danger'", INDEX)

    def test_board_panel_merges_mode_changes_with_board_messages(self):
        self.assertIn("function dashboardBoardEvents", INDEX)
        self.assertIn("Режим змінено на", INDEX)
        self.assertIn("board_messages", INDEX)


if __name__ == "__main__":
    unittest.main()
