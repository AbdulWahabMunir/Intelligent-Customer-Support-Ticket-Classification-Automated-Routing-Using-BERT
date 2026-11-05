"""Inspect the raw CSV without changing or splitting it. Uses only Python's stdlib."""

import argparse
import csv
from collections import Counter, defaultdict
import html
import json
from pathlib import Path
import statistics

ROOT = Path(__file__).resolve().parents[2]
REQUIRED = {"instruction", "category", "intent"}


def normalize_key(text):
    """Conservative duplicate key; preserve punctuation and words in model text."""
    return " ".join(text.casefold().split())


def inspect_csv(path):
    with Path(path).open(encoding="utf-8-sig", newline="") as source:
        reader = csv.DictReader(source)
        columns = reader.fieldnames or []
        if not REQUIRED.issubset(columns):
            raise ValueError(f"Missing required columns: {sorted(REQUIRED - set(columns))}")
        rows = list(reader)
    if not rows:
        raise ValueError("Dataset contains no rows")
    if any(None in row or any(value is None for value in row.values()) for row in rows):
        raise ValueError("Malformed CSV: row width does not match header")
    missing = {column: sum(not row[column].strip() for row in rows) for column in columns}
    valid = [row for row in rows if all(row[column].strip() for column in REQUIRED)]
    texts = [row["instruction"] for row in valid]
    groups = defaultdict(set)
    intent_categories = defaultdict(set)
    for row in valid:
        groups[normalize_key(row["instruction"])].add((row["category"], row["intent"]))
        intent_categories[row["intent"]].add(row["category"])
    lengths = [len(text.split()) for text in texts]
    buckets = Counter()
    for length in lengths:
        buckets["1–5" if length <= 5 else "6–10" if length <= 10 else "11–20" if length <= 20 else "21+"] += 1
    return {
        "rows": len(rows), "columns": columns, "valid_rows": len(valid),
        "missing_by_column": missing,
        "exact_duplicate_rows": len(rows) - len({tuple(row[c] for c in columns) for row in rows}),
        "duplicate_texts_exact": len(texts) - len(set(texts)),
        "duplicate_texts_normalized": len(texts) - len(groups),
        "conflicting_normalized_text_groups": sum(len(labels) > 1 for labels in groups.values()),
        "category_counts": dict(sorted(Counter(row["category"] for row in valid).items())),
        "intent_counts": dict(sorted(Counter(row["intent"] for row in valid).items())),
        "intent_to_categories": {key: sorted(value) for key, value in sorted(intent_categories.items())},
        "word_count": {"min": min(lengths, default=0), "median": statistics.median(lengths) if lengths else 0,
                       "mean": round(statistics.mean(lengths), 2) if lengths else 0, "max": max(lengths, default=0)},
        "word_count_buckets": {key: buckets[key] for key in ["1–5", "6–10", "11–20", "21+"]},
    }


def write_report(summary, directory):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "eda_summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    sections = []
    for heading, key in [("Categories", "category_counts"), ("Intents", "intent_counts"), ("Message lengths (words)", "word_count_buckets")]:
        counts = summary[key]
        largest = max(counts.values(), default=1) or 1
        bars = "".join(f'<tr><td>{html.escape(label)}</td><td><meter min="0" max="{largest}" value="{count}"></meter></td><td>{count:,}</td></tr>' for label, count in counts.items())
        sections.append(f"<h2>{heading}</h2><table>{bars}</table>")
    details = {k: v for k, v in summary.items() if k not in {"category_counts", "intent_counts", "word_count_buckets", "intent_to_categories"}}
    document = """<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Bitext exploratory analysis</title><style>body{font:16px system-ui;max-width:1000px;margin:40px auto;padding:0 20px;color:#182334}td{padding:5px 12px}meter{width:260px}pre{white-space:pre-wrap;background:#f1f4f8;padding:20px}</style>
<h1>Bitext exploratory analysis</h1><p>Raw dataset audit. Distribution counts use rows with nonempty instruction, category and intent. Lengths are whitespace word counts, not transformer tokens.</p>"""
    document += "<pre>" + html.escape(json.dumps(details, indent=2, ensure_ascii=False)) + "</pre>" + "".join(sections)
    document += "<h2>Before training</h2><p>Resolve conflicting labels and deduplicate before splitting. Keep normalized duplicate groups in one split. Near duplicates and synthetic template overlap require further review. Never use response, category or intent as input features.</p></html>"
    (directory / "eda_report.html").write_text(document, encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=ROOT / "data/raw/bitext.csv")
    parser.add_argument("--output", type=Path, default=ROOT / "reports")
    args = parser.parse_args()
    summary = inspect_csv(args.input)
    write_report(summary, args.output)
    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
