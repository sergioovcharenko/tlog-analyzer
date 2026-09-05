from pathlib import Path
import unittest

HTML = Path('index.html').read_text(encoding='utf-8')


class HorizonOnlyDarkLayoutContract(unittest.TestCase):
    def test_dark_theme_is_the_only_visible_theme(self):
        self.assertIn('HORIZON_ONLY_DARK_V1', HTML)
        self.assertIn("localStorage.setItem('tlog-theme','dark')", HTML)
        self.assertIn('.tlog-theme-switch{display:none!important}', HTML)
        self.assertNotIn('○ Світла</button>', HTML)

    def test_top_summary_is_moved_under_horizon(self):
        self.assertIn('id="attitudeTelemetryGrid"', HTML)
        self.assertIn('function applyHorizonOnlyDarkLayout()', HTML)
        self.assertIn("summary.children.length", HTML)
        self.assertIn("grid.appendChild(summary.firstElementChild)", HTML)
        self.assertIn('.graph-dashboard-summary{display:none!important}', HTML)

    def test_right_dock_is_horizon_only(self):
        self.assertIn('.graph-dock-tabs{display:none!important}', HTML)
        self.assertIn('.graph-dock-panel:not([data-dock-panel="attitude"]){display:none!important}', HTML)
        for label in ('>Повідомлення<','>TX16<','>Дані<'):
            self.assertNotIn(label, HTML)

    def test_moved_cards_keep_existing_status_classes(self):
        self.assertIn('attitude-telemetry-grid', HTML)
        self.assertIn('graph-summary-item', HTML)
        self.assertIn('color:inherit', HTML)


if __name__ == '__main__':
    unittest.main()
