from pathlib import Path
import unittest

SRC = Path("backend/main.py").read_text(encoding="utf-8")


class BackendTx16MappingTests(unittest.TestCase):
    def test_switch_channel_mapping(self):
        for item in ('"SH": 6', '"SA": 7', '"SB": 8', '"SF": 10', '"SD": 13', '"SC": 15'):
            self.assertIn(item, SRC)

    def test_three_position_switch_names(self):
        self.assertIn('if name in ("SA", "SB", "SC", "SD"):', SRC)


if __name__ == "__main__":
    unittest.main()
