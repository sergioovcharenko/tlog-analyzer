import threading
from pathlib import Path

_server_thread = None

def start_server(port=8765):
    global _server_thread
    if _server_thread is not None and _server_thread.is_alive():
        return True

    def run():
        import uvicorn
        from fastapi.responses import FileResponse
        from backend.main import app

        @app.get("/map3d.js", include_in_schema=False)
        def android_map3d():
            path = Path(__file__).resolve().parent / "backend" / "map3d.js"
            return FileResponse(path, media_type="application/javascript; charset=utf-8")

        uvicorn.run(
            app,
            host="127.0.0.1",
            port=int(port),
            log_level="warning",
            access_log=False,
        )

    _server_thread = threading.Thread(target=run, daemon=True, name="tlog-local-server")
    _server_thread.start()
    return True
