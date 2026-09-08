from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
MAIN = (ROOT / 'backend' / 'main.py').read_text(encoding='utf-8')
AI = (ROOT / 'backend' / 'ai_reconstruction.py').read_text(encoding='utf-8')


class GyrosInconsistentConclusionContract(unittest.TestCase):
    def test_board_marks_gyros_inconsistent_as_serious(self):
        self.assertIn('"gyros inconsistent"', MAIN)

    def test_ai_has_prearm_gyros_explanation(self):
        self.assertIn('def augment_ai_reconstruction_with_prearm_diagnostics', AI)
        self.assertIn('Gyros inconsistent', AI)
        self.assertIn('розбіжність між показами гіроскопів', AI)
        self.assertIn('калібрування IMU', AI)

    def test_main_applies_prearm_diagnostics(self):
        self.assertIn('augment_ai_reconstruction_with_prearm_diagnostics', MAIN)
        self.assertIn('ai_reconstruction = augment_ai_reconstruction_with_prearm_diagnostics(', MAIN)


if __name__ == '__main__':
    unittest.main()
