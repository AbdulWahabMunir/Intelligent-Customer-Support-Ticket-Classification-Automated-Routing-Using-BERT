"""Build and verify containers after Docker's Linux engine is ready."""

import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def main():
    docker = shutil.which("docker")
    if not docker:
        candidate = Path(os.environ.get("LOCALAPPDATA", "")) / "Programs/DockerDesktop/resources/bin/docker.exe"
        if candidate.is_file():
            docker = str(candidate)
    if not docker:
        raise RuntimeError("Install Docker Desktop first")
    result = subprocess.run([docker, "info", "--format", "{{.ServerVersion}}"], cwd=ROOT, timeout=45)
    if result.returncode:
        raise RuntimeError("Docker engine is unavailable. Restart Windows if required, then start Docker Desktop.")
    for arguments in [["compose", "config", "--quiet"], ["compose", "up", "--build", "-d", "--wait", "--wait-timeout", "300"]]:
        subprocess.run([docker] + arguments, cwd=ROOT, check=True)
    subprocess.run([sys.executable, str(ROOT / "scripts/verify_container_flow.py"), "--docker", docker], cwd=ROOT, check=True)


if __name__ == "__main__":
    main()
