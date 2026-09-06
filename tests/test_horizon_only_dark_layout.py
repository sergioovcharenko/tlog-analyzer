from pathlib import Path
import unittest

HTML = Path('index.html').read_text(encoding='utf-8')


class HorizonOnlyDarkLayoutContract(unittest.TestCase):
    def test_dark_theme_is_the_only_visible_theme(self):
        self.assertIn('HORIZON_ONLY_DARK_V1', HTML)
        self.assertIn("localStorage.setItem('tlog-theme','dark')", HTML)
        self.assertIn('.tlog-theme-switch{display:none!important}', HTML)
        self.assertNotIn('○ Світла</button>', HTML)

    def test_summary_and_messages_are_moved_under_horizon(self):
        self.assertIn('function applyHorizonOnlyDarkLayout()', HTML)
        self.assertIn("attitudePanel.appendChild(summary)", HTML)
        self.assertIn("attitudePanel.appendChild(messages)", HTML)
        self.assertIn('.graph-dashboard-summary.in-attitude{', HTML)
        self.assertIn('display:grid!important', HTML)

    def test_right_dock_keeps_horizon_plus_requested_radio_cards(self):
        self.assertIn('.graph-dock-tabs{display:none!important}', HTML)
        self.assertIn('.graph-dock-panel:not([data-dock-panel="attitude"]){display:none!important}', HTML)
        self.assertIn('.graph-dashboard-dock .attitude-radio-row{display:grid!important', HTML)
        self.assertIn('.graph-dashboard-dock #attitudeValues{display:none!important}', HTML)
        self.assertIn('attitudeRssi', HTML)
        self.assertIn('attitudeDbm', HTML)

    def test_summary_status_coloring_uses_requested_thresholds(self):
        self.assertIn("attitudeBatClass(n)", HTML)
        self.assertIn("attitudeFcTempClass(n)", HTML)
        self.assertIn("n>=80?'summary-danger'", HTML)
        self.assertIn("k==='ENGINE LOAD'", HTML)
        self.assertIn('.graph-summary-item.summary-success strong', HTML)
        self.assertIn('.graph-summary-item.summary-warning strong', HTML)
        self.assertIn('.graph-summary-item.summary-danger strong', HTML)


if __name__ == '__main__':
    unittest.main()
