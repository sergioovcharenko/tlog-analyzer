import threading

_server_thread = None

def start_server(port=8765):
    global _server_thread
    if _server_thread is not None and _server_thread.is_alive():
        return True

    def run():
        import uvicorn
        from backend.main import app
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
