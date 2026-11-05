"""Train fixed baseline configurations; select by validation macro F1 only."""

import csv
import hashlib
import json
import platform
import time
import warnings

import joblib
import numpy as np
import sklearn
from sklearn.exceptions import ConvergenceWarning
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix, f1_score
from sklearn.naive_bayes import MultinomialNB
from sklearn.pipeline import Pipeline

from src.data.inspect import ROOT
from src.data.prepare import assert_disjoint, read_split


def make_pipeline(classifier):
    # The vectorizer is fitted inside the pipeline on training messages only.
    return Pipeline([("tfidf", TfidfVectorizer(ngram_range=(1, 2), min_df=2, sublinear_tf=True)),
                     ("classifier", classifier)])


def score(model, rows, mapping):
    text = [row["instruction"] for row in rows]
    truth = [row["intent"] for row in rows]
    prediction = model.predict(text).tolist()
    result = {"accuracy": accuracy_score(truth, prediction),
              "macro_f1": f1_score(truth, prediction, average="macro"),
              "weighted_f1": f1_score(truth, prediction, average="weighted"),
              "category_accuracy": accuracy_score([row["category"] for row in rows], [mapping[p] for p in prediction]),
              "per_class": classification_report(truth, prediction, output_dict=True, zero_division=0)}
    return result, prediction


def main():
    splits = {name: read_split(name) for name in ["train", "validation", "test"]}
    assert_disjoint(splits)
    manifest = json.loads((ROOT / "data/processed/manifest.json").read_text(encoding="utf-8"))
    for name in splits:
        digest = hashlib.sha256((ROOT / f"data/processed/{name}.csv").read_bytes()).hexdigest()
        if digest != manifest["splits"][name]["sha256"]:
            raise ValueError(f"Split hash mismatch: {name}")
    train = splits["train"]
    mapping = {}
    for row in train:
        if row["intent"] in mapping and mapping[row["intent"]] != row["category"]:
            raise ValueError("Intent maps to multiple categories")
        mapping[row["intent"]] = row["category"]
    classifiers = {"logistic_regression": LogisticRegression(max_iter=1000, random_state=42),
                   "naive_bayes": MultinomialNB(alpha=1.0)}
    results = {"python": platform.python_version(), "sklearn": sklearn.__version__,
               "selection": "validation macro F1; fixed configurations, no hyperparameter search", "models": {}}
    fitted = {}
    for name, classifier in classifiers.items():
        model = make_pipeline(classifier)
        start = time.perf_counter()
        with warnings.catch_warnings():
            warnings.simplefilter("error", ConvergenceWarning)
            model.fit([row["instruction"] for row in train], [row["intent"] for row in train])
        elapsed = time.perf_counter() - start
        validation, _ = score(model, splits["validation"], mapping)
        results["models"][name] = {"fit_seconds": elapsed, "validation": validation}
        fitted[name] = model
        print(f"{name}: validation macro F1={validation['macro_f1']:.4f}, fit={elapsed:.2f}s", flush=True)
    selected = max(fitted, key=lambda name: results["models"][name]["validation"]["macro_f1"])
    results["selected_model"] = selected
    # Test results are computed only after selection is fixed.
    report_dir = ROOT / "reports/baselines"
    report_dir.mkdir(parents=True, exist_ok=True)
    for name, model in fitted.items():
        test, predictions = score(model, splits["test"], mapping)
        results["models"][name]["test"] = test
        labels = model.classes_.tolist()
        matrix = confusion_matrix([r["intent"] for r in splits["test"]], predictions, labels=labels)
        with (report_dir / f"{name}_confusion.csv").open("w", encoding="utf-8", newline="") as output:
            writer = csv.writer(output)
            writer.writerow(["actual / predicted"] + labels)
            writer.writerows([[label] + counts.tolist() for label, counts in zip(labels, matrix)])
        # Preserve errors locally without publishing raw messages in aggregate reports.
        errors = [{"instruction": row["instruction"], "actual": row["intent"], "predicted": pred}
                  for row, pred in zip(splits["test"], predictions) if row["intent"] != pred]
        (ROOT / f"data/predictions/{name}_errors.json").write_text(json.dumps(errors, indent=2), encoding="utf-8")
        joblib.dump({"pipeline": model, "intent_to_category": mapping, "model_name": name,
                     "sklearn_version": sklearn.__version__, "data_manifest": manifest}, ROOT / f"models/{name}.joblib")
    model = fitted[selected]
    model.predict([splits["test"][0]["instruction"]])  # Warm up.
    timings = []
    for row in splits["test"][:200]:
        start = time.perf_counter()
        model.predict([row["instruction"]])
        timings.append((time.perf_counter() - start) * 1000)
    results["selected_latency_ms"] = {"samples": len(timings), "mean": float(np.mean(timings)), "p95": float(np.percentile(timings, 95)), "scope": "warm local single-message pipeline inference"}
    (report_dir / "metrics.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
    lines = ["# Baseline comparison", "", "Selection: validation macro F1, before examining test results.", "",
             "| Model | Validation macro F1 | Test accuracy | Test macro F1 | Test weighted F1 |", "| --- | ---: | ---: | ---: | ---: |"]
    for name, result in results["models"].items():
        t = result["test"]
        lines.append(f"| {name} | {result['validation']['macro_f1']:.4f} | {t['accuracy']:.4f} | {t['macro_f1']:.4f} | {t['weighted_f1']:.4f} |")
    lines += ["", f"Selected model: **{selected}**.", "", "Both models use word unigram/bigram TF-IDF fitted on training messages only. Category is derived from the training intent-to-category map. Per-class precision/recall/F1 and category accuracy are in metrics.json; confusion matrices have actual labels in rows and predicted labels in columns.", "", "These scores describe a deduplicated random split of synthetic Bitext data. Shared templates and paraphrases may inflate scores; real customer performance and linguistic robustness are not established. Confidence calibration has not been evaluated. Do not tune against the test results."]
    (report_dir / "comparison.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Selected {selected}; reports saved to {report_dir}")


if __name__ == "__main__":
    main()
