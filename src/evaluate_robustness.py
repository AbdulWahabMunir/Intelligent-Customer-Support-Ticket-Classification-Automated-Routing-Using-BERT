"""Evaluate fixed paired challenge cases without training or tuning a model."""

import argparse
from collections import defaultdict
import hashlib
import json

from sklearn.metrics import accuracy_score, f1_score

from src.data.inspect import ROOT, normalize_key
from src.data.prepare import read_split
from src.inference import TicketClassifier


def validate_cases(cases, allowed_intents):
    if not cases:
        raise ValueError("No challenge cases selected")
    seen = set()
    groups = defaultdict(dict)
    for case in cases:
        if case["id"] in seen:
            raise ValueError("Duplicate challenge ID")
        seen.add(case["id"])
        if case["intent"] not in allowed_intents or not case["text"].strip():
            raise ValueError("Unknown intent or blank challenge text")
        if case["review_status"] not in {"draft", "approved"}:
            raise ValueError("Invalid review status")
        group = groups[case["group"]]
        if case["condition"] in group:
            raise ValueError("Duplicate condition within challenge group")
        group[case["condition"]] = case
    for group in groups.values():
        if set(group) != {"anchor", "paraphrase", "spelling_swap", "polite_wrapper"} or len({case["intent"] for case in group.values()}) != 1:
            raise ValueError("Each group needs all four paired conditions and a consistent expected intent")
    return groups


def summarize(cases, predictions):
    if len(cases) != len(predictions):
        raise ValueError("Prediction count mismatch")
    grouped = defaultdict(list)
    anchors = {case["group"]: predicted for case, predicted in zip(cases, predictions) if case["condition"] == "anchor"}
    anchor_truth = {case["group"]: case["intent"] for case in cases if case["condition"] == "anchor"}
    for case, prediction in zip(cases, predictions):
        grouped[case["condition"]].append((case, prediction))
    metrics = {}
    for condition, pairs in sorted(grouped.items()):
        truth = [case["intent"] for case, _ in pairs]
        guessed = [predicted for _, predicted in pairs]
        eligible = [(case, predicted) for case, predicted in pairs if anchors[case["group"]] == anchor_truth[case["group"]]]
        metrics[condition] = {"cases": len(pairs), "accuracy": accuracy_score(truth, guessed),
            "macro_f1": f1_score(truth, guessed, labels=sorted(set(truth)), average="macro", zero_division=0),
            "prediction_consistency_with_anchor": sum(predicted == anchors[case["group"]] for case, predicted in pairs) / len(pairs),
            "correct_anchor_cases": len(eligible),
            "accuracy_when_anchor_correct": sum(predicted == case["intent"] for case, predicted in eligible) / len(eligible) if eligible else None}
    anchor_accuracy = metrics["anchor"]["accuracy"]
    for row in metrics.values():
        row["accuracy_drop_from_anchor_pp"] = (anchor_accuracy - row["accuracy"]) * 100
    return metrics


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--approved-only", action="store_true")
    args = parser.parse_args()
    path = ROOT / "data/robustness/pilot.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    cases = payload["cases"]
    if args.approved_only:
        cases = [case for case in cases if case["review_status"] == "approved"]
    taxonomy = json.loads((ROOT / "config/routing.json").read_text(encoding="utf-8"))["intents"]
    validate_cases(cases, taxonomy)
    # Quantify exact normalized overlap; absence does not rule out shared templates.
    existing = {normalize_key(row["instruction"]) for split in ["train", "validation", "test"] for row in read_split(split)}
    overlaps = sum(normalize_key(case["text"]) in existing for case in cases)
    destination = ROOT / ("reports/robustness-approved" if args.approved_only else "reports/robustness-pilot")
    destination.mkdir(exist_ok=True)
    report = {"set_sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "cases": len(cases),
              "draft_cases": sum(case["review_status"] == "draft" for case in cases), "exact_overlap_with_dataset": overlaps,
              "interpretation": "Diagnostic pilot; draft labels are not human-approved ground truth", "models": {}}
    details = []
    for name in ["logistic_regression", "distilbert"]:
        classifier = TicketClassifier(name)
        predictions = []
        for case in cases:
            prediction = classifier.predict(case["text"])
            predictions.append(prediction.intent)
            details.append({"case_id": case["id"], "model": name, "expected": case["intent"],
                            "predicted": prediction.intent, "score_uncalibrated": prediction.score,
                            "correct": prediction.intent == case["intent"]})
        report["models"][name] = {"model_version": classifier.version, "conditions": summarize(cases, predictions)}
        print(f"{name}: {json.dumps(report['models'][name]['conditions'])}", flush=True)
    (destination / "metrics.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    (destination / "predictions.json").write_text(json.dumps(details, indent=2), encoding="utf-8")
    lines = ["# Linguistic robustness pilot", "", f"{len(cases)} cases; {report['draft_cases']} draft labels; {overlaps} exact normalized overlaps with existing dataset messages.",
             "", "This small agent-authored set is a diagnostic, not a human-approved independent benchmark. Shared templates and ambiguous expected labels can affect these results. No retraining or tuning was performed.", "",
             "| Model | Condition | Accuracy | Macro F1 | Change from anchor (pp) | Anchor consistency |", "| --- | --- | ---: | ---: | ---: | ---: |"]
    for name, result in report["models"].items():
        for condition, metrics in result["conditions"].items():
            lines.append(f"| {name} | {condition} | {metrics['accuracy']:.3f} | {metrics['macro_f1']:.3f} | {metrics['accuracy_drop_from_anchor_pp']:.2f} | {metrics['prediction_consistency_with_anchor']:.3f} |")
    lines += ["", "Positive change values indicate degradation from anchor accuracy. Prediction consistency can remain high even when the anchor is wrong; metrics.json also records accuracy conditional on a correctly predicted anchor.",
              "", "Before research claims: have a human review label correctness and intent preservation, expand coverage with independent sources and contrastive/negation examples, and use --approved-only. Human approval requires complete groups with an approved anchor. Do not edit examples to increase model scores."]
    (destination / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
