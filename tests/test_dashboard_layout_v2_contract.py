from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
HTML = (ROOT / "index.html").read_text(encoding="utf-8")


class DashboardLayoutV2Contract(unittest.TestCase):
    def test_layout_wrappers_exist(self):
        self.assertTrue(
            'id="graphDashboardV2"' in HTML or "root.id='graphDashboardV2'" in HTML,
            "dashboard root must exist statically or be created by the layout initializer",
        )
        for marker in (
            'class="graph-dashboard-summary"',
            'class="graph-dashboard-workspace"',
            'class="graph-dashboard-main"',
            'class="graph-dashboard-dock"',
            'id="mavlinkSelectorShell"',
        ):
            self.assertIn(marker, HTML)
        for label in ("ЧАС", "РЕЖИМ", "ВИСОТА", "ДАЛЬНІСТЬ", "АЗИМУТ", "НАПРУГА", "СТРУМ", "RSSI", "dBm"):
            self.assertIn(label, HTML)

    def test_right_dock_tabs_exist(self):
        for tab in ("Авіагоризонт", "Повідомлення", "TX16", "Дані"):
            self.assertIn(f">{tab}<", HTML)
        self.assertIn("setGraphDockTab", HTML)
        self.assertIn('data-dock-panel="attitude"', HTML)
        self.assertIn('data-dock-panel="messages"', HTML)
        self.assertIn('data-dock-panel="tx16"', HTML)
        self.assertIn('data-dock-panel="data"', HTML)

    def test_theme_control_is_exact_and_persistent(self):
        self.assertIn("● Темна", HTML)
        self.assertIn("○ Світла", HTML)
        self.assertIn("localStorage.getItem('tlog-theme')", HTML)
        self.assertIn("localStorage.setItem('tlog-theme'", HTML)
        self.assertIn("data-tlog-theme", HTML)
        self.assertIn("--graph-bg", HTML)
        self.assertIn("--graph-grid", HTML)
        self.assertIn("--input-bg", HTML)
        self.assertIn('[data-tlog-theme="light"]', HTML)

    def test_light_theme_polishes_hardcoded_dark_sections(self):
        self.assertIn("/* LIGHT_THEME_POLISH_V1 */", HTML)
        for selector in (
            '[data-tlog-theme="light"] .timeline',
            '[data-tlog-theme="light"] .tl-header',
            '[data-tlog-theme="light"] .repeat-alert-group',
            '[data-tlog-theme="light"] .esc-detail',
            '[data-tlog-theme="light"] .board-message',
            '[data-tlog-theme="light"] .graph-viewer-chart-wrap',
        ):
            self.assertIn(selector, HTML)
        self.assertIn("--light-page:#eef3f8", HTML)
        self.assertIn("--light-panel:#ffffff", HTML)
        self.assertIn("--light-text:#172033", HTML)

    def test_theme_switch_is_visible_on_upload_page(self):
        header = re.search(r'<div class="header">(.*?)</div>\s*\n\s*<div class="container">', HTML, re.S)
        self.assertIsNotNone(header)
        self.assertIn('id="globalThemeSwitch"', header.group(1))
        self.assertIn('data-theme-choice="dark"', header.group(1))
        self.assertIn('data-theme-choice="light"', header.group(1))

    def test_mavlink_selector_is_collapsible_with_presets(self):
        self.assertIn('id="mavlinkSelectorToggle"', HTML)
        for preset in ("Altitude", "Power", "Radio", "Attitude", "ESC"):
            self.assertIn(f">{preset}<", HTML)
        self.assertIn("setMavlinkSelectorCollapsed", HTML)
        self.assertIn('id="graphSelectedSeriesChips"', HTML)

    def test_responsive_breakpoints_exist(self):
        self.assertRegex(HTML, r"@media\s*\(max-width:\s*1199px\)")
        self.assertRegex(HTML, r"@media\s*\(max-width:\s*767px\)")
        self.assertIn("overflow-x:hidden", HTML.replace(" ", ""))
        self.assertIn('data-mobile-view="overview"', HTML)
        self.assertIn('data-mobile-view="graph"', HTML)
        self.assertIn('data-mobile-view="attitude"', HTML)
        self.assertIn('data-mobile-view="messages"', HTML)

    def test_current_horizon_hooks_are_not_replaced(self):
        for marker in (
            "attitudeHorizon",
            "attitudeScene",
            "attitudeRollPointer",
            "attitudeValues",
            "attitudeFlightMode",
            "updateAttitudeAtTime",
        ):
            self.assertIn(marker, HTML)

    def test_existing_graph_and_message_hooks_stay_present(self):
        for marker in (
            "graphCanvas",
            "graphMetricSelect",
            "mavlinkPlotPanel",
            "mavlinkPlotGroups",
            "boardMessagesPanel",
            "boardMessagesList",
            "renderBoardMessagesAtTime",
        ):
            self.assertIn(marker, HTML)

    def test_tab_and_theme_switches_are_frontend_only(self):
        tab_body = re.search(r"function setGraphDockTab\([^)]*\)\{.*?\n\}", HTML, re.S)
        self.assertIsNotNone(tab_body)
        self.assertNotIn("fetch(", tab_body.group(0))
        theme_body = re.search(r"function setTlogTheme\([^)]*\)\{.*?\n\}", HTML, re.S)
        self.assertIsNotNone(theme_body)
        self.assertNotIn("fetch(", theme_body.group(0))

    def test_patcher_marker_present_after_generation(self):
        self.assertIn("/* DASHBOARD_LAYOUT_V2 */", HTML)


if __name__ == "__main__":
    unittest.main()
