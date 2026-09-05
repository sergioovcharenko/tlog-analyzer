from pathlib import Path
import unittest

HTML = Path('index.html').read_text(encoding='utf-8')


class GraphHorizonLayoutLightThemeContract(unittest.TestCase):
    def test_summary_cards_are_moved_into_horizon_panel(self):
        self.assertIn('id="attitudeTelemetryGrid"', HTML)
        for metric in ('ЧАС','РЕЖИМ','ВИСОТА','ДАЛЬНІСТЬ','АЗИМУТ','НАПРУГА','СТРУМ','RSSI','DBM','TEMP'):
            self.assertIn(f'data-attitude-metric="{metric}"', HTML)
        self.assertNotIn('class="graph-dashboard-summary"', HTML)

    def test_right_panel_is_horizon_only(self):
        for label in ('>Повідомлення<','>TX16<','>Дані<'):
            self.assertNotIn(label, HTML)
        self.assertNotIn('class="graph-dashboard-tabs"', HTML)

    def test_light_theme_has_overrides_for_problem_areas(self):
        for marker in (
            '[data-tlog-theme="light"] .timeline',
            '[data-tlog-theme="light"] .tl-header',
            '[data-tlog-theme="light"] .tl-item',
            '[data-tlog-theme="light"] #mapTelemetryPanel',
            '[data-tlog-theme="light"] .graph-dashboard-main',
            '[data-tlog-theme="light"] .attitude-telemetry-card',
        ):
            self.assertIn(marker, HTML)


if __name__ == '__main__':
    unittest.main()
