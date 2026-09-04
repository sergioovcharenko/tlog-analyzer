from pathlib import Path
import unittest


class AttentionSummaryContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html = Path('index.html').read_text(encoding='utf-8')

    def test_grouped_collapsible_attention_summary_exists(self):
        self.assertIn('function buildAttentionSummaryHtml', self.html)
        self.assertIn('На що звернути увагу', self.html)
        self.assertIn('Критичне', self.html)
        self.assertIn('Увага', self.html)
        self.assertIn('Попередження', self.html)
        self.assertIn('Інформація', self.html)
        self.assertIn('attention-summary', self.html)

    def test_high_current_over_80_is_promoted_to_attention(self):
        self.assertIn('ВИСОКЕ СПОЖИВАННЯ СТРУМУ', self.html)
        self.assertIn('maxCurrentRow', self.html)
        self.assertIn('>80', self.html)
        self.assertIn('data-attention-severity="attention"', self.html)

    def test_existing_alerts_keep_timeline_jump_support(self):
        self.assertIn('data-jump-time', self.html)
        self.assertIn('ai-clickable', self.html)
        self.assertIn('buildAttentionSummaryHtml(combinedAiAlerts', self.html)


if __name__ == '__main__':
    unittest.main()
