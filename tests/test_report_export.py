from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "index.html"


class ReportExportContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html = INDEX.read_text(encoding="utf-8")

    def test_report_controls_exist(self):
        for marker in (
            'id="reportButton"', 'id="reportMenu"', 'id="reportPdfButton"',
            'id="reportHtmlButton"', 'id="reportShareButton"', 'id="reportPrintButton"',
        ):
            self.assertIn(marker, self.html)

    def test_report_controls_follow_analysis_state(self):
        self.assertIn("function setReportControlsEnabled(enabled)", self.html)
        self.assertIn("setReportControlsEnabled(false);", self.html)
        self.assertIn("window.__lastAnalysisResult=data;", self.html)
        self.assertIn("setReportControlsEnabled(true);", self.html)

    def test_report_model_and_safety_helpers_exist(self):
        for marker in (
            "function safeReportText(value)",
            "function reportNumber(value,digits=1,unit='')",
            "function reportFileBaseName()",
            "function buildReportModel(data)",
            "function escapeReportHtml(value)",
        ):
            self.assertIn(marker, self.html)

    def test_report_does_not_serialize_sensitive_runtime_fields(self):
        self.assertNotIn("JSON.stringify(window.__lastAnalysisResult)", self.html)
        self.assertIn("delete safe.plotToken", self.html)
        self.assertIn("delete safe._mavlinkPlotPromise", self.html)

    def test_standalone_html_builder_has_required_sections(self):
        self.assertIn("function buildReportHtml(data,chartImages={})", self.html)
        for label in ("Звіт аналізу польоту", "Основні показники", "Зв’язок", "VTX", "Критичні події", "AI-висновок"):
            self.assertIn(label, self.html)
        self.assertIn("@media print", self.html)

    def test_report_reuses_processed_event_and_vtx_paths(self):
        self.assertIn("summarizeVtxFrequencySelectionsAllDbm", self.html)
        self.assertIn("function reportBoardMessages(model)", self.html)
        self.assertIn("function reportVtxMatrix(model)", self.html)
        self.assertIn("function reportAiConclusion(model)", self.html)
        self.assertIn("Gyros inconsistent", self.html)

    def test_vtx_report_uses_existing_best_worst(self):
        self.assertIn("model.vtx.stableFrequency", self.html)
        self.assertIn("model.vtx.worstFrequency", self.html)
        self.assertIn("dbmSamples", self.html)
        self.assertIn("'K1':[5180,5520,5700]", self.html)
        self.assertIn("'K2':[5240,5580,5765]", self.html)
        self.assertIn("'K3':[5300,5640,5825]", self.html)

    def test_report_chart_helpers_exist(self):
        self.assertIn("function renderReportChart(title,series,width=1000,height=320)", self.html)
        self.assertIn("function buildReportChartImages(data)", self.html)
        self.assertIn("canvas.toDataURL('image/png')", self.html)
        self.assertIn("data?.graph_data||{}", self.html)
        for key in ('altitude_m','voltage_v','current_a','radio_dbm','rssi_pct','engine_load_pct'):
            self.assertIn(key, self.html)

    def test_report_reuses_engine_load_summary(self):
        report_block=self.html.split('// REPORT_EXPORT_V1',1)[1].split('function getVoltageClass',1)[0]
        self.assertIn('summarizeEngineLoad(data?.timeline)', report_block)
        self.assertNotIn('VFR_HUD.throttle', report_block)

    def test_export_actions_exist(self):
        for marker in (
            "async function getCurrentReportHtml()",
            "async function createReportBlob()",
            "async function downloadReportHtml()",
            "async function openReportForPrint()",
            "async function shareReport()",
            "navigator.share", "navigator.canShare", "URL.createObjectURL",
        ):
            self.assertIn(marker, self.html)

    def test_share_cancel_is_silent_and_errors_use_existing_ui(self):
        self.assertIn("e?.name==='AbortError'", self.html)
        self.assertIn("UI.error.textContent", self.html)
        self.assertIn("UI.error.style.display='block'", self.html)

    def test_report_css_is_responsive_and_disabled_state_is_visible(self):
        self.assertIn("#reportButton:disabled{opacity:.45;cursor:not-allowed}", self.html)
        self.assertIn(".report-export{position:relative;display:inline-flex", self.html)
        self.assertIn("@media(max-width:760px){.report-menu{position:fixed;left:12px;right:12px;bottom:12px;top:auto", self.html)


if __name__ == "__main__":
    unittest.main()
