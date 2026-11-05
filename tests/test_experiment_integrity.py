import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from src.train_distilbert import verified_splits


class ExperimentIntegrityTests(unittest.TestCase):
    def test_changed_split_is_rejected_before_training(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            folder = root / "data/processed"
            folder.mkdir(parents=True)
            split = folder / "train.csv"
            split.write_text("instruction,category,intent\nhello,ACCOUNT,create_account\n", encoding="utf-8")
            digest = hashlib.sha256(split.read_bytes()).hexdigest()
            (folder / "manifest.json").write_text(json.dumps({"splits": {"train": {"sha256": digest}}}))
            split.write_text("instruction,category,intent\nchanged,ACCOUNT,create_account\n", encoding="utf-8")
            with patch("src.train_distilbert.ROOT", root):
                with self.assertRaisesRegex(ValueError, "Changed split"):
                    verified_splits(["train"])

    def test_smoke_split_verification_never_requests_test_data(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            folder = root / "data/processed"
            folder.mkdir(parents=True)
            manifest = {"splits": {}}
            for name in ["train", "validation"]:
                path = folder / f"{name}.csv"
                path.write_text(name, encoding="utf-8")
                manifest["splits"][name] = {"sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
            (folder / "manifest.json").write_text(json.dumps(manifest))
            rows = {name: [{"instruction": name, "intent": "login", "category": "ACCOUNT"}]
                    for name in ["train", "validation"]}
            with patch("src.train_distilbert.ROOT", root), patch("src.train_distilbert.read_split", side_effect=lambda name: rows[name]) as reader:
                verified_splits(["train", "validation"])
                self.assertEqual([call.args[0] for call in reader.call_args_list], ["train", "validation"])


if __name__ == "__main__":
    unittest.main()
