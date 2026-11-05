import csv
from pathlib import Path
import tempfile
import unittest

from src.data.inspect import inspect_csv, write_report


class InspectionTests(unittest.TestCase):
    def test_duplicate_conflicts_and_missing_values(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "fixture.csv"
            with path.open("w", encoding="utf-8", newline="") as output:
                writer = csv.writer(output)
                writer.writerow(["instruction", "category", "intent", "response"])
                writer.writerows([
                    ["  Help ME ", "ACCOUNT", "login", "a"],
                    ["help me", "ORDER", "track", "b"],
                    ["help me", "ORDER", "track", "b"],
                    [" ", "ACCOUNT", "login", "c"],
                ])
            summary = inspect_csv(path)
            self.assertEqual(summary["rows"], 4)
            self.assertEqual(summary["valid_rows"], 3)
            self.assertEqual(summary["missing_by_column"]["instruction"], 1)
            self.assertEqual(summary["exact_duplicate_rows"], 1)
            self.assertEqual(summary["duplicate_texts_normalized"], 2)
            self.assertEqual(summary["conflicting_normalized_text_groups"], 1)
            write_report(summary, Path(temporary) / "reports")
            self.assertTrue((Path(temporary) / "reports/eda_report.html").exists())

    def test_invalid_schema_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "invalid.csv"
            path.write_text("message,label\nhello,account\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "Missing required columns"):
                inspect_csv(path)


if __name__ == "__main__":
    unittest.main()
