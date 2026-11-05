"""Quantify template-similarity risk without changing model selection or splits."""
import json
import random

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.neighbors import NearestNeighbors

from src.data.inspect import ROOT
from src.data.prepare import read_split


def main():
    train, test = read_split('train'), read_split('test')
    sample = random.Random(42).sample(test, min(1000, len(test)))
    vectorizer = TfidfVectorizer(analyzer='char_wb', ngram_range=(3, 5), min_df=2, max_features=80000, dtype=np.float32)
    training = vectorizer.fit_transform([row['instruction'] for row in train])
    neighbors = NearestNeighbors(n_neighbors=1, metric='cosine', algorithm='brute', n_jobs=1).fit(training)
    similarities = []
    for start in range(0, len(sample), 32):
        queries = vectorizer.transform([row['instruction'] for row in sample[start:start+32]])
        distances, _ = neighbors.kneighbors(queries)
        similarities.extend((1 - distances[:, 0]).tolist())
    report = {'seed': 42, 'test_sample': len(sample), 'training_rows': len(train),
              'method': 'Training-only TF-IDF char_wb 3-5 grams; nearest training cosine for seeded test sample',
              'mean_nearest_cosine': float(np.mean(similarities)),
              'at_least_0_90': sum(value >= .90 for value in similarities),
              'at_least_0_95': sum(value >= .95 for value in similarities),
              'at_least_0_99': sum(value >= .99 for value in similarities),
              'limitation': 'Similarity audit, not proof of independent templates. Original random-split scores can be optimistic. No threshold was selected to improve model scores, and no retraining was done.'}
    (ROOT / 'reports/similarity_audit.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
