"""Separate 77-intent baseline experiment; never changes the deployed taxonomy."""
import csv
import hashlib
import json
from pathlib import Path
import time
from urllib.request import urlretrieve

import joblib
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, classification_report, f1_score
from sklearn.model_selection import train_test_split
from sklearn.naive_bayes import MultinomialNB

from src.data.inspect import ROOT, normalize_key
from src.train_baselines import make_pipeline

REVISION = '57ec275d8078af65b7731c2a98be812d844a6d6b'


def evaluate(model, rows):
    truth = [row['category'] for row in rows]
    predictions = model.predict([row['text'] for row in rows])
    return {'accuracy': accuracy_score(truth, predictions), 'macro_f1': f1_score(truth, predictions, average='macro'),
            'weighted_f1': f1_score(truth, predictions, average='weighted'),
            'per_class': classification_report(truth, predictions, output_dict=True, zero_division=0)}


def main():
    directory = ROOT / 'data/raw/banking77'
    directory.mkdir(parents=True, exist_ok=True)
    hashes = {}
    for filename in ['train.csv', 'test.csv', 'categories.json']:
        path = directory / filename
        if not path.exists():
            urlretrieve(f'https://raw.githubusercontent.com/PolyAI-LDN/task-specific-datasets/{REVISION}/banking_data/{filename}', path)
        hashes[filename] = hashlib.sha256(path.read_bytes()).hexdigest()
    def read(name):
        with (directory / name).open(encoding='utf-8', newline='') as source:
            return list(csv.DictReader(source))
    original_train, test = read('train.csv'), read('test.csv')
    test_keys = {normalize_key(row['text']) for row in test}
    seen, train, removed = {}, [], 0
    for row in original_train:
        key = normalize_key(row['text'])
        if key in seen and seen[key] != row['category']:
            raise ValueError('Conflicting normalized training label')
        if key in seen or key in test_keys:
            removed += 1
            continue
        seen[key] = row['category']
        train.append(row)
    train, validation = train_test_split(train, test_size=.15, random_state=42, stratify=[row['category'] for row in train])
    assert not ({normalize_key(row['text']) for row in train} & {normalize_key(row['text']) for row in validation})
    report = {'dataset': 'BANKING77', 'source': 'https://github.com/PolyAI-LDN/task-specific-datasets/tree/' + REVISION + '/banking_data',
              'license': 'CC BY 4.0; credit PolyAI and Casanueva et al. (2020), arXiv:2003.04807', 'revision': REVISION,
              'sha256': hashes, 'seed': 42, 'original_train': len(original_train), 'removed_training_duplicates_or_test_overlap': removed,
              'train': len(train), 'validation': len(validation), 'official_test': len(test), 'intents': len(seen and {row['category'] for row in train}),
              'selection': 'Fixed configurations, validation macro F1; official test evaluated after selection', 'models': {}}
    fitted = {}
    for name, estimator in [('naive_bayes', MultinomialNB()), ('logistic_regression', LogisticRegression(max_iter=1000, random_state=42))]:
        model = make_pipeline(estimator)
        start = time.perf_counter()
        model.fit([row['text'] for row in train], [row['category'] for row in train])
        fitted[name] = model
        report['models'][name] = {'fit_seconds': time.perf_counter() - start, 'validation': evaluate(model, validation)}
        print(name + ' fitted', flush=True)
    report['selected_model'] = max(fitted, key=lambda name: report['models'][name]['validation']['macro_f1'])
    for name, model in fitted.items():
        report['models'][name]['test'] = evaluate(model, test)
    destination = ROOT / 'reports/banking77'
    destination.mkdir(parents=True, exist_ok=True)
    (destination / 'metrics.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    model_dir = ROOT / 'models/banking77'
    model_dir.mkdir(parents=True, exist_ok=True)
    joblib.dump(fitted[report['selected_model']], model_dir / 'baseline.joblib')
    lines = ['# BANKING77 additional experiment', '', 'A separate 77-intent banking-domain experiment. This does not evaluate the Bitext classifier on incompatible labels, fine-tune a second transformer, or change the deployed 27-intent model.', '', '| Model | Test accuracy | Macro F1 | Weighted F1 |', '|---|---:|---:|---:|']
    for name, row in report['models'].items():
        metrics = row['test']
        lines.append(f"| {name} | {metrics['accuracy']:.4f} | {metrics['macro_f1']:.4f} | {metrics['weighted_f1']:.4f} |")
    lines += ['', f"Training/validation/official test rows: {len(train)}/{len(validation)}/{len(test)}. Removed {removed} normalized duplicate/overlap training rows. TF-IDF fits training text only. Selected by validation macro F1 with seed 42; no test-set tuning.", '', f"Source: {report['source']}. Attribution: PolyAI, Casanueva et al., Efficient Intent Detection with Dual Sentence Encoders (2020), https://arxiv.org/abs/2003.04807. Dataset license: CC BY 4.0. Raw examples are excluded from Git."]
    (destination / 'report.md').write_text('\n'.join(lines), encoding='utf-8')
    print('BANKING77 experiment complete')


if __name__ == '__main__':
    main()
