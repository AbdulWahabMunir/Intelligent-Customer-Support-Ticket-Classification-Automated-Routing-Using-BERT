"""Provision a checksum-verified model bundle before a hosted service starts."""

import hashlib
import json
import os
from pathlib import Path
import re
import stat
import tempfile
from urllib.request import urlopen
from zipfile import ZipFile


def safe_extract(archive_path, target):
    target = Path(target).resolve()
    with ZipFile(archive_path) as archive:
        names = set()
        members = archive.infolist()
        if len(members) > 256 or sum(member.file_size for member in members) > 2 * 1024**3:
            raise ValueError("Unexpected model archive size")
        for member in members:
            if member.filename in names or not (target / member.filename).resolve().is_relative_to(target):
                raise ValueError("Unsafe or duplicate model archive path")
            if stat.S_ISLNK(member.external_attr >> 16):
                raise ValueError("Model archive symlinks are not allowed")
            names.add(member.filename)
        archive.extractall(target)


def model_ready(root):
    try:
        metadata = json.loads((root / "distilbert/experiment.json").read_text(encoding="utf-8"))
        return metadata["status"] == "training_complete" and metadata["reload_inference_passed"] and all(
            (root / "distilbert/final" / name).is_file() for name in ["config.json", "model.safetensors", "tokenizer.json", "tokenizer_config.json"])
    except (OSError, ValueError, KeyError):
        return False


def ensure_models(root):
    root = Path(root).resolve()
    url = os.environ.get("MODEL_BUNDLE_URL")
    expected = os.environ.get("MODEL_BUNDLE_SHA256", "").lower()
    if not url:
        if model_ready(root):
            return
        raise RuntimeError("Provide local model artifacts or MODEL_BUNDLE_URL and MODEL_BUNDLE_SHA256")
    if not re.fullmatch(r"[a-f0-9]{64}", expected) or not url.startswith("https://"):
        raise ValueError("A HTTPS model URL and SHA-256 checksum are required")
    marker = root / ".bundle-sha256"
    if model_ready(root) and marker.exists() and marker.read_text() == expected:
        return
    root.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=root.parent) as temporary:
        temporary = Path(temporary)
        archive_path = temporary / "bundle.zip"
        try:
            with urlopen(url, timeout=120) as response, archive_path.open("wb") as output:
                downloaded = 0
                while chunk := response.read(1024 * 1024):
                    downloaded += len(chunk)
                    if downloaded > 1024**3:
                        raise ValueError("Model download exceeds 1 GiB")
                    output.write(chunk)
        except OSError:
            raise RuntimeError("Model artifact download failed") from None
        with archive_path.open("rb") as source:
            if hashlib.file_digest(source, "sha256").hexdigest() != expected:
                raise ValueError("Model bundle checksum mismatch")
        unpacked = temporary / "unpacked"
        safe_extract(archive_path, unpacked)
        if not model_ready(unpacked):
            raise ValueError("Model bundle does not contain a completed checkpoint")
        for path in unpacked.rglob("*"):
            if path.is_file():
                target = root / path.relative_to(unpacked)
                target.parent.mkdir(parents=True, exist_ok=True)
                os.replace(path, target)
        marker.write_text(expected)
