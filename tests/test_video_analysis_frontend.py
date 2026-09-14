from pathlib import Path


HTML = Path("index.html").read_text(encoding="utf-8")


def test_optional_video_upload_controls_exist():
    assert "Є відео польоту" in HTML
    assert 'id="videoFlightEnabled"' in HTML
    assert 'id="videoUploadPanel"' in HTML
    assert 'id="videoFileInput"' in HTML
    assert 'id="videoPreview"' in HTML
    assert "URL.createObjectURL" in HTML
    assert "URL.revokeObjectURL" in HTML


def test_tlog_only_and_video_assisted_paths_are_both_present():
    assert "API_BASE_URL+'/analyze'" in HTML or 'API_BASE_URL + "/analyze"' in HTML
    assert "/analyze-video" in HTML
    assert "videoEnabled" in HTML
    assert "videoFile" in HTML
    assert "formData.append('video'" in HTML or 'formData.append("video"' in HTML
