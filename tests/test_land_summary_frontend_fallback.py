from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
INDEX = (ROOT / "index.html").read_text(encoding="utf-8")


class LandSummaryFrontendFallbackTest(unittest.TestCase):
    def test_frontend_builds_land_transition_alert_from_timeline(self):
        self.assertIn("function buildLandTransitionAlerts(timeline)", INDEX)
        self.assertIn("if(mode==='LAND'&&prevMode&&prevMode!=='LAND')", INDEX)
        self.assertIn("🛬 <b>Перехід у LAND:</b>", INDEX)
        self.assertIn("data-jump-time=", INDEX)

    def test_land_alerts_are_included_in_combined_ai_alerts(self):
        self.assertIn("const landTransitionAlerts=buildLandTransitionAlerts(data.timeline);", INDEX)
        self.assertIn("...landTransitionAlerts,", INDEX)


if __name__ == '__main__':
    unittest.main()
