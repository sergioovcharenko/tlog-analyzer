import os
import threading
from pathlib import Path

_server_thread = None
_shared_tlog_path = None
_shared_tlog_name = None

def register_shared_tlog(path, name):
    global _shared_tlog_path, _shared_tlog_name
    resolved = str(Path(path).resolve())
    if not os.path.isfile(resolved):
        raise FileNotFoundError(resolved)
    _shared_tlog_path = resolved
    _shared_tlog_name = str(name or Path(resolved).name)
    return True

def start_server(port=8765):
    global _server_thread
    if _server_thread is not None and _server_thread.is_alive():
        return True

    def run():
        import uvicorn
        from fastapi.responses import FileResponse
        from starlette.datastructures import UploadFile
        from backend.main import app, analyze

        @app.get("/map3d.js", include_in_schema=False)
        def android_map3d():
            path = Path(__file__).resolve().parent / "backend" / "map3d.js"
            return FileResponse(path, media_type="application/javascript; charset=utf-8")

        @app.get("/android-shared-tlog/meta", include_in_schema=False)
        def android_shared_tlog_meta():
            path = _shared_tlog_path
            if not path or not os.path.isfile(path):
                return {"available": False}
            return {
                "available": True,
                "name": _shared_tlog_name or Path(path).name,
                "size": os.path.getsize(path),
            }

        @app.post("/android-shared-tlog/analyze", include_in_schema=False)
        async def android_shared_tlog_analyze():
            path = _shared_tlog_path
            if not path or not os.path.isfile(path):
                return {"success": False, "error": "TLOG із зовнішнього застосунку недоступний"}
            handle = open(path, "rb")
            upload = UploadFile(filename=_shared_tlog_name or Path(path).name, file=handle)
            try:
                return await analyze(upload)
            finally:
                try:
                    await upload.close()
                except Exception:
                    try:
                        handle.close()
                    except Exception:
                        pass

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
