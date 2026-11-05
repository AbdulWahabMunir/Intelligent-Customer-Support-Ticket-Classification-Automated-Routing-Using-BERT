import unittest

from src.evaluate_confidence import calibration_metrics


class ConfidenceTests(unittest.TestCase):
    def test_perfect_probabilities_include_one_in_last_bin(self):
        result = calibration_metrics([0, 1], [[1, 0], [0, 1]])
        self.assertEqual(result["ece_10_bins"], 0)
        self.assertEqual(result["multiclass_brier_sum"], 0)
        self.assertEqual(result["reliability_bins"][-1]["count"], 2)

    def test_overconfident_errors_are_penalized(self):
        result = calibration_metrics([1, 1], [[0.9, 0.1], [0.9, 0.1]])
        self.assertAlmostEqual(result["ece_10_bins"], 0.9)
        self.assertAlmostEqual(result["multiclass_brier_sum"], 1.62)

    def test_invalid_probabilities_are_rejected(self):
        for matrix in [[[0.1, 0.1]], [[float("nan"), 0.5]], [[1.1, -0.1]]]:
            with self.assertRaises(ValueError):
                calibration_metrics([0], matrix)


if __name__ == "__main__":
    unittest.main()
