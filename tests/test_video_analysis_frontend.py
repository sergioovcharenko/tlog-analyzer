from pathlib import Path
import re

# HOTFIX_VERIFICATION_V1
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
    match = re.search(r'<select id="videoRoiLabel"[^>]*>(.*?)</select>', HTML, re.S)
    assert match, "video ROI label select not found"
    options = re.findall(r'<option>(.*?)</option>', match.group(1), re.S)
    assert options == [
        "Flight Time",
        "Напруга АКБ",
        "Ампераж",
        "dBm",
        "RSSI",
        "VISP",
        "Режим",
        "Попередження",
        "Інше",
    ]
    assert "Відеоканал" not in options


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


def test_flight_time_auto_sync_controls_exist():
    assert 'id="videoAutoSync"' in HTML
    assert 'id="videoAutoSyncStatus"' in HTML
    assert 'id="videoAutoSyncConfidence"' in HTML
    assert 'id="videoAutoSyncCandidate"' in HTML
    assert 'id="videoAutoSyncApplyCandidate"' in HTML
    assert "Автосинхронізація по Flight Time" in HTML


def test_flight_time_auto_sync_reuses_existing_anchor_state():
    assert "flight_time_roi_json" in HTML
    assert "auto_sync" in HTML
    assert "runFlightTimeAutoSync" in HTML
    assert "applyAutoSyncResult" in HTML
    assert "autoSync.videoAnchorSec" in HTML
    assert "autoSync.tlogAnchorSec" in HTML
    assert "videoAnchorSec=va" in HTML or "videoAnchorSec = va" in HTML
    assert "tlogAnchorSec=ta" in HTML or "tlogAnchorSec = ta" in HTML
    assert "videoAnchorSec=0" in HTML or "videoAnchorSec = 0" in HTML
    assert "tlogAnchorSec=offset" in HTML or "tlogAnchorSec = offset" in HTML


def test_combined_video_tlog_results_section_exists():
    assert 'id="videoAnalysisSection"' in HTML
    assert 'id="videoAnalysisSummary"' in HTML
    assert 'id="videoAnalysisCorrelations"' in HTML
    assert 'id="videoAnalysisObservations"' in HTML
    assert 'id="videoAnalysisWarnings"' in HTML
    assert "AI — ВІДЕО + TLOG" in HTML
    assert "renderVideoAnalysisSection" in HTML


def test_combined_results_renderer_is_optional_and_surfaces_key_fields():
    assert "data?.videoAnalysis" in HTML or "data.videoAnalysis" in HTML
    assert "videoAnalysisSection.hidden=true" in HTML or "section.hidden=true" in HTML
    assert "correlations" in HTML
    assert "observations" in HTML
    assert "warnings" in HTML
    assert "confidence" in HTML
    assert "deltaSec" in HTML
    assert "roiLabel" in HTML
