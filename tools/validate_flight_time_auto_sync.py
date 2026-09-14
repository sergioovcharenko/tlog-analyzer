import argparse
import json
from pathlib import Path

from fastapi.testclient import TestClient

import backend.main as backend_main
from backend.video_analysis import probe_video, run_flight_time_auto_sync


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("tlog", type=Path)
    parser.add_argument("video", type=Path)
    parser.add_argument("--roi", required=True)
    args = parser.parse_args()

    client = TestClient(backend_main.app)
    with args.tlog.open("rb") as handle:
        response = client.post(
            "/analyze",
            files={
                "file": (args.tlog.name, handle, "application/octet-stream")
            },
        )
    response.raise_for_status()
    tlog_result = response.json()
    sessions = (tlog_result.get("flight") or {}).get("flightSessions") or []
    metadata = probe_video(args.video)
    result = run_flight_time_auto_sync(
        args.video,
        metadata,
        json.loads(args.roi),
        sessions,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
