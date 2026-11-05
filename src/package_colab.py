"""Package project code and exact existing splits for private Colab training."""

from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED

from src.data.inspect import ROOT
from src.train_distilbert import verified_splits


def main():
    verified_splits(["train", "validation", "test"])
    destination = ROOT / "artifacts/distilbert-colab.zip"
    destination.parent.mkdir(exist_ok=True)
    paths = [ROOT / name for name in ["requirements.txt", "README.md", "docs/distilbert_experiment.md",
             "data/processed/manifest.json", "reports/baselines/metrics.json", "models/logistic_regression.joblib"]]
    paths += [ROOT / f"data/processed/{name}.csv" for name in ["train", "validation", "test"]]
    paths += sorted((ROOT / "src").rglob("*.py"))
    with ZipFile(destination, "w", compression=ZIP_DEFLATED) as archive:
        for path in paths:
            archive.write(path, path.relative_to(ROOT).as_posix())
    print(f"Created {destination} ({destination.stat().st_size:,} bytes). Contains dataset splits; keep private.")


if __name__ == "__main__":
    main()
