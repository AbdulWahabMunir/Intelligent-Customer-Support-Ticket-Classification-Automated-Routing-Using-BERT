from dataclasses import replace
import unittest

from src.inference import Prediction
from src.routing import RoutingPolicy, TicketService


class RoutingTests(unittest.TestCase):
    def setUp(self):
        self.policy = RoutingPolicy()
        self.prediction = Prediction("track_refund", "REFUND", 0.98, 0.8, "test-model:v1")

    def test_confident_refund_routes_to_finance(self):
        result = self.policy.decide("Where is my refund?", self.prediction)
        self.assertEqual((result["department"], result["priority"]), ("Finance", "Medium"))
        self.assertFalse(result["requires_review"])

    def test_low_score_and_small_margin_require_review(self):
        result = self.policy.decide("help", replace(self.prediction, score=0.6, margin=0.05))
        self.assertEqual(result["department"], "Manual Triage")
        self.assertEqual(result["review_reasons"], ["low_model_score", "ambiguous_top_predictions", "insufficient_context"])

    def test_high_score_does_not_auto_route_underspecified_text(self):
        result = self.policy.decide("help", self.prediction)
        self.assertEqual(result["department"], "Manual Triage")
        self.assertIn("insufficient_context", result["review_reasons"])

    def test_unknown_or_inconsistent_taxonomy_requires_review(self):
        for prediction in [replace(self.prediction, intent="unknown"), replace(self.prediction, category="ACCOUNT")]:
            result = self.policy.decide("help", prediction)
            self.assertTrue(result["requires_review"])
            self.assertEqual(result["department"], "Manual Triage")

    def test_truncated_input_requires_review(self):
        result = self.policy.decide("long message", replace(self.prediction, truncated=True))
        self.assertIn("input_truncated", result["review_reasons"])

    def test_security_override_preserves_uncertain_prediction(self):
        prediction = replace(self.prediction, score=0.5, margin=0.05)
        result = self.policy.decide("My account has been hacked", prediction)
        self.assertEqual((result["department"], result["priority"]), ("Account Security", "High"))
        self.assertTrue(result["requires_review"])
        self.assertIn("low_model_score", result["review_reasons"])
        self.assertEqual(result["prediction"]["intent"], "track_refund")

    def test_outage_takes_precedence_over_urgency(self):
        result = self.policy.decide("URGENT: the service is down", self.prediction)
        self.assertEqual((result["department"], result["priority"]), ("Incident Response", "Critical"))
        self.assertTrue(result["requires_review"])

    def test_negated_outage_does_not_match_simple_rule(self):
        result = self.policy.decide("The service is not down; where is my refund?", self.prediction)
        self.assertEqual(result["priority"], "Medium")

    def test_informational_intent_is_low_unless_urgent(self):
        prediction = replace(self.prediction, intent="delivery_options", category="DELIVERY")
        self.assertEqual(self.policy.decide("What delivery options exist?", prediction)["priority"], "Low")
        self.assertEqual(self.policy.decide("URGENT delivery question", prediction)["priority"], "High")
        uncertain = self.policy.decide("help", replace(prediction, score=0.6))
        self.assertEqual(uncertain["priority"], "Medium")

    def test_invalid_scores_are_rejected(self):
        for score in [float("nan"), float("inf"), -0.1, 1.1]:
            with self.assertRaises(ValueError):
                replace(self.prediction, score=score)

    def test_service_rejects_taxonomy_mismatch_and_blank_input(self):
        class Classifier:
            mapping = {"track_refund": "REFUND"}

            def predict(inner_self, text):
                return self.prediction

        service = TicketService(Classifier())
        with self.assertRaises(ValueError):
            service.classify_and_route("   ")
        self.assertEqual(service.classify_and_route("Where is my refund?")["department"], "Finance")
        Classifier.mapping = {"track_refund": "ACCOUNT"}
        with self.assertRaisesRegex(ValueError, "taxonomy mismatch"):
            TicketService(Classifier())


if __name__ == "__main__":
    unittest.main()
