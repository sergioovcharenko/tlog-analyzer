from pathlib import Path
import unittest


class IndexedTlogFallbackContractTest(unittest.TestCase):
    def test_fallback_keeps_full_efi_status_path(self):
        text = Path("backend/main.py").read_text(encoding="utf-8")
        self.assertIn('if not efi_indexed_enabled:', text)
        self.assertIn('needed_messages.append("EFI_STATUS")', text)
        self.assertIn('elif msg_type == "EFI_STATUS":', text)


if __name__ == "__main__":
    unittest.main()
