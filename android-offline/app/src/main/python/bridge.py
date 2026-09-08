import threading
import time

_started = False
_lock = threading.Lock()


def start_server():
    global _started
    with _lock:
        if _started:
            return True

        def run():
            import uvicorn
            import main
            uvicorn.run(
                main.app,
                host="127.0.0.1",
                port=8765,
                log_level="warning",
                access_log=False,
            )

        thread = threading.Thread(target=run, name="tlog-offline-server", daemon=True)
        thread.start()
        _started = True
        return True
