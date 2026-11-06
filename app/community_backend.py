"""Manage one loopback FastAPI child for the Streamlit Community Cloud demo."""
import atexit
import os
from pathlib import Path
import subprocess
import sys
import time

import httpx
import psutil

ROOT = Path(__file__).resolve().parents[1]
APPLICATION_RELEASE = '1.1.2'


def stop_backend(process):
    if process.poll() is None:
        process.terminate()
        try:
            process.wait(timeout=15)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)


def start_backend():
    port = int(os.environ.get('SUPPORT_INTERNAL_API_PORT', '8787'))
    if not 1 <= port <= 65535:
        raise ValueError('Invalid internal API port')
    url = f'http://127.0.0.1:{port}'
    child_env = dict(os.environ)
    child_env.update(PORT=str(port), SUPPORT_API_HOST='127.0.0.1', HF_HUB_OFFLINE='1', TOKENIZERS_PARALLELISM='false')
    # A source update can rerun Streamlit without stopping its previous child.
    # Retire only this parent process's API on the same internal port.
    for previous in psutil.Process().children(recursive=False):
        try:
            command = previous.cmdline()
            environment = previous.environ()
            if 'app.run_api' in command and environment.get('PORT') == str(port) and environment.get('SUPPORT_API_HOST') == '127.0.0.1':
                previous.terminate()
                try:
                    previous.wait(timeout=15)
                except psutil.TimeoutExpired:
                    previous.kill()
                    previous.wait(timeout=5)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    # Inherit Cloud stdout/stderr so startup failures reach Manage app logs.
    child_env['PYTHONUNBUFFERED'] = '1'
    process = subprocess.Popen([sys.executable, '-u', '-m', 'app.run_api'], cwd=ROOT, env=child_env,
                               creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    atexit.register(stop_backend, process)
    deadline = time.monotonic() + 300
    with httpx.Client(base_url=url, timeout=50, trust_env=False,
                      headers={'X-API-Key': child_env.get('SUPPORT_API_KEY', '')}) as client:
        while time.monotonic() < deadline:
            if process.poll() is not None:
                raise RuntimeError('Internal FastAPI did not start. Check the server deployment log.')
            try:
                if client.get('/health').status_code == 200 and client.get('/taxonomy').status_code == 200:
                    return process
            except httpx.RequestError:
                pass
            time.sleep(1)
    stop_backend(process)
    raise RuntimeError('Internal FastAPI startup timed out. Check the server deployment log.')
