from pathlib import Path
import unittest

HTML = Path("index.html").read_text(encoding="utf-8")


class AIReconstructionFrontendContractTest(unittest.TestCase):
    def test_block_is_below_existing_findings(self):
        self.assertIn('id="aiBlock"', HTML)
        self.assertIn('id="aiReconstructionBlock"', HTML)
        self.assertLess(HTML.index('id="aiBlock"'), HTML.index('id="aiReconstructionBlock"'))
        self.assertIn('🤖 AI ВИСНОВОК', HTML)

    def test_renderer_and_sections_exist(self):
        for marker in (
            "function renderAiReconstruction(recon)",
            "aiReconWhat",
            "aiReconSequence",
            "aiReconActions",
            "aiReconAlternatives",
            "aiReconConfidence",
            "renderAiReconstruction(data.ai_reconstruction)",
        ):
            self.assertIn(marker, HTML)

    def test_existing_findings_list_is_preserved(self):
        self.assertIn('id="aiAlerts" class="ai-list"', HTML)
        self.assertIn("aiTitle.textContent=data.ai?.verdict||'Результати';", HTML)


if __name__ == "__main__":
    unittest.main()
