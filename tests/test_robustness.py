import unittest

from src.evaluate_robustness import summarize, validate_cases


def fixture():
    return [{"id": f"{label}:{condition}", "group": label, "intent": label,
             "condition": condition, "text": "authored message", "review_status": "draft"}
            for label in ["a", "b"] for condition in ["anchor", "paraphrase", "spelling_swap", "polite_wrapper"]]


class RobustnessTests(unittest.TestCase):
    def test_consistency_does_not_hide_wrong_anchor(self):
        cases = fixture()
        predictions = ["a", "b", "b", "a", "a", "a", "a", "a"]
        result = summarize(cases, predictions)
        self.assertEqual(result["anchor"]["accuracy"], 0.5)
        self.assertEqual(result["paraphrase"]["accuracy"], 0)
        self.assertEqual(result["paraphrase"]["prediction_consistency_with_anchor"], 0.5)
        self.assertEqual(result["paraphrase"]["accuracy_when_anchor_correct"], 0)
        self.assertEqual(result["paraphrase"]["accuracy_drop_from_anchor_pp"], 50)

    def test_incomplete_approved_groups_and_duplicate_ids_are_rejected(self):
        cases = fixture()
        validate_cases(cases, {"a", "b"})
        with self.assertRaises(ValueError):
            validate_cases(cases[1:], {"a", "b"})
        with self.assertRaises(ValueError):
            validate_cases(cases + [cases[0]], {"a", "b"})

    def test_empty_or_unknown_label_challenges_are_rejected(self):
        with self.assertRaises(ValueError):
            validate_cases([], {"a", "b"})
        with self.assertRaises(ValueError):
            validate_cases(fixture(), {"a"})

    def test_prediction_count_mismatch_is_rejected(self):
        with self.assertRaises(ValueError):
            summarize(fixture(), ["a"])


if __name__ == "__main__":
    unittest.main()
