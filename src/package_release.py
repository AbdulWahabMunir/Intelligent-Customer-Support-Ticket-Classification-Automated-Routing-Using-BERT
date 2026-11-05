"""Create a clean source archive and separate model bundle with SHA-256 hashes."""

import hashlib
import json
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

from src.data.inspect import ROOT


def digest(path):
    with path.open("rb") as source:
        return hashlib.file_digest(source, "sha256").hexdigest()


def main():
    destination = ROOT / "artifacts/release"
    destination.mkdir(parents=True, exist_ok=True)
    model_files = [ROOT / "models/distilbert/experiment.json", ROOT / "models/logistic_regression.joblib"]
    model_files += sorted(path for path in (ROOT / "models/distilbert/final").iterdir() if path.is_file())
    metadata = json.loads(model_files[0].read_text(encoding="utf-8"))
    if metadata["status"] != "training_complete" or not metadata["reload_inference_passed"]:
        raise ValueError("Completed, reload-verified model required")
    model_zip = destination / "model-bundle.zip"
    with ZipFile(model_zip, "w", compression=ZIP_DEFLATED, compresslevel=3) as archive:
        for path in model_files:
            archive.write(path, path.relative_to(ROOT / "models").as_posix())
    source_files = []
    for name in ["app", "src", "tests", "scripts", "config", "docs", "reports", "notebooks", ".streamlit", ".github", "docker", "community", "data/robustness"]:
        source_files += [path for path in (ROOT / name).rglob("*") if path.is_file() and "__pycache__" not in path.parts and path.suffix != ".pyc"]
    source_files += [path for path in ROOT.iterdir() if path.is_file() and (path.name.startswith("requirements") or path.name in {"README.md", ".gitignore", ".dockerignore", "Dockerfile", "compose.yaml", "render.yaml", "render-free.yaml"})]
    source_files = [path for path in source_files if path.name != 'secrets.toml' and not path.name.startswith('.env')]
    source_files = [path for path in source_files if "installation" not in path.relative_to(ROOT).parts]
    source_zip = destination / "customer-support-source.zip"
    with ZipFile(source_zip, "w", compression=ZIP_DEFLATED) as archive:
        for path in sorted(set(source_files)):
            archive.write(path, path.relative_to(ROOT).as_posix())
    report = {"source": {"file": source_zip.name, "bytes": source_zip.stat().st_size, "sha256": digest(source_zip)},
              "models": {"file": model_zip.name, "bytes": model_zip.stat().st_size, "sha256": digest(model_zip)},
              "excluded": ["raw customer dataset", "runtime ticket databases", "model training checkpoints", "caches", "virtual environment", "installers"]}
    (destination / "manifest.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
