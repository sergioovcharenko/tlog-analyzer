from pathlib import Path

HTML = Path("index.html").read_text(encoding="utf-8")


def test_confirmed_tx16_channel_labels_are_present():
    for label in (
        "SA — CH7", "SB — CH8", "SC — CH15", "SF — CH10",
        "SD — CH13", "SH — CH6", "LS — CH12", "RS — CH9",
    ):
        assert label in HTML


def test_obsolete_fc_fs_labels_are_removed():
    assert "FC — CH15" not in HTML
    assert "FS — CH11" not in HTML


def test_drop_and_emergency_use_correct_selector_channels():
    assert "const sc=rcPwmValue(row,15);" in HTML
    assert "const sd=rcPwmValue(row,13);" in HTML
    assert "EMERGENCY STOP" in HTML
    assert "SD=ДО СЕБЕ + SH" in HTML


def test_vtx_names_match_confirmed_sa_sb_mapping():
    assert "SA=CH7, SB=CH8" in HTML
