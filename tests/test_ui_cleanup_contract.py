from pathlib import Path
import unittest


class UiCleanupContractTest(unittest.TestCase):
    def test_main_ui_has_clean_alert_rows_and_stacked_land_vspeed(self):
        html = Path("index.html").read_text(encoding="utf-8")
        required = [
            "UI_CLEANUP_V1",
            "PERF_DIAGNOSTIC_PREFIXES",
            "🚀 VFR_HUD raw:",
            "⚡ EFI_STATUS індекс:",
            "🔬 MAVLink профіль:",
            "⏱ Швидкість аналізу backend:",
            "function tidyAiAlertRows",
            "ai-alert-hidden-debug",
            "ai-alert-row",
            "ai-alert-needs-attention",
            ".tl-altitude-cell{display:flex!important;flex-direction:column!important;align-items:flex-start!important;justify-content:center!important;gap:2px!important",
            ".land-vspeed-inline{display:block",
        ]
        for marker in required:
            self.assertIn(marker, html, marker)

        self.assertIn("observer.observe(aiAlerts", html)
        self.assertIn("display:none!important", html)


if __name__ == "__main__":
    unittest.main()
