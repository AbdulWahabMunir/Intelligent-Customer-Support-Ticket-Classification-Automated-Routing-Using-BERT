"""Deduplicate before making reproducible 70/15/15 intent-stratified splits."""

import csv
import hashlib
import json
from collections import Counter

from sklearn.model_selection import train_test_split

from src.data.inspect import ROOT, inspect_csv, normalize_key

SEED = 42
FIELDS = ["instruction", "category", "intent"]


def clean_rows(rows):
    unique = {}
    for row in rows:
        if not all(row.get(field, "").strip() for field in FIELDS):
            raise ValueError("Missing instruction or target; review raw data before proceeding")
        key = normalize_key(row["instruction"])
        cleaned = {field: row[field].strip() for field in FIELDS}
        cleaned["instruction"] = " ".join(cleaned["instruction"].split())
        if key in unique and any(unique[key][field] != cleaned[field] for field in ["category", "intent"]):
            raise ValueError("Conflicting labels for normalized message")
        unique.setdefault(key, cleaned)
    return [unique[key] for key in sorted(unique)]


def assert_disjoint(splits):
    seen = set()
    for name, rows in splits.items():
        keys = {normalize_key(row["instruction"]) for row in rows}
        if len(keys) != len(rows) or seen.intersection(keys):
            raise ValueError(f"Duplicate message within or across splits: {name}")
        seen.update(keys)


def split_rows(rows):
    train, holdout = train_test_split(rows, test_size=0.30, random_state=SEED,
                                     stratify=[row["intent"] for row in rows])
    validation, test = train_test_split(holdout, test_size=0.5, random_state=SEED,
                                      stratify=[row["intent"] for row in holdout])
    splits = {"train": train, "validation": validation, "test": test}
    assert_disjoint(splits)
    labels = {row["intent"] for row in rows}
    if any({row["intent"] for row in subset} != labels for subset in splits.values()):
        raise ValueError("Every split must contain every intent")
    return splits


def read_split(name):
    with (ROOT / f"data/processed/{name}.csv").open(encoding="utf-8", newline="") as source:
        return list(csv.DictReader(source))


def main():
    source = ROOT / "data/raw/bitext.csv"
    inspect_csv(source)  # Reject malformed CSV or schema before cleaning.
    with source.open(encoding="utf-8-sig", newline="") as stream:
        raw = list(csv.DictReader(stream))
    cleaned = clean_rows(raw)
    splits = split_rows(cleaned)
    destination = ROOT / "data/processed"
    destination.mkdir(parents=True, exist_ok=True)
    manifest = {"seed": SEED, "raw_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
                "raw_rows": len(raw), "unique_rows": len(cleaned), "duplicates_removed": len(raw) - len(cleaned),
                "method": "case/whitespace deduplication; intent-stratified 70/15/15", "splits": {}}
    for name, rows in splits.items():
        target = destination / f"{name}.csv"
        with target.open("w", encoding="utf-8", newline="") as output:
            writer = csv.DictWriter(output, fieldnames=FIELDS)
            writer.writeheader()
            writer.writerows(rows)
        manifest["splits"][name] = {"rows": len(rows), "sha256": hashlib.sha256(target.read_bytes()).hexdigest(),
                                    "intent_counts": dict(sorted(Counter(row["intent"] for row in rows).items()))}
    (destination / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    (ROOT / "reports/split_summary.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"Removed {len(raw) - len(cleaned):,} duplicates; " + ", ".join(f"{k}: {len(v):,}" for k, v in splits.items()))


if __name__ == "__main__":
    main()
