from pathlib import Path
import tempfile
import unittest
from zipfile import ZipFile

from app.bootstrap import safe_extract


class BootstrapTests(unittest.TestCase):
    def test_archive_traversal_is_rejected_before_extraction(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            archive = root / "bad.zip"
            with ZipFile(archive, "w") as output:
                output.writestr("../escape.txt", "untrusted")
            with self.assertRaises(ValueError):
                safe_extract(archive, root / "models")
            self.assertFalse((root / "escape.txt").exists())

    def test_valid_archive_is_extracted(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            archive = root / "good.zip"
            with ZipFile(archive, "w") as output:
                output.writestr("distilbert/final/config.json", "{}")
            safe_extract(archive, root / "models")
            self.assertEqual((root / "models/distilbert/final/config.json").read_text(), "{}")


if __name__ == "__main__":
    unittest.main()
