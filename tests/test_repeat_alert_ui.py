from pathlib import Path
import unittest


class RepeatAlertUiContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html = Path('index.html').read_text(encoding='utf-8')
        cls.backend = Path('backend/main.py').read_text(encoding='utf-8')

    def test_esc_only_title_is_bold(self):
        self.assertNotIn('class="ai-jump esc-fault-alert-bold"', self.html)
        self.assertIn('const escTitle=', self.html)
        self.assertIn('<b>${escTitle}</b>', self.html)

    def test_radio_uses_switch_names_not_channel_numbers(self):
        self.assertNotIn('CH7/CH8/VTX', self.backend)
        self.assertNotIn('CH7/CH8 —', self.backend)
        self.assertIn('SA/SB/VTX', self.backend)
        self.assertIn('parts.append(f"SA {int(round(ch7))} us")', self.backend)
        self.assertIn('parts.append(f"SB {int(round(ch8))} us")', self.backend)
        self.assertIn('.vtx-switch-label', self.html)

    def test_no_global_severity_grouping(self):
        self.assertNotIn('buildAttentionSummaryHtml(combinedAiAlerts)', self.html)
        self.assertIn('buildRepeatedAlertListHtml(combinedAiAlerts)', self.html)

    def test_only_repeated_types_get_dropdowns(self):
        self.assertIn('function repeatedAlertKey', self.html)
        self.assertIn("return 'potential-thrust-loss'", self.html)
        self.assertIn('class="repeat-alert-group', self.html)
        self.assertIn('group.length>1', self.html)

    def test_high_current_remains_visible_and_colored(self):
        self.assertIn('ВИСОКЕ СПОЖИВАННЯ СТРУМУ', self.html)
        self.assertIn('alert-attention', self.html)


if __name__ == '__main__':
    unittest.main()
