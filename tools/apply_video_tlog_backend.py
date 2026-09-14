from pathlib import Path


MAIN = Path("backend/main.py")
MARKER = "# VIDEO_TLOG_ANALYSIS_ENDPOINT_V1"

ENDPOINT = r'''
# VIDEO_TLOG_ANALYSIS_ENDPOINT_V1
@app.post("/analyze-video")
async def analyze_video(
    file: UploadFile = File(...),
    video: UploadFile = File(...),
    video_anchor_sec: float = Form(...),
    tlog_anchor_sec: float = Form(...),
    rois_json: str = Form("[]"),
):
    """Run the stable TLOG analyzer first, then add optional video metadata.

    Video failures are isolated: a completed TLOG result is still returned with
    a warning in ``videoAnalysis`` rather than failing the whole request.
    """
    import json
    from backend.video_analysis import build_sample_times, normalize_rois, probe_video

    tlog_result = await analyze(file)
    if not isinstance(tlog_result, dict):
        return tlog_result

    video_result = {
        "enabled": True,
        "videoDurationSec": None,
        "anchorVideoSec": float(video_anchor_sec),
        "anchorTlogSec": float(tlog_anchor_sec),
        "rois": [],
        "observations": [],
        "correlations": [],
        "warnings": [],
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
        if not 0.0 <= float(video_anchor_sec) <= duration:
            raise ValueError("Точка синхронізації відео виходить за межі ролика")

        timeline_times = []
        for row in tlog_result.get("timeline") or []:
            if not isinstance(row, dict):
                continue
            t_ms = _timeline_graph_time_ms(row.get("time"))
            if t_ms is not None:
                timeline_times.append(t_ms / 1000.0)
        if timeline_times and not min(timeline_times) <= float(tlog_anchor_sec) <= max(timeline_times):
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

    if MARKER not in source:
        anchor = "\n# ============================================================\n# OFFLINE V24 LAUNCHER\n# ============================================================\n"
        if anchor not in source:
            raise SystemExit("offline launcher anchor not found")
        source = source.replace(anchor, "\n\n" + ENDPOINT + "\n\n" + anchor, 1)

    MAIN.write_text(source, encoding="utf-8")


if __name__ == "__main__":
    main()
