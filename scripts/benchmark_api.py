"""Measure local ASGI request latency/error handling with the actual saved model."""
from datetime import datetime, timezone
import json
from pathlib import Path
import statistics
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from fastapi.testclient import TestClient
from app.api import create_app


def main():
    cases = {'normal': 'I need to track my refund', 'short': 'help', 'long': 'refund ' * 1300,
             'misspelling': 'i ned to trak my refnd', 'ambiguous': 'I have a problem with my account and payment',
             'multiple_issues': 'Track my refund and change my shipping address',
             'unseen': 'Explain quantum gravity to me'}
    rows, timings = [], []
    with tempfile.TemporaryDirectory() as temporary, TestClient(create_app(Path(temporary) / 'benchmark.sqlite3')) as client:
        client.post('/predict', json={'text': cases['normal']}).raise_for_status()
        for repetition in range(5):
            for name, text in cases.items():
                start = time.perf_counter()
                response = client.post('/predict', json={'text': text})
                elapsed = (time.perf_counter() - start) * 1000
                response.raise_for_status()
                timings.append(elapsed)
                if repetition == 0:
                    result = response.json()
                    rows.append({'case': name, 'http_status': response.status_code, 'predicted_intent': result['prediction']['intent'],
                                 'requires_review': result['requires_review'], 'truncated': result['prediction']['truncated']})
        for name, text in [('empty', ''), ('whitespace', '   '), ('oversized', 'a' * 10001)]:
            response = client.post('/predict', json={'text': text})
            assert response.status_code == 422
            rows.append({'case': name, 'http_status': response.status_code})
    report = {'verified_at': datetime.now(timezone.utc).isoformat(), 'model': 'actual fine-tuned DistilBERT',
              'transport': 'local ASGI TestClient; excludes internet and cold-start latency', 'warm_requests': len(timings),
              'mean_ms': statistics.mean(timings), 'p95_ms': sorted(timings)[int(.95 * (len(timings)-1))],
              'unexpected_error_rate': 0, 'cases': rows,
              'limitation': 'A closed-set classifier can confidently misclassify unseen or multi-issue messages. Review thresholds are provisional, not an OOD detector.'}
    (ROOT / 'reports/api/performance.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps({key:value for key,value in report.items() if key != 'cases'}, indent=2))


if __name__ == '__main__':
    main()
