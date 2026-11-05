"""Try a local trained baseline. Only load trusted project artifacts."""
import argparse
import json

import joblib

from src.data.inspect import ROOT


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("text")
    args = parser.parse_args()
    if not args.text.strip():
        parser.error("Ticket text must not be blank")
    metrics = json.loads((ROOT / "reports/baselines/metrics.json").read_text(encoding="utf-8"))
    artifact = joblib.load(ROOT / f"models/{metrics['selected_model']}.joblib")
    model = artifact["pipeline"]
    probabilities = model.predict_proba([args.text])[0]
    index = probabilities.argmax()
    intent = str(model.classes_[index])
    print(json.dumps({"intent": intent, "category": artifact["intent_to_category"][intent],
                      "score_uncalibrated": float(probabilities[index]), "model": artifact["model_name"]}, indent=2))


if __name__ == "__main__":
    main()
