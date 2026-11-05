"""Train DistilBERT on existing splits; smoke runs never evaluate the test set."""

import argparse
import csv
import hashlib
import json
from pathlib import Path
import platform
import time

from sklearn.metrics import accuracy_score, classification_report, confusion_matrix, f1_score

from src.data.inspect import ROOT
from src.data.prepare import assert_disjoint, read_split

MODEL_ID = "distilbert/distilbert-base-uncased"
REVISION = "12040accade4e8a0f71eabdb258fecc2e7e948be"


def verified_splits(names):
    manifest = json.loads((ROOT / "data/processed/manifest.json").read_text(encoding="utf-8"))
    splits = {}
    for name in names:
        path = ROOT / f"data/processed/{name}.csv"
        if hashlib.sha256(path.read_bytes()).hexdigest() != manifest["splits"][name]["sha256"]:
            raise ValueError(f"Changed split: {name}; regenerate and rerun baselines")
        splits[name] = read_split(name)
    assert_disjoint(splits)
    return splits, manifest


def take_per_intent(rows, count=2):
    counts = {}
    chosen = []
    for row in rows:
        label = row["intent"]
        if counts.get(label, 0) < count:
            chosen.append(row)
            counts[label] = counts.get(label, 0) + 1
    return chosen


def compute_metrics(prediction):
    predicted = prediction.predictions.argmax(axis=-1)
    return {"accuracy": accuracy_score(prediction.label_ids, predicted),
            "macro_f1": f1_score(prediction.label_ids, predicted, average="macro", zero_division=0),
            "weighted_f1": f1_score(prediction.label_ids, predicted, average="weighted", zero_division=0)}


class TicketDataset:
    def __init__(self, rows, tokenizer, label2id):
        self.encodings = tokenizer([r["instruction"] for r in rows], truncation=True, max_length=64)
        self.labels = [label2id[r["intent"]] for r in rows]

    def __len__(self):
        return len(self.labels)

    def __getitem__(self, index):
        return {**{key: values[index] for key, values in self.encodings.items()}, "labels": self.labels[index]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--smoke", action="store_true", help="Two training steps on 54 train/validation examples; no test evaluation")
    parser.add_argument("--evaluate-only", action="store_true", help="Evaluate a completed full run on the test split")
    parser.add_argument("--cpu", action="store_true")
    parser.add_argument("--output", type=Path, help="Defaults to models/distilbert or models/distilbert-smoke")
    args = parser.parse_args()
    if args.smoke and args.evaluate_only:
        parser.error("Smoke runs cannot evaluate the test set")
    # Keep caches inside the project, also when running on Colab.
    import os
    os.environ.setdefault("HF_HOME", str(ROOT / ".cache/huggingface"))
    os.environ.setdefault("HF_HUB_DISABLE_XET", "1")
    os.environ.setdefault("HF_HUB_DISABLE_TELEMETRY", "1")
    os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
    import torch
    import transformers
    from transformers import (AutoModelForSequenceClassification, AutoTokenizer, DataCollatorWithPadding,
                              Trainer, TrainingArguments, set_seed)
    torch.set_num_threads(min(4, os.cpu_count() or 1))
    set_seed(42)
    output = args.output or ROOT / ("models/distilbert-smoke" if args.smoke else "models/distilbert")
    output = output.resolve()
    report_dir = ROOT / ("reports/distilbert-smoke" if args.smoke else "reports/distilbert")
    if args.evaluate_only:
        metadata = json.loads((output / "experiment.json").read_text(encoding="utf-8"))
        if metadata["status"] != "training_complete" or metadata["smoke"]:
            raise ValueError("Only a completed full training run can be evaluated")
        splits, manifest = verified_splits(["train", "validation", "test"])
        if manifest != metadata["data_manifest"]:
            raise ValueError("Evaluation data does not match training provenance")
        tokenizer = AutoTokenizer.from_pretrained(output / "final", local_files_only=True)
        model = AutoModelForSequenceClassification.from_pretrained(output / "final", local_files_only=True)
        label2id = model.config.label2id
        trainer = Trainer(model=model, args=TrainingArguments(output_dir=str(output / "evaluation"),
                          per_device_eval_batch_size=32, use_cpu=args.cpu, report_to="none", dataloader_pin_memory=False),
                          data_collator=DataCollatorWithPadding(tokenizer), compute_metrics=compute_metrics)
        test = TicketDataset(splits["test"], tokenizer, label2id)
        prediction = trainer.predict(test)
        predicted = prediction.predictions.argmax(axis=-1)
        result = {k: float(v) for k, v in prediction.metrics.items()}
        ids = list(range(len(label2id)))
        labels = [model.config.id2label[i] for i in ids]
        result["per_class"] = classification_report(test.labels, predicted, labels=ids, target_names=labels,
                                                    output_dict=True, zero_division=0)
        mapping = metadata["intent_to_category"]
        result["category_accuracy"] = accuracy_score([r["category"] for r in splits["test"]], [mapping[labels[i]] for i in predicted])
        matrix = confusion_matrix(test.labels, predicted, labels=ids)
        report_dir.mkdir(parents=True, exist_ok=True)
        with (report_dir / "confusion.csv").open("w", encoding="utf-8", newline="") as stream:
            writer = csv.writer(stream)
            writer.writerow(["actual / predicted"] + labels)
            writer.writerows([[label] + counts.tolist() for label, counts in zip(labels, matrix)])
        baseline = json.loads((ROOT / "reports/baselines/metrics.json").read_text(encoding="utf-8"))
        import joblib
        baseline_artifact = joblib.load(ROOT / "models/logistic_regression.joblib")
        baseline_manifest = baseline_artifact["data_manifest"]
        if baseline_manifest != manifest:
            raise ValueError("Baseline split provenance differs; cannot compare results")
        result["baseline_test_macro_f1"] = {name: item["test"]["macro_f1"] for name, item in baseline["models"].items()}
        # Match the baseline's 200 warm, single-message, end-to-end predictions.
        import numpy as np
        device = trainer.model.device
        trainer.model.eval()

        def infer(text):
            encoded = tokenizer(text, return_tensors="pt", truncation=True, max_length=metadata["max_length"])
            encoded = {key: value.to(device) for key, value in encoded.items()}
            with torch.inference_mode():
                return trainer.model(**encoded).logits.argmax(dim=-1).item()

        infer(splits["test"][0]["instruction"])
        timings = []
        for row in splits["test"][:200]:
            if device.type == "cuda":
                torch.cuda.synchronize()
            start = time.perf_counter()
            infer(row["instruction"])
            if device.type == "cuda":
                torch.cuda.synchronize()
            timings.append((time.perf_counter() - start) * 1000)
        result["latency_ms"] = {"samples": len(timings), "mean": float(np.mean(timings)),
                                 "p95": float(np.percentile(timings, 95)), "device": str(device),
                                 "scope": "warm single-message tokenization and inference"}
        baseline_model = baseline_artifact["pipeline"]
        baseline_model.predict([splits["test"][0]["instruction"]])
        baseline_timings = []
        for row in splits["test"][:200]:
            start = time.perf_counter()
            baseline_model.predict([row["instruction"]])
            baseline_timings.append((time.perf_counter() - start) * 1000)
        result["same_run_baseline_latency_ms"] = {"model": "logistic_regression", "samples": len(baseline_timings),
                    "mean": float(np.mean(baseline_timings)), "p95": float(np.percentile(baseline_timings, 95)), "device": "cpu"}
        result["model_parameters"] = sum(parameter.numel() for parameter in trainer.model.parameters())
        (report_dir / "test_metrics.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
        lines = ["# Baselines versus DistilBERT", "", "All models use the same hashed splits. Model/checkpoint selection uses validation macro F1; test scores are descriptive final results.", "",
                 "| Model | Test accuracy | Test macro F1 | Test weighted F1 |", "| --- | ---: | ---: | ---: |"]
        for name, item in baseline["models"].items():
            score = item["test"]
            lines.append(f"| {name} | {score['accuracy']:.4f} | {score['macro_f1']:.4f} | {score['weighted_f1']:.4f} |")
        lines.append(f"| distilbert | {result['test_accuracy']:.4f} | {result['test_macro_f1']:.4f} | {result['test_weighted_f1']:.4f} |")
        lines += ["", f"DistilBERT warm single-message latency on {device}: mean {result['latency_ms']['mean']:.2f} ms, p95 {result['latency_ms']['p95']:.2f} ms (200 messages).",
                  f"Logistic Regression measured in the same evaluation process on CPU: mean {result['same_run_baseline_latency_ms']['mean']:.2f} ms, p95 {result['same_run_baseline_latency_ms']['p95']:.2f} ms, using the same 200 messages. These are local warm timings, not API load-test results.",
                  "", "Scores cover a deduplicated random split of synthetic Bitext data. Shared templates may inflate performance. Real-ticket robustness and confidence calibration remain untested."]
        (report_dir / "comparison.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
        print(json.dumps(result, indent=2))
        return
    if (output / "experiment.json").exists():
        raise ValueError("Output already contains an experiment; choose a new --output directory")
    splits, manifest = verified_splits(["train", "validation"])
    labels = sorted({r["intent"] for r in splits["train"]})
    label2id = {label: i for i, label in enumerate(labels)}
    mapping = {}
    for row in splits["train"]:
        if row["intent"] in mapping and mapping[row["intent"]] != row["category"]:
            raise ValueError("Ambiguous intent-to-category mapping")
        mapping[row["intent"]] = row["category"]
    if args.smoke:
        splits = {name: take_per_intent(rows) for name, rows in splits.items()}
    output.mkdir(parents=True, exist_ok=True)
    metadata = {"status": "started", "smoke": args.smoke, "model": MODEL_ID, "revision": REVISION,
                "seed": 42, "max_length": 64, "epochs": 3, "learning_rate": 2e-5,
                "data_manifest": manifest, "intent_to_category": mapping,
                "python": platform.python_version(), "torch": torch.__version__, "transformers": transformers.__version__,
                "cuda_available": torch.cuda.is_available(), "rows": {name: len(rows) for name, rows in splits.items()}}
    (output / "experiment.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    tokenizer = AutoTokenizer.from_pretrained(MODEL_ID, revision=REVISION)
    model = AutoModelForSequenceClassification.from_pretrained(MODEL_ID, revision=REVISION,
                num_labels=len(labels), id2label=dict(enumerate(labels)), label2id=label2id, use_safetensors=True)
    datasets = {name: TicketDataset(rows, tokenizer, label2id) for name, rows in splits.items()}
    arguments = TrainingArguments(output_dir=str(output / "checkpoints"), learning_rate=2e-5,
                 per_device_train_batch_size=4 if args.smoke else 16, per_device_eval_batch_size=16,
                 num_train_epochs=3, max_steps=2 if args.smoke else -1,
                 weight_decay=0.01, warmup_ratio=0.1, eval_strategy="steps" if args.smoke else "epoch",
                 save_strategy="steps" if args.smoke else "epoch", eval_steps=2, save_steps=2,
                 save_total_limit=1, load_best_model_at_end=True, metric_for_best_model="macro_f1",
                 greater_is_better=True, report_to="none", seed=42, data_seed=42,
                 use_cpu=args.cpu, fp16=torch.cuda.is_available() and not args.cpu,
                 dataloader_num_workers=0, dataloader_pin_memory=False, logging_steps=1 if args.smoke else 50)
    trainer = Trainer(model=model, args=arguments, train_dataset=datasets["train"], eval_dataset=datasets["validation"],
                      processing_class=tokenizer, data_collator=DataCollatorWithPadding(tokenizer), compute_metrics=compute_metrics)
    start = time.perf_counter()
    trainer.train()
    validation = trainer.evaluate()
    trainer.save_model(str(output / "final"))
    tokenizer.save_pretrained(output / "final")
    # Verify that the saved checkpoint can be loaded for inference.
    reloaded = AutoModelForSequenceClassification.from_pretrained(output / "final", local_files_only=True).eval()
    encoded = tokenizer("I need to track my refund", return_tensors="pt", truncation=True, max_length=64)
    with torch.no_grad():
        logits = reloaded(**encoded).logits
    if logits.shape != (1, len(labels)) or not torch.isfinite(logits).all():
        raise ValueError("Saved checkpoint inference failed")
    metadata.update(status="smoke_complete" if args.smoke else "training_complete",
                    elapsed_seconds=time.perf_counter() - start, validation=validation,
                    best_checkpoint=trainer.state.best_model_checkpoint, reload_inference_passed=True)
    (output / "experiment.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    report_dir.mkdir(parents=True, exist_ok=True)
    (report_dir / "training.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    print(f"Completed {'SMOKE CHECK (not a trained benchmark)' if args.smoke else 'training'}: {output}")


if __name__ == "__main__":
    main()
