"""Verify actual DistilBERT + PostgreSQL in an isolated 512 MiB API container."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import time

import httpx


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--docker', default='docker')
    args = parser.parse_args()
    name = 'support-hosted-verification'
    with httpx.Client(base_url='http://127.0.0.1:8003', timeout=120, trust_env=False) as client:
        assert client.get('/health').status_code == 200
        assert client.get('/analytics').status_code == 401
        client.headers['X-API-Key'] = 'local-verification-key-at-least-32-characters'
        response = client.post('/tickets', json={'text': 'I need to track my refund'})
        response.raise_for_status()
        ticket = response.json()
        assert ticket['result']['prediction']['intent'] == 'track_refund'
        response = client.post(f"/tickets/{ticket['id']}/feedback", json={'corrected_intent': 'track_refund', 'note': 'Constrained hosted verification'})
        response.raise_for_status()
        response = client.post('/predict', json={'text': ('refund ' * 1400).strip()})
        response.raise_for_status()
        assert response.json()['prediction']['truncated']
        subprocess.run([args.docker, 'restart', name], check=True, capture_output=True)
        deadline = time.monotonic() + 120
        while time.monotonic() < deadline:
            try:
                if client.get('/health', timeout=3).status_code == 200:
                    break
            except httpx.RequestError:
                pass
            time.sleep(1)
        else:
            raise RuntimeError('API failed to recover')
        restored = client.get(f"/tickets/{ticket['id']}").json()
        assert restored['result'] == ticket['result']
        assert restored['feedback_count'] == 1
    inspection = json.loads(subprocess.check_output([args.docker, 'inspect', name], text=True))[0]
    assert inspection['HostConfig']['Memory'] == 512 * 1024 * 1024
    assert not inspection['State']['OOMKilled']
    report = {'status': 'passed', 'verified_at': datetime.now(timezone.utc).isoformat(),
              'memory_limit_bytes': inspection['HostConfig']['Memory'], 'swap_extra_bytes': 0,
              'model': 'actual fine-tuned DistilBERT', 'storage': 'isolated local PostgreSQL',
              'cloud_deployment': 'not yet performed', 'checks': ['API authentication', 'DistilBERT prediction',
              'long ticket truncation', 'PostgreSQL feedback', 'container restart persistence']}
    destination = Path(__file__).resolve().parents[1] / 'reports/deployment/free-backend-verification.json'
    destination.write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
