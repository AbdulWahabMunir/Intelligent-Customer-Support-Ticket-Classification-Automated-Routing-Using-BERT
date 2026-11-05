"""Run local inference with the completed fine-tuned DistilBERT checkpoint."""

import argparse
import json

from src.data.inspect import ROOT


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("text")
    args = parser.parse_args()
    if not args.text.strip():
        parser.error("Ticket text must not be blank")
    metadata = json.loads((ROOT / "models/distilbert/experiment.json").read_text(encoding="utf-8"))
    if metadata["status"] != "training_complete" or metadata["smoke"]:
        raise ValueError("A completed full training run is required")
    import torch
    from transformers import AutoModelForSequenceClassification, AutoTokenizer
    torch.set_num_threads(4)
    path = ROOT / "models/distilbert/final"
    tokenizer = AutoTokenizer.from_pretrained(path, local_files_only=True)
    model = AutoModelForSequenceClassification.from_pretrained(path, local_files_only=True).eval()
    encoded = tokenizer(args.text, return_tensors="pt", truncation=True, max_length=metadata["max_length"])
    with torch.inference_mode():
        probabilities = model(**encoded).logits.softmax(dim=-1)[0]
    index = probabilities.argmax().item()
    intent = model.config.id2label[index]
    print(json.dumps({"intent": intent, "category": metadata["intent_to_category"][intent],
                      "score_uncalibrated": probabilities[index].item(), "model": "distilbert"}, indent=2))


if __name__ == "__main__":
    main()
