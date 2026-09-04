from pathlib import Path
import unittest

HTML = Path("index.html").read_text(encoding="utf-8")


class Tx16UiContractTests(unittest.TestCase):
    def test_confirmed_tx16_channel_labels_are_present(self):
        for label in (
            "SA — CH7", "SB — CH8", "SC — CH15", "SF — CH10",
            "SD — CH13", "SH — CH6", "LS — CH12", "RS — CH9",
        ):
            self.assertIn(label, HTML)

    def test_obsolete_fc_fs_labels_are_removed(self):
        self.assertNotIn("FC — CH15", HTML)
        self.assertNotIn("FS — CH11", HTML)

    def test_drop_and_emergency_use_correct_selector_channels(self):
        self.assertIn("const sc=rcPwmValue(row,15);", HTML)
        self.assertIn("const sd=rcPwmValue(row,13);", HTML)
        self.assertIn("EMERGENCY STOP", HTML)
        self.assertIn("SD=ДО СЕБЕ + SH", HTML)

    def test_vtx_names_match_confirmed_sa_sb_mapping(self):
        self.assertIn("SA=CH7, SB=CH8", HTML)


if __name__ == "__main__":
    unittest.main()
