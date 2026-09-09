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
            'id="reportButton"',
            'id="reportMenu"',
            'id="reportPdfButton"',
            'id="reportHtmlButton"',
            'id="reportShareButton"',
            'id="reportPrintButton"',
        ):
            self.assertIn(marker, self.html)

    def test_report_controls_follow_analysis_state(self):
        self.assertIn("function setReportControlsEnabled(enabled)", self.html)
        self.assertIn("setReportControlsEnabled(false);", self.html)
        self.assertIn("window.__lastAnalysisResult=data;", self.html)
        self.assertIn("setReportControlsEnabled(true);", self.html)


if __name__ == "__main__":
    unittest.main()
