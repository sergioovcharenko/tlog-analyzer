from pathlib import Path
import unittest

HTML = Path('index.html').read_text(encoding='utf-8')


class EscAlertBoldTests(unittest.TestCase):
    def test_persistent_esc_fault_alert_is_entirely_bold(self):
        self.assertIn('.esc-fault-alert-bold{font-weight:800}', HTML)
        self.assertIn('class=\"ai-jump esc-fault-alert-bold\"', HTML)


if __name__ == '__main__':
    unittest.main()
