from pathlib import Path
import unittest


class IndexedTlogIntegrationContractTest(unittest.TestCase):
    def test_main_uses_indexed_efi_with_fallback_and_metrics(self):
        text = Path("backend/main.py").read_text(encoding="utf-8")

        self.assertIn("INDEXED_EFI_STATUS_V1", text)
        self.assertIn("build_indexed_numeric_series", text)
        self.assertIn('"EFI_STATUS", "engine_load", interval_s=0.2', text)
        self.assertIn("efi_indexed_enabled", text)
        self.assertIn("efi_indexed_input_count", text)
        self.assertIn("efi_indexed_decoded_count", text)
        self.assertIn('needed_messages.append("EFI_STATUS")', text)
        self.assertIn("efi_engine_load_samples", text)
        self.assertIn("efi_sample_index", text)
        self.assertIn("⚡ <b>EFI_STATUS індекс:</b>", text)


if __name__ == "__main__":
    unittest.main()
