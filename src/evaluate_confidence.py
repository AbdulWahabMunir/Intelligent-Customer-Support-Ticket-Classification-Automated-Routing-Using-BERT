"""Measure raw score calibration on the fixed test split; never fit on test data."""

import json

import numpy as np
from sklearn.metrics import log_loss

from src.data.inspect import ROOT
from src.inference import TicketClassifier
from src.train_distilbert import verified_splits


def calibration_metrics(truth, probabilities, bins=10):
    probabilities = np.asarray(probabilities, dtype=float)
    truth = np.asarray(truth, dtype=int)
    if probabilities.ndim != 2 or len(truth) == 0 or len(truth) != len(probabilities):
        raise ValueError("Nonempty aligned labels and probability matrix required")
    if not np.isfinite(probabilities).all() or (probabilities < 0).any() or (probabilities > 1).any():
        raise ValueError("Probabilities must be finite and in [0, 1]")
    if not np.allclose(probabilities.sum(axis=1), 1, atol=1e-5):
        raise ValueError("Probability rows must sum to one")
    if (truth < 0).any() or (truth >= probabilities.shape[1]).any():
        raise ValueError("Label index outside class range")
    # Softmax is float32: remove only roundoff after validating row sums above.
    probabilities = probabilities / probabilities.sum(axis=1, keepdims=True)
    scores = probabilities.max(axis=1)
    correct = probabilities.argmax(axis=1) == truth
    one_hot = np.eye(probabilities.shape[1])[truth]
    assignments = np.minimum((scores * bins).astype(int), bins - 1)
    rows = []
    ece = 0.0
    for index in range(bins):
        mask = assignments == index
        count = int(mask.sum())
        accuracy = float(correct[mask].mean()) if count else None
        score = float(scores[mask].mean()) if count else None
        if count:
            ece += count / len(truth) * abs(accuracy - score)
        rows.append({"lower": index / bins, "upper": (index + 1) / bins, "count": count,
                     "accuracy": accuracy, "mean_score": score})
    return {"samples": len(truth), "accuracy": float(correct.mean()), "mean_top_score": float(scores.mean()),
            "ece_10_bins": ece, "multiclass_brier_sum": float(((probabilities - one_hot) ** 2).sum(axis=1).mean()),
            "log_loss": float(log_loss(truth, probabilities, labels=list(range(probabilities.shape[1])))),
            "score_below_0_8_rate": float((scores < 0.8).mean()), "reliability_bins": rows}


def main():
    splits, manifest = verified_splits(["test"])
    texts = [row["instruction"] for row in splits["test"]]
    report = {"scope": "Raw test-split diagnostics; no calibration fitting or threshold tuning", "test_sha256": manifest["splits"]["test"]["sha256"], "models": {}}
    for name in ["logistic_regression", "distilbert"]:
        classifier = TicketClassifier(name)
        if name == "logistic_regression":
            labels = classifier.model.classes_.tolist()
            probabilities = classifier.model.predict_proba(texts)
        else:
            import torch
            labels = [classifier.model.config.id2label[i] for i in range(classifier.model.config.num_labels)]
            batches = []
            for offset in range(0, len(texts), 16):
                encoded = classifier.tokenizer(texts[offset:offset + 16], return_tensors="pt", padding=True,
                                               truncation=True, max_length=classifier.max_length)
                with torch.inference_mode():
                    batches.append(classifier.model(**encoded).logits.softmax(dim=-1).numpy())
            probabilities = np.concatenate(batches)
        label2id = {label: index for index, label in enumerate(labels)}
        truth = [label2id[row["intent"]] for row in splits["test"]]
        metrics = calibration_metrics(truth, probabilities)
        metrics["model_version"] = classifier.version
        report["models"][name] = metrics
        print(name, {key: metrics[key] for key in ["accuracy", "ece_10_bins", "multiclass_brier_sum", "score_below_0_8_rate"]}, flush=True)
    destination = ROOT / "reports/confidence"
    destination.mkdir(exist_ok=True)
    (destination / "metrics.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    lines = ["# Raw model score diagnostics", "", "Measured on the fixed synthetic Bitext test split. No score transformation, calibration fitting or threshold selection was performed.", "",
             "| Model | Accuracy | ECE (10 bins) | Brier sum | Log loss | Score < 0.8 |", "| --- | ---: | ---: | ---: | ---: | ---: |"]
    for name, item in report["models"].items():
        lines.append(f"| {name} | {item['accuracy']:.4f} | {item['ece_10_bins']:.4f} | {item['multiclass_brier_sum']:.4f} | {item['log_loss']:.4f} | {item['score_below_0_8_rate']:.4f} |")
    lines += ["", "ECE is the support-weighted absolute gap between top-score averages and empirical accuracy in ten equal-width bins. Brier sum is the mean sum of squared probability errors over all classes (not divided by class count). Empty bins have null accuracy and score. These measures depend on the test distribution and do not establish calibration for real tickets or out-of-domain inputs.", "", "Raw scores stay marked uncalibrated in the API. Proper post-hoc calibration would need fitting on validation data and an untouched evaluation protocol; that is a future experiment."]
    (destination / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
