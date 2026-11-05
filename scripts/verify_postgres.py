"""Verify the hosted storage contract against an isolated PostgreSQL database."""
import json
import os
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from fastapi.testclient import TestClient
from app.api import create_app
from src.inference import Prediction
from src.routing import TicketService


class Classifier:
    mapping = {'track_refund': 'REFUND'}
    version = 'postgres-verification:v1'

    def predict(self, text):
        return Prediction('track_refund', 'REFUND', .99, .95, self.version)


def main():
    if not os.environ.get('DATABASE_URL'):
        raise RuntimeError('Set DATABASE_URL to an isolated verification database')
    service = TicketService(Classifier())
    with TestClient(create_app(service=service)) as client:
        before = client.get('/analytics').json()['tickets']
        response = client.post('/tickets', json={'text': 'Where is my refund?'})
        response.raise_for_status()
        ticket = response.json()
        response = client.post(f"/tickets/{ticket['id']}/feedback", json={'corrected_intent': 'track_refund', 'note': 'PostgreSQL verification'})
        response.raise_for_status()
        assert client.get('/analytics').json()['tickets'] == before + 1
        assert client.get('/tickets', params={'needs_review': False}).json()['total'] >= 1
        assert client.get('/tickets', params={'needs_review': True}).json()['total'] == 0
    with TestClient(create_app(service=service)) as client:
        saved = client.get(f"/tickets/{ticket['id']}").json()
        assert saved['result'] == ticket['result']
        assert saved['feedback_count'] == 1
        assert len(client.get(f"/tickets/{ticket['id']}/feedback").json()) == 1
        assert client.get('/analytics').json()['feedback_entries'] >= 1
    report = {'status': 'passed', 'checks': ['PostgreSQL ticket storage', 'append-only feedback', 'analytics', 'review filtering', 'application restart persistence'], 'model': 'fixture (storage-only verification)'}
    (Path(__file__).resolve().parents[1] / 'reports/deployment/postgres-verification.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps(report))


if __name__ == '__main__':
    main()
