from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
HTML = (ROOT / 'index.html').read_text(encoding='utf-8')


class ReportExportFullContract(unittest.TestCase):
    def test_model_template_and_exports_exist(self):
        for marker in (
            'function safeReportText(value)',
            "function reportNumber(value,digits=1,unit='')",
            'function reportFileBaseName()',
            'function buildReportModel(data)',
            'function escapeReportHtml(value)',
            'function buildReportHtml(data,chartImages={})',
            'function buildReportChartImages(data)',
            'function downloadReportHtml()',
            'function openReportPrint()',
            'async function shareReport()',
        ):
            self.assertIn(marker, HTML)

    def test_required_report_sections_present(self):
        for label in ('Звіт аналізу польоту','Основні показники','Зв’язок','VTX','Критичні події','AI-висновок','Графіки'):
            self.assertIn(label, HTML)
        self.assertIn('@media print', HTML)

    def test_sensitive_runtime_payload_is_not_serialized(self):
        self.assertNotIn('JSON.stringify(window.__lastAnalysisResult)', HTML)
        self.assertIn('delete safe.plotToken', HTML)
        self.assertIn('delete safe._mavlinkPlotPromise', HTML)

    def test_share_and_pdf_are_browser_native(self):
        self.assertIn('navigator.share', HTML)
        self.assertIn('navigator.canShare', HTML)
        self.assertIn("new Blob([html],{type:'text/html;charset=utf-8'})", HTML)
        self.assertIn("w.print()", HTML)

    def test_no_third_party_pdf_dependency(self):
        lowered=HTML.lower()
        for forbidden in ('jspdf','pdfmake','cloudconvert','pdf.co'):
            self.assertNotIn(forbidden, lowered)

    def test_vtx_matrix_order_is_preserved(self):
        self.assertIn('[[5180,5520,5700],[5240,5580,5765],[5300,5640,5825]]', HTML)

    def test_engine_load_not_recomputed_from_vfr_hud(self):
        report_block=HTML.split('// REPORT_EXPORT_V1',1)[1].split('function getVoltageClass',1)[0]
        self.assertIn('h.engineLoadAvg', report_block)
        self.assertNotIn('VFR_HUD.throttle', report_block)


if __name__ == '__main__':
    unittest.main()
