"""Start the local API and dashboard without changing PowerShell policy."""

from pathlib import Path
import subprocess
import sys
import time
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]


def healthy(url):
    try:
        with urlopen(url, timeout=2) as response:
            return response.status == 200
    except OSError:
        return False


def main():
    logs = ROOT / "data/runtime/logs"
    logs.mkdir(parents=True, exist_ok=True)
    services = [
        ("api", "http://127.0.0.1:8000/health", ["-m", "uvicorn", "app.api:app", "--host", "127.0.0.1", "--port", "8000"]),
        ("dashboard", "http://127.0.0.1:8501/_stcore/health", ["-m", "streamlit", "run", "app/dashboard.py"]),
    ]
    for name, url, arguments in services:
        if not healthy(url):
            with (logs / f"{name}.log").open("ab") as output:
                subprocess.Popen([sys.executable] + arguments, cwd=ROOT, stdout=output, stderr=output,
                                 creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    deadline = time.monotonic() + 90
    while time.monotonic() < deadline:
        if all(healthy(url) for _, url, _ in services):
            print("Dashboard: http://127.0.0.1:8501\nAPI docs: http://127.0.0.1:8000/docs")
            return
        time.sleep(1)
    raise RuntimeError(f"Services did not become ready; inspect {logs}")


if __name__ == "__main__":
    main()
