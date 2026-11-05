"""Observe the deployed UI in isolated headless Edge without logging credentials."""
import argparse
import base64
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import time
from urllib.request import urlopen

from websockets.sync.client import connect

ROOT = Path(__file__).resolve().parents[1]
URL = 'https://aw-intelligent-customer-support.streamlit.app'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--updated', action='store_true')
    args = parser.parse_args()
    password = json.loads((ROOT / 'data/runtime/deployment-secrets.json').read_text())['SUPPORT_DASHBOARD_PASSWORD']
    edge = Path(r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe')
    port = 9226 if args.updated else 9225
    profile = ROOT / ('artifacts/edge-live-after-profile' if args.updated else 'artifacts/edge-live-before-profile')
    process = subprocess.Popen([str(edge), '--headless', '--disable-gpu', '--no-first-run',
                 f'--user-data-dir={profile}', f'--remote-debugging-port={port}', '--window-size=1440,1100', URL],
                 stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=subprocess.CREATE_NO_WINDOW)
    try:
        deadline = time.monotonic() + 180
        pages = []
        while time.monotonic() < deadline:
            try:
                with urlopen(f'http://127.0.0.1:{port}/json/list', timeout=2) as response:
                    pages = [page for page in json.load(response) if page.get('type') == 'page' and page.get('url', '').startswith(URL)]
                if pages:
                    break
            except OSError:
                pass
            time.sleep(.5)
        if not pages:
            raise RuntimeError('Live verification browser did not start')
        with connect(pages[0]['webSocketDebuggerUrl'], open_timeout=10) as socket:
            counter = 0
            def command(method, parameters=None):
                nonlocal counter
                counter += 1
                socket.send(json.dumps({'id': counter, 'method': method, 'params': parameters or {}}))
                while True:
                    response = json.loads(socket.recv(timeout=20))
                    if response.get('id') == counter:
                        if 'error' in response:
                            raise RuntimeError('Browser command failed')
                        return response['result']
            def evaluate(expression):
                wrapped = '((document)=>(' + expression + '))(window.document.querySelector(\'iframe[src*="/~/+/"]\')?.contentDocument || window.document)'
                return command('Runtime.evaluate', {'expression': wrapped, 'returnByValue': True}).get('result', {}).get('value')
            def wait_text(expected):
                deadline = time.monotonic() + 180
                while time.monotonic() < deadline:
                    body = evaluate('document.body.innerText') or ''
                    if expected in body:
                        return body
                    time.sleep(1)
                raise RuntimeError('Live UI did not reach expected state: ' + expected)
            command('Page.enable')
            command('Emulation.setDeviceMetricsOverride', {'width': 1440, 'height': 1100, 'deviceScaleFactor': 1, 'mobile': False})
            wait_text('Workspace password')
            evaluate("document.querySelector('input[type=password]').focus()")
            command('Input.insertText', {'text': password})
            evaluate("Array.from(document.querySelectorAll('button')).find(b=>b.innerText.trim()==='Sign in').click()")
            wait_text('Support overview')
            wait_text('API connected')
            if args.updated:
                evaluate("Array.from(document.querySelectorAll('summary')).find(b=>b.innerText.includes('Workspace details')).click()")
                wait_text('Application: 1.1.0')
            time.sleep(2)
            prefix = 'live-updated' if args.updated else 'live'
            screenshots = ROOT / 'reports/screenshots'
            screenshots.mkdir(exist_ok=True)
            capture = command('Page.captureScreenshot', {'format': 'png', 'captureBeyondViewport': False})
            (screenshots / (prefix + '-overview.png')).write_bytes(base64.b64decode(capture['data']))
            evaluate("Array.from(document.querySelectorAll('label')).find(b=>b.innerText.trim()==='Ticket review').click()")
            wait_text('Inspect the original prediction')
            if args.updated:
                wait_text('Search messages')
            # Awaiting-review is initially empty; select All tickets with keyboard.
            comboboxes = evaluate("document.querySelectorAll('input[role=combobox]').length")
            if comboboxes:
                evaluate("document.querySelector('input[role=combobox]').focus()")
                command('Input.insertText', {'text': 'All tickets'})
                command('Input.dispatchKeyEvent', {'type': 'keyDown', 'key': 'Enter', 'code': 'Enter'})
                command('Input.dispatchKeyEvent', {'type': 'keyUp', 'key': 'Enter', 'code': 'Enter'})
            body = wait_text('a623e207')
            assert 'Reviewed' in body and 'Track Refund' in body
            time.sleep(2)
            capture = command('Page.captureScreenshot', {'format': 'png', 'captureBeyondViewport': False})
            (screenshots / (prefix + '-review.png')).write_bytes(base64.b64decode(capture['data']))
            report = {'url': URL, 'verified_at': datetime.now(timezone.utc).isoformat(), 'status': 'passed',
                      'application_version': '1.1.0' if args.updated else '1.0.0',
                      'checks': ['public Streamlit login', 'API connected', 'overview renders',
                                 'previous cloud ticket a623e207 retained', 'reviewed status retained'],
                      'method': 'isolated headless Edge DOM observations and screenshots'}
            if args.updated:
                report['checks'] += ['new filter UI visible', 'updated FastAPI version confirmed after child replacement']
            path = ROOT / 'reports/deployment' / (prefix + '-verification.json')
            path.write_text(json.dumps(report, indent=2), encoding='utf-8')
            print(json.dumps(report, indent=2))
    finally:
        process.terminate()
        process.wait(timeout=15)


if __name__ == '__main__':
    main()
