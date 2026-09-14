from backend.video_analysis import map_video_to_tlog_time, validate_roi, normalize_rois


def test_partial_clip_anchor_mapping():
    assert map_video_to_tlog_time(37.0, 37.0, 822.0) == 822.0
    assert map_video_to_tlog_time(0.0, 37.0, 822.0) == 785.0
    assert map_video_to_tlog_time(120.0, 37.0, 822.0) == 905.0


def test_validate_roi_accepts_rect_inside_frame():
    roi = {"id": "r1", "label": "dBm", "x": 100, "y": 50, "width": 200, "height": 80}
    assert validate_roi(roi, 1920, 1080)["label"] == "dBm"


def test_normalize_rois_rejects_zero_or_outside_rect_without_failing_all():
    rois = [
        {"id": "ok", "label": "Напруга", "x": 10, "y": 10, "width": 100, "height": 40},
        {"id": "bad", "label": "dBm", "x": 1900, "y": 10, "width": 100, "height": 40},
    ]
    valid, warnings = normalize_rois(rois, 1920, 1080)
    assert [r["id"] for r in valid] == ["ok"]
    assert warnings


def test_sample_times_support_short_partial_clip():
    from backend.video_analysis import build_sample_times
    times = build_sample_times(5.0, normal_fps=1.0)
    assert times == [0.0, 1.0, 2.0, 3.0, 4.0, 5.0]


def test_dense_windows_do_not_create_unbounded_samples():
    from backend.video_analysis import build_sample_times
    times = build_sample_times(20.0, normal_fps=1.0, dense_windows=[(9.0, 11.0)])
    assert len(times) < 100
    assert any(9.0 < t < 10.0 for t in times)


def test_correlation_uses_non_causal_wording():
    from backend.video_analysis import build_observation, correlate_observations
    obs = [
        build_observation(
            10.0,
            810.0,
            {"id": "v", "label": "Відеоканал"},
            "video_degradation",
            "Сильні артефакти",
            0.9,
        )
    ]
    events = [{"timeSec": 810.4, "type": "RADIO_LOSS", "text": "-128 dBm"}]
    out = correlate_observations(obs, events, max_delta_sec=2.0)
    assert len(out) == 1
    assert out[0]["deltaSec"] == 0.4
    assert "часово" in out[0]["summary"].lower()
    assert "причин" not in out[0]["summary"].lower()


def test_correlation_ignores_events_outside_window():
    from backend.video_analysis import build_observation, correlate_observations
    obs = [build_observation(10.0, 810.0, {"id": "v", "label": "Відеоканал"}, "video_degradation", "Артефакти", 0.8)]
    events = [{"timeSec": 814.0, "type": "RADIO_LOSS", "text": "-128 dBm"}]
    assert correlate_observations(obs, events, max_delta_sec=2.0) == []


def test_packaged_ffmpeg_can_probe_and_extract_without_system_ffprobe(tmp_path):
    import subprocess
    import imageio_ffmpeg
    from backend.video_analysis import extract_frame, probe_video

    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    video_path = tmp_path / "sample.mp4"
    frame_path = tmp_path / "frame.jpg"
    subprocess.run(
        [
            ffmpeg,
            "-hide_banner",
            "-loglevel",
            "error",
            "-f",
            "lavfi",
            "-i",
            "color=c=black:s=160x90:d=1:r=10",
            "-pix_fmt",
            "yuv420p",
            "-y",
            str(video_path),
        ],
        check=True,
        timeout=30,
    )

    meta = probe_video(video_path)
    assert meta["width"] == 160
    assert meta["height"] == 90
    assert meta["durationSec"] > 0
    assert meta["fps"] > 0

    extract_frame(video_path, 0.2, frame_path)
    assert frame_path.exists()
    assert frame_path.stat().st_size > 0
