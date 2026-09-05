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

    def test_right_dock_is_horizon_only(self):
        self.assertIn('data-dock-panel="attitude"', HTML)
        self.assertIn('.graph-dock-tabs{display:none!important}', HTML)
        self.assertIn('.graph-dock-panel:not([data-dock-panel="attitude"]){display:none!important}', HTML)
        self.assertIn('applyHorizonOnlyDarkLayout', HTML)

    def test_dark_theme_is_single_visible_theme(self):
        self.assertIn("localStorage.setItem('tlog-theme','dark')", HTML)
        self.assertIn('.tlog-theme-switch{display:none!important}', HTML)
        self.assertNotIn('○ Світла</button>', HTML)
        self.assertIn("--graph-bg", HTML)
        self.assertIn("--graph-grid", HTML)

    def test_summary_is_reused_below_horizon(self):
        self.assertIn("attitudePanel.appendChild(summary)", HTML)
        self.assertIn('.graph-dashboard-summary.in-attitude{display:grid!important}', HTML)

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

    def test_patcher_marker_present_after_generation(self):
        self.assertIn("/* DASHBOARD_LAYOUT_V2 */", HTML)
        self.assertIn("/* HORIZON_ONLY_DARK_V1 */", HTML)


if __name__ == "__main__":
    unittest.main()
