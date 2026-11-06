"""Capture the local dashboard using an isolated installed Edge profile."""

import base64
import json
from pathlib import Path
import subprocess
import time
from urllib.request import urlopen

from websockets.sync.client import connect

ROOT = Path(__file__).resolve().parents[1]


def main():
    edge = Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe")
    profile = ROOT / "artifacts/edge-capture-profile"
    output = ROOT / "reports/screenshots/overview.png"
    output.parent.mkdir(parents=True, exist_ok=True)
    process = subprocess.Popen([str(edge), "--headless", "--disable-gpu", "--disable-breakpad", "--no-first-run",
               f"--user-data-dir={profile}", "--remote-debugging-port=9223", "--window-size=1440,1100", "http://127.0.0.1:8501"],
               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=subprocess.CREATE_NO_WINDOW)
    try:
        deadline = time.monotonic() + 40
        pages = []
        while time.monotonic() < deadline:
            try:
                with urlopen("http://127.0.0.1:9223/json/list", timeout=2) as response:
                    pages = [p for p in json.load(response) if p.get("type") == "page"]
                if pages:
                    break
            except OSError:
                pass
            time.sleep(0.3)
        if not pages:
            raise RuntimeError("Headless browser did not become ready")
        with connect(pages[0]["webSocketDebuggerUrl"], open_timeout=10) as websocket:
            counter = 0

            def command(method, params=None):
                nonlocal counter
                counter += 1
                websocket.send(json.dumps({"id": counter, "method": method, "params": params or {}}))
                while True:
                    response = json.loads(websocket.recv(timeout=10))
                    if response.get("id") == counter:
                        if "error" in response:
                            raise RuntimeError(response["error"])
                        return response["result"]

            command("Page.enable")
            command("Emulation.setDeviceMetricsOverride", {"width": 1440, "height": 1100, "deviceScaleFactor": 1, "mobile": False})
            text = ""
            while time.monotonic() < deadline:
                result = command("Runtime.evaluate", {"expression": "document.body.innerText", "returnByValue": True})
                text = result.get("result", {}).get("value", "")
                if "Support overview" in text and "Total tickets" in text:
                    break
                time.sleep(0.5)
            if "Support overview" not in text or "Total tickets" not in text:
                raise RuntimeError("Dashboard did not render expected content: " + text[:200])
            time.sleep(12)  # Allow HTML cards, styles and sidebar animation to finish.
            screenshot = command("Page.captureScreenshot", {"format": "png", "captureBeyondViewport": False})
            output.write_bytes(base64.b64decode(screenshot["data"]))
            print(f"Verified browser content and saved {output}")
    finally:
        process.terminate()
        process.wait(timeout=10)


if __name__ == "__main__":
    main()
