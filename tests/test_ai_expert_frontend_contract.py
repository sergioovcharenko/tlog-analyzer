from pathlib import Path
import unittest

HTML = Path("index.html").read_text(encoding="utf-8")


class AIExpertFrontendContractTest(unittest.TestCase):
    def test_expert_block_and_renderer_exist(self):
        for marker in (
            'id="aiExpertBlock"',
            'id="aiExpertSummary"',
            'id="aiExpertSessions"',
            'id="aiExpertDetails"',
            "function renderAiExpert(expert)",
            "renderAiExpert(data.ai_expert)",
        ):
            self.assertIn(marker, HTML)

    def test_required_expert_sections_exist(self):
        for heading in (
            "ПІДТВЕРДЖЕНО TLOG",
            "ЙМОВІРНА ІНТЕРПРЕТАЦІЯ",
            "ЩО НЕМОЖЛИВО ВСТАНОВИТИ",
            "ЩО ПЕРЕВІРИТИ",
        ):
            self.assertIn(heading, HTML)

    def test_old_ai_reconstruction_remains_as_fallback(self):
        self.assertIn('id="aiReconstructionBlock"', HTML)
        self.assertIn("renderAiReconstruction(data.ai_reconstruction)", HTML)

    def test_primary_session_is_expandable_and_selected(self):
        self.assertIn("expert.primary_session_id", HTML)
        self.assertIn("ai-expert-session", HTML)
        self.assertIn("details.open", HTML)


if __name__ == "__main__":
    unittest.main()
