"""Verify the container HTTP/data flow, including API restart persistence."""

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import time

import httpx

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--docker", default="docker")
    args = parser.parse_args()
    with httpx.Client(base_url="http://127.0.0.1:8002", timeout=60, trust_env=False) as client:
        health = client.get("/health")
        health.raise_for_status()
        response = client.post("/tickets", json={"text": "I need to track my refund"})
        response.raise_for_status()
        original = response.json()
        assert original["result"]["prediction"]["intent"] == "track_refund"
        feedback = client.post(f"/tickets/{original['id']}/feedback", json={"corrected_intent": "track_refund", "note": "Automated container verification"})
        feedback.raise_for_status()
        subprocess.run([args.docker, "compose", "restart", "api"], cwd=ROOT, check=True)
        deadline = time.monotonic() + 120
        while time.monotonic() < deadline:
            try:
                if client.get("/health", timeout=3).status_code == 200:
                    break
            except httpx.RequestError:
                pass
            time.sleep(1)
        else:
            raise RuntimeError("API did not recover after container restart")
        restored = client.get(f"/tickets/{original['id']}")
        restored.raise_for_status()
        assert restored.json()["result"] == original["result"]
        assert restored.json()["feedback_count"] == 1
        with httpx.Client(timeout=15, trust_env=False) as browser:
            browser.get("http://127.0.0.1:8502/_stcore/health").raise_for_status()
        report = {"status": "passed", "verified_at": datetime.now(timezone.utc).isoformat(),
                  "model_version": health.json()["model_version"], "ticket_id": original["id"],
                  "checks": ["container API prediction", "SQLite persistence", "feedback preservation", "API restart persistence", "dashboard health"]}
        destination = ROOT / "reports/containers/runtime.json"
        destination.write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
