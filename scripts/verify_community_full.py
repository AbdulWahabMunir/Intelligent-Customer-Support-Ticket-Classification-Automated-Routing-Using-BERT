"""Local integration check of Community Cloud process layout against Neon."""
import json
import os
from pathlib import Path
import sys
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import httpx
from streamlit.testing.v1 import AppTest
from app.community_backend import start_backend, stop_backend


def main():
    database_url = ROOT.joinpath('.env').read_text(encoding='utf-8-sig').strip().split('=', 1)[1]
    settings = json.loads(ROOT.joinpath('data/runtime/deployment-secrets.json').read_text())
    settings.update(DATABASE_URL=database_url,
                    MODEL_BUNDLE_URL='https://github.com/AbdulWahabMunir/Intelligent-Customer-Support-Ticket-Classification-Automated-Routing-Using-BERT/releases/download/v1.0.0/model-bundle.zip',
                    MODEL_BUNDLE_SHA256='0e9a4050e81883d274dc3e9f25f0c65badaae62b4a8738af924e0f0846c55fcc')
    os.environ.update({key: settings[key] for key in ['DATABASE_URL', 'SUPPORT_API_KEY']})
    os.environ['SUPPORT_MODELS_PATH'] = str(ROOT / 'models')
    os.environ.pop('MODEL_BUNDLE_URL', None)
    process = start_backend()
    try:
        with httpx.Client(base_url='http://127.0.0.1:8787', timeout=60, trust_env=False) as client:
            assert client.get('/analytics').status_code == 401
            client.headers['X-API-Key'] = settings['SUPPORT_API_KEY']
            health = client.get('/health').json()
            response = client.post('/tickets', json={'text': 'I need to track my refund'})
            response.raise_for_status()
            ticket = response.json()
            assert ticket['result']['prediction']['intent'] == 'track_refund'
            response = client.post(f"/tickets/{ticket['id']}/feedback", json={'corrected_intent': 'track_refund', 'note': 'Deployment verification: synthetic example'})
            response.raise_for_status()
        with patch('app.community_backend.start_backend', return_value=process):
            app = AppTest.from_file(str(ROOT / 'community_full/streamlit_app.py'))
            app.secrets = settings
            app.run(timeout=30)
            assert not app.exception
            app.text_input[0].set_value(settings['SUPPORT_DASHBOARD_PASSWORD'])
            next(button for button in app.button if button.label == 'Sign in').click().run(timeout=60)
            assert not app.exception
            assert not app.error, [error.value for error in app.error]
            assert app.metric
        stop_backend(process)
        os.environ.pop('MODEL_BUNDLE_URL', None)
        process = start_backend()
        with httpx.Client(base_url='http://127.0.0.1:8787', headers={'X-API-Key': settings['SUPPORT_API_KEY']}, timeout=60, trust_env=False) as client:
            restored = client.get(f"/tickets/{ticket['id']}").json()
            assert restored['result'] == ticket['result']
            assert restored['feedback_count'] == 1
        report = {'status': 'passed', 'model_version': health['model_version'], 'database': 'live Neon PostgreSQL',
                  'runtime': 'local Streamlit plus internal FastAPI process', 'cloud_deployment': 'not yet performed',
                  'checks': ['API authentication', 'actual DistilBERT prediction', 'Neon feedback persistence',
                             'Streamlit login and dashboard widgets', 'API restart persistence']}
        ROOT.joinpath('reports/deployment/community-full-verification.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
        print(json.dumps(report, indent=2))
    finally:
        stop_backend(process)


if __name__ == '__main__':
    main()
