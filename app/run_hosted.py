"""Run a password-protected Streamlit service with a loopback-only API."""

import os
from pathlib import Path
import signal
import subprocess
import sys
from threading import Event
import time
from urllib.request import urlopen

from app.bootstrap import ensure_models
from src.data.inspect import ROOT


def main():
    if len(os.environ.get("SUPPORT_DASHBOARD_PASSWORD", "")) < 12:
        raise ValueError("Hosted mode requires a dashboard password of at least 12 characters")
    port = int(os.environ.get("PORT", "10000"))
    internal_port = int(os.environ.get("SUPPORT_INTERNAL_API_PORT", "8000"))
    if not 1 <= port <= 65535 or not 1 <= internal_port <= 65535 or port == internal_port:
        raise ValueError("Invalid hosted dashboard port")
    models = Path(os.environ.get("SUPPORT_MODELS_PATH", str(ROOT / "models")))
    ensure_models(models)
    os.environ["SUPPORT_MODELS_PATH"] = str(models)
    api_url = f"http://127.0.0.1:{internal_port}"
    os.environ["SUPPORT_API_URL"] = api_url
    stopped = Event()
    for name in ["SIGINT", "SIGTERM"]:
        signal.signal(getattr(signal, name), lambda *_: stopped.set())
    processes = []
    try:
        api = subprocess.Popen([sys.executable, "-m", "uvicorn", "app.api:app", "--host", "127.0.0.1", "--port", str(internal_port)], cwd=ROOT)
        processes.append(api)
        deadline = time.monotonic() + 120
        while time.monotonic() < deadline and not stopped.is_set():
            if api.poll() is not None:
                raise RuntimeError("Hosted API exited before readiness")
            try:
                with urlopen(api_url + "/health", timeout=2) as response:
                    if response.status == 200:
                        break
            except OSError:
                pass
            time.sleep(0.5)
        else:
            raise RuntimeError("Hosted API did not become ready")
        dashboard = subprocess.Popen([sys.executable, "-m", "streamlit", "run", "app/dashboard.py", "--server.address", "0.0.0.0",
                                      "--server.port", str(port), "--server.headless", "true"], cwd=ROOT)
        processes.append(dashboard)
        while not stopped.wait(0.5):
            if any(process.poll() is not None for process in processes):
                raise RuntimeError("A hosted child process exited unexpectedly")
    finally:
        for process in reversed(processes):
            if process.poll() is None:
                process.terminate()
        for process in processes:
            try:
                process.wait(timeout=15)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)


if __name__ == "__main__":
    main()
