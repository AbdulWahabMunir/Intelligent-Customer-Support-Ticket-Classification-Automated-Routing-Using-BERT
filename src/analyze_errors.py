"""Summarize baseline confusion patterns without publishing customer text."""

from collections import Counter
import json

import joblib

from src.data.inspect import ROOT
from src.data.prepare import read_split
from src.train_distilbert import verified_splits


def main():
    name = "logistic_regression"
    artifact = joblib.load(ROOT / f"models/{name}.joblib")
    _, manifest = verified_splits(["train", "validation", "test"])
    if artifact["data_manifest"] != manifest:
        raise ValueError("Baseline model and current splits have different provenance")
    summaries = {}
    for split in ["validation", "test"]:
        rows = read_split(split)
        predicted = artifact["pipeline"].predict([r["instruction"] for r in rows])
        errors = [{"instruction": r["instruction"], "actual": r["intent"], "predicted": str(p)}
                  for r, p in zip(rows, predicted) if r["intent"] != p]
        pairs = Counter((r["actual"], r["predicted"]) for r in errors)
        summaries[split] = {"rows": len(rows), "errors": len(errors),
                            "pairs": [{"actual": a, "predicted": p, "count": count}
                                      for (a, p), count in pairs.most_common()]}
        (ROOT / f"data/predictions/{name}_{split}_errors.json").write_text(json.dumps(errors, indent=2), encoding="utf-8")
    target = ROOT / "reports/baselines"
    (target / "error_analysis.json").write_text(json.dumps(summaries, indent=2), encoding="utf-8")
    lines = ["# Baseline error analysis", "", "Validation errors guide analysis. Test errors are descriptive only; do not use them to tune models or author evaluation examples.", ""]
    for split, summary in summaries.items():
        lines += [f"## {split.title()}: {summary['errors']} errors / {summary['rows']} messages", "",
                  "| Actual intent | Predicted intent | Count |", "| --- | --- | ---: |"]
        lines += [f"| {p['actual']} | {p['predicted']} | {p['count']} |" for p in summary["pairs"][:10]]
        lines.append("")
    lines += ["## Interpretation", "", "Manual inspection of validation errors found misspellings (such as cancle and dfownload), joined words (such as trackorder), and related-intent ambiguity (registration problems versus account creation, invoice retrieval versus invoice checking). Some short messages lack enough context to establish a unique intent. These are qualitative observations, not mutually exclusive or quantified linguistic annotations. No automatic spelling fixes or relabeling are applied.", "", "The DistilBERT experiment retains the same split and a fixed configuration. Its outcome is unknown until training and held-out evaluation finish. A separate human-reviewed robustness set remains future work."]
    (target / "error_analysis.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({k: {"rows": v["rows"], "errors": v["errors"]} for k, v in summaries.items()}, indent=2))


if __name__ == "__main__":
    main()
