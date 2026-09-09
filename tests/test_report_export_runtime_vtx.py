from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
INDEX = (ROOT / "index.html").read_text(encoding="utf-8")
FINALIZER = (ROOT / "tools" / "finalize_report_export.py").read_text(encoding="utf-8")


class ReportExportRuntimeVtxRegression(unittest.TestCase):
    def test_report_uses_existing_vtx_summary_helper(self):
        self.assertIn("const vtx=summarizeVtxFrequencySelections(data?.timeline,v?.frequencyDbmStats);", INDEX)
        self.assertNotIn("summarizeVtxFrequencySelectionsAllDbm", INDEX)
        self.assertIn("const vtx=summarizeVtxFrequencySelections(data?.timeline,v?.frequencyDbmStats);", FINALIZER)
        self.assertNotIn("summarizeVtxFrequencySelectionsAllDbm", FINALIZER)

    def test_report_button_is_slightly_inset_and_lower(self):
        expected = ".report-export{position:relative;display:inline-flex;justify-content:flex-end;margin:6px 10px 18px 0;float:right}"
        self.assertIn(expected, INDEX)
        self.assertIn(expected, FINALIZER)


if __name__ == "__main__":
    unittest.main()
