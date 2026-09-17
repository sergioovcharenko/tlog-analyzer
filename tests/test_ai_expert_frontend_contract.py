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

    def test_expert_chronology_rows_jump_to_timeline(self):
        self.assertIn("function bindAiExpertTimelineJumps()", HTML)
        self.assertIn("li.dataset.jumpTime", HTML)
        self.assertIn("title='Перейти до рядка Timeline'", HTML)
        self.assertIn("bindAiExpertTimelineJumps();", HTML)

    def test_timeline_uses_full_width_compact_columns_and_safe_highlight(self):
        self.assertIn("TIMELINE_FULL_WIDTH_COMPACT_V1", HTML)
        self.assertIn("width:calc(100vw - 24px)", HTML)
        self.assertIn("column-gap:8px", HTML)
        self.assertIn("inset 0 2px 0 #60a5fa", HTML)
        self.assertNotIn("outline:2px solid #60a5fa", HTML)


if __name__ == "__main__":
    unittest.main()
