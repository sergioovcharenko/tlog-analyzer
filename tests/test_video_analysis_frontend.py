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
    assert "'/analyze'" in HTML or '"/analyze"' in HTML
    assert "/analyze-video" in HTML
    assert "analyzeEndpoint" in HTML
    assert "videoEnabled" in HTML
    assert "videoFile" in HTML
    assert "formData.append('video'" in HTML or 'formData.append("video"' in HTML


def test_roi_editor_controls_and_labels_exist():
    assert 'id="videoRoiOverlay"' in HTML
    assert 'id="videoRoiLabel"' in HTML
    assert 'id="videoAddRoi"' in HTML
    assert 'id="videoClearRois"' in HTML
    assert "Додати зону" in HTML
    for label in ("Напруга", "dBm", "Режим", "Попередження", "Відеоканал", "Інше"):
        assert label in HTML


def test_roi_editor_converts_display_pixels_to_source_pixels():
    assert "video.videoWidth" in HTML or "VideoUI.preview.videoWidth" in HTML
    assert "video.videoHeight" in HTML or "VideoUI.preview.videoHeight" in HTML
    assert "displayRectToSourceRoi" in HTML
    assert "pointerdown" in HTML
    assert "pointermove" in HTML
    assert "pointerup" in HTML


def test_manual_partial_clip_sync_controls_exist():
    assert 'id="videoSetAnchor"' in HTML
    assert 'id="tlogSelectAnchor"' in HTML
    assert 'id="videoSyncPair"' in HTML
    assert "Взяти поточний час відео" in HTML
    assert "Вибрати момент TLOG" in HTML
    assert "відео" in HTML and "TLOG" in HTML


def test_manual_sync_uses_video_current_time_and_timeline_row_time():
    assert "currentTime" in HTML
    assert "timelineSeconds" in HTML
    assert "video_anchor_sec" in HTML
    assert "tlog_anchor_sec" in HTML
    assert "awaitingTlogAnchor" in HTML
