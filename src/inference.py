"""Load a model once and expose predictions independently of routing policy."""

from dataclasses import dataclass
import hashlib
import json
import math
import os
from pathlib import Path

from src.data.inspect import ROOT


@dataclass(frozen=True)
class Prediction:
    intent: str
    category: str
    score: float
    margin: float
    model_version: str
    truncated: bool = False

    def __post_init__(self):
        if any(not math.isfinite(value) or not 0 <= value <= 1 for value in [self.score, self.margin]):
            raise ValueError("Prediction score and margin must be finite numbers between zero and one")


def validate_text(text):
    if not isinstance(text, str) or not text.strip():
        raise ValueError("Ticket text must not be blank")
    if len(text) > 10000:
        raise ValueError("Ticket text must be at most 10,000 characters")
    return " ".join(text.split())


def file_version(name, path):
    with path.open("rb") as source:
        digest = hashlib.file_digest(source, "sha256").hexdigest()
    return f"{name}:{digest[:12]}"


class TicketClassifier:
    def __init__(self, model="distilbert"):
        if model not in {"distilbert", "logistic_regression"}:
            raise ValueError("Unsupported model")
        self.name = model
        models_root = Path(os.environ.get("SUPPORT_MODELS_PATH", str(ROOT / "models")))
        if model == "distilbert":
            import torch
            from transformers import AutoModelForSequenceClassification, AutoTokenizer
            torch.set_num_threads(4)
            metadata = json.loads((models_root / "distilbert/experiment.json").read_text(encoding="utf-8"))
            if metadata["status"] != "training_complete" or metadata["smoke"]:
                raise ValueError("Completed full DistilBERT checkpoint required")
            path = models_root / "distilbert/final"
            self.tokenizer = AutoTokenizer.from_pretrained(path, local_files_only=True)
            self.model = AutoModelForSequenceClassification.from_pretrained(path, local_files_only=True).eval()
            self.mapping = metadata["intent_to_category"]
            self.max_length = metadata["max_length"]
            self.version = file_version(model, path / "model.safetensors")
        else:
            import joblib
            path = models_root / "logistic_regression.joblib"
            artifact = joblib.load(path)
            self.model = artifact["pipeline"]
            self.mapping = artifact["intent_to_category"]
            self.version = file_version(model, path)

    def predict(self, text):
        text = validate_text(text)
        truncated = False
        if self.name == "distilbert":
            import torch
            full = self.tokenizer(text, truncation=False)
            truncated = len(full["input_ids"]) > self.max_length
            encoded = self.tokenizer(text, return_tensors="pt", truncation=True, max_length=self.max_length)
            with torch.inference_mode():
                probabilities = self.model(**encoded).logits.softmax(dim=-1)[0].tolist()
            labels = [self.model.config.id2label[i] for i in range(len(probabilities))]
        else:
            probabilities = self.model.predict_proba([text])[0].tolist()
            labels = self.model.classes_.tolist()
        ordered = sorted(range(len(probabilities)), key=lambda i: probabilities[i], reverse=True)
        first, second = ordered[:2]
        intent = labels[first]
        return Prediction(intent, self.mapping[intent], probabilities[first],
                          probabilities[first] - probabilities[second], self.version, truncated)
