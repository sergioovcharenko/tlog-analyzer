from pathlib import Path


MAIN = Path("backend/main.py")
MARKER = "# VIDEO_TLOG_ANALYSIS_ENDPOINT_V1"
LAUNCHER = "# ============================================================\n# OFFLINE V24 LAUNCHER\n# ============================================================"

ENDPOINT = r'''
# VIDEO_TLOG_ANALYSIS_ENDPOINT_V1
@app.post("/analyze-video")
async def analyze_video(
    file: UploadFile = File(...),
    video: UploadFile = File(...),
    video_anchor_sec: float | None = Form(None),
    tlog_anchor_sec: float | None = Form(None),
    rois_json: str = Form("[]"),
    auto_sync: bool = Form(False),
    flight_time_roi_json: str = Form(""),
):
    """Run the stable TLOG analyzer first, then add optional video metadata.

    Video failures are isolated: a completed TLOG result is still returned with
    a warning in ``videoAnalysis`` rather than failing the whole request.
    """
    import json
    try:
        from backend.video_analysis import (
            build_sample_times,
            normalize_rois,
            probe_video,
            run_flight_time_auto_sync,
        )
    except ImportError:
        from video_analysis import (
            build_sample_times,
            normalize_rois,
            probe_video,
            run_flight_time_auto_sync,
        )

    tlog_result = await analyze(file)
    if not isinstance(tlog_result, dict):
        return tlog_result

    video_result = {
        "enabled": True,
        "videoDurationSec": None,
        "anchorVideoSec": float(video_anchor_sec) if video_anchor_sec is not None else None,
        "anchorTlogSec": float(tlog_anchor_sec) if tlog_anchor_sec is not None else None,
        "rois": [],
        "observations": [],
        "correlations": [],
        "warnings": [],
        "autoSync": None,
    }
    tlog_result["videoAnalysis"] = video_result

    suffix = Path(video.filename or "").suffix.lower()
    temp_video_path = None
    try:
        if suffix not in {".mp4", ".mov"}:
            raise ValueError("Підтримуються відеофайли MP4 або MOV")

        temp_video = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
        temp_video_path = temp_video.name
        try:
            await video.seek(0)
            while True:
                chunk = await video.read(1024 * 1024)
                if not chunk:
                    break
                temp_video.write(chunk)
        finally:
            temp_video.close()

        metadata = probe_video(temp_video_path)
        duration = float(metadata["durationSec"])
        if video_anchor_sec is not None:
            if not 0.0 <= float(video_anchor_sec) <= duration:
                raise ValueError("Точка синхронізації відео виходить за межі ролика")

        timeline_times = []
        for row in tlog_result.get("timeline") or []:
            if isinstance(row, dict):
                t_ms = _timeline_graph_time_ms(row.get("time"))
                if t_ms is not None:
                    timeline_times.append(t_ms / 1000.0)
        if tlog_anchor_sec is not None and timeline_times:
            if not min(timeline_times) <= float(tlog_anchor_sec) <= max(timeline_times):
                raise ValueError("Точка синхронізації TLOG виходить за межі журналу")

        parsed_rois = json.loads(rois_json or "[]")
        if not isinstance(parsed_rois, list):
            raise ValueError("ROIs must be a JSON array")
        valid_rois, roi_warnings = normalize_rois(
            parsed_rois,
            int(metadata["width"]),
            int(metadata["height"]),
        )

        sample_times = build_sample_times(duration, normal_fps=1.0)
        video_result.update(
            {
                "videoDurationSec": duration,
                "videoWidth": int(metadata["width"]),
                "videoHeight": int(metadata["height"]),
                "videoFps": float(metadata.get("fps") or 0.0),
                "rois": valid_rois,
                "sampleCount": len(sample_times),
                "warnings": roi_warnings,
            }
        )

        if auto_sync:
            try:
                if not flight_time_roi_json:
                    raise ValueError("Для автосинхронізації намалюй зону Flight Time")
                flight_time_roi = json.loads(flight_time_roi_json)
                if not isinstance(flight_time_roi, dict):
                    raise ValueError("Flight Time ROI must be a JSON object")
                auto_result = run_flight_time_auto_sync(
                    temp_video_path,
                    metadata,
                    flight_time_roi,
                    (tlog_result.get("flight") or {}).get("flightSessions") or [],
                )
            except Exception as exc:
                auto_result = {
                    "status": "failed",
                    "confidence": "low",
                    "selectedFlight": None,
                    "armTlogSec": None,
                    "offsetSec": None,
                    "videoAnchorSec": None,
                    "tlogAnchorSec": None,
                    "samples": [],
                    "offsetSpreadSec": None,
                    "candidates": [],
                    "warnings": [f"Автосинхронізація недоступна: {exc}"],
                }
            video_result["autoSync"] = auto_result
            if (
                auto_result.get("status") == "success"
                and auto_result.get("confidence") in {"high", "medium"}
            ):
                video_result["anchorVideoSec"] = auto_result.get("videoAnchorSec")
                video_result["anchorTlogSec"] = auto_result.get("tlogAnchorSec")
        elif video_anchor_sec is None or tlog_anchor_sec is None:
            video_result["warnings"].append(
                "Для ручного відеоаналізу спочатку синхронізуй відео з TLOG"
            )
    except Exception as exc:
        video_result["warnings"].append(f"Відеоаналіз недоступний: {exc}")
    finally:
        if temp_video_path and os.path.exists(temp_video_path):
            try:
                os.unlink(temp_video_path)
            except OSError:
                pass

    return tlog_result
'''.strip("\n")


def main():
    source = MAIN.read_text(encoding="utf-8")
    if "from fastapi import FastAPI, File, UploadFile" in source:
        source = source.replace(
            "from fastapi import FastAPI, File, UploadFile",
            "from fastapi import FastAPI, File, Form, UploadFile",
            1,
        )

    if LAUNCHER not in source:
        raise SystemExit("offline launcher anchor not found")

    if MARKER in source:
        before, rest = source.split(MARKER, 1)
        _old_endpoint, after = rest.split(LAUNCHER, 1)
        source = before.rstrip() + "\n\n" + ENDPOINT + "\n\n\n" + LAUNCHER + after
    else:
        source = source.replace(
            LAUNCHER,
            ENDPOINT + "\n\n\n" + LAUNCHER,
            1,
        )

    MAIN.write_text(source, encoding="utf-8")


if __name__ == "__main__":
    main()
