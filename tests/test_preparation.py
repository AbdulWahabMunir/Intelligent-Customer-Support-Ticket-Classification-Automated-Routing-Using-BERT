import unittest

from sklearn.naive_bayes import MultinomialNB

from src.data.prepare import assert_disjoint, clean_rows, split_rows
from src.train_baselines import make_pipeline


class PreparationTests(unittest.TestCase):
    def test_deduplicate_and_reject_conflicts(self):
        row = {"instruction": " Help  ME ", "category": "ACCOUNT", "intent": "login"}
        duplicate = dict(row, instruction="help me")
        self.assertEqual(len(clean_rows([row, duplicate])), 1)
        with self.assertRaises(ValueError):
            clean_rows([row, dict(duplicate, intent="delete")])

    def test_split_reproducibility_and_overlap_guard(self):
        rows = [{"instruction": f"message {label} {i}", "category": label, "intent": label}
                for label in ["a", "b", "c"] for i in range(50)]
        first = split_rows(rows)
        self.assertEqual(first, split_rows(rows))
        self.assertEqual(sum(map(len, first.values())), len(rows))
        with self.assertRaises(ValueError):
            assert_disjoint({"train": rows[:2], "test": rows[:1]})

    def test_vectorizer_does_not_learn_heldout_words(self):
        model = make_pipeline(MultinomialNB())
        model.fit(["refund money", "refund payment", "account login", "account access"], ["refund", "refund", "account", "account"])
        model.predict(["unseenheldouttoken"])
        self.assertNotIn("unseenheldouttoken", model.named_steps["tfidf"].vocabulary_)


if __name__ == "__main__":
    unittest.main()
