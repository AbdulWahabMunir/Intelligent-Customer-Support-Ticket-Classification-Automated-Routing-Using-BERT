"""Download an immutable revision of the public Bitext CSV and dataset card."""

import hashlib
import json
from pathlib import Path
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[2]
DATASET = "bitext/Bitext-customer-support-llm-chatbot-training-dataset"
REVISION = "430d1a89bd93bd1fa23c16f29dd53e73f0087443"
FILENAME = "Bitext_Sample_Customer_Support_Training_Dataset_27K_responses-v11.csv"


def main():
    destination = ROOT / "data" / "raw"
    destination.mkdir(parents=True, exist_ok=True)
    manifest = {"dataset": DATASET, "revision": REVISION, "files": {}}
    for remote, local in [(FILENAME, "bitext.csv"), ("README.md", "DATASET_CARD.md")]:
        url = f"https://huggingface.co/datasets/{DATASET}/resolve/{REVISION}/{remote}"
        target = destination / local
        # A partial network download must never become the final CSV.
        temporary = target.with_suffix(target.suffix + ".part")
        try:
            with urlopen(url, timeout=120) as response, temporary.open("wb") as output:
                while chunk := response.read(1024 * 1024):
                    output.write(chunk)
            temporary.replace(target)
        finally:
            temporary.unlink(missing_ok=True)
        digest = hashlib.sha256(target.read_bytes()).hexdigest()
        manifest["files"][local] = {"url": url, "sha256": digest, "bytes": target.stat().st_size}
        print(f"Downloaded {local}: {target.stat().st_size:,} bytes")
    (destination / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
