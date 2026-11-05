"""Explicit business policy; no model loading, training or persistence."""

from dataclasses import asdict
import json
import math
import re
import time

from src.data.inspect import ROOT
from src.inference import validate_text


class RoutingPolicy:
    def __init__(self, path=None):
        self.config = json.loads((path or ROOT / "config/routing.json").read_text(encoding="utf-8"))
        for key in ["minimum_score", "minimum_margin"]:
            value = self.config[key]
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or not 0 <= value <= 1:
                raise ValueError(f"Invalid {key}")
        if type(self.config["minimum_words"]) is not int or self.config["minimum_words"] < 1:
            raise ValueError("minimum_words must be a positive integer")
        for intent, pair in self.config["intents"].items():
            if not isinstance(pair, list) or len(pair) != 2 or not all(isinstance(value, str) and value.strip() for value in pair):
                raise ValueError(f"Invalid route for {intent}")
        if not set(self.config["low_priority_intents"]).issubset(self.config["intents"]):
            raise ValueError("Unknown low-priority intent")
        self.rules = []
        for rule in self.config["priority_rules"]:
            if rule["priority"] not in {"Critical", "High", "Medium", "Low"}:
                raise ValueError("Invalid rule priority")
            self.rules.append((rule, re.compile(rule["pattern"], re.IGNORECASE)))

    def decide(self, text, prediction):
        text = validate_text(text)
        review_reasons = []
        route = self.config["intents"].get(prediction.intent)
        if not route:
            review_reasons.append("unmapped_intent")
        elif route[0] != prediction.category:
            review_reasons.append("category_mismatch")
        if prediction.score < self.config["minimum_score"]:
            review_reasons.append("low_model_score")
        if prediction.margin < self.config["minimum_margin"]:
            review_reasons.append("ambiguous_top_predictions")
        if prediction.truncated:
            review_reasons.append("input_truncated")
        if len(text.split()) < self.config["minimum_words"]:
            review_reasons.append("insufficient_context")
        priority = "Medium"
        priority_reason = "default_medium"
        if not review_reasons and prediction.intent in self.config["low_priority_intents"]:
            priority, priority_reason = "Low", "informational_intent"
        matched = None
        # Configuration order is precedence; the first matching rule wins.
        for rule, pattern in self.rules:
            if pattern.search(text):
                matched = rule
                priority, priority_reason = rule["priority"], rule["id"]
                if rule["requires_review"]:
                    review_reasons.append(rule["id"])
                break
        if matched and matched.get("department"):
            department = matched["department"]
            route_reason = "priority_rule_escalation"
        elif review_reasons:
            department = self.config["review_department"]
            route_reason = "human_review_required"
        else:
            department = route[1]
            route_reason = "intent_mapping"
        return {"prediction": asdict(prediction), "department": department, "priority": priority,
                "priority_source": "business_rules", "priority_reason": priority_reason,
                "routing_reason": route_reason, "requires_review": bool(review_reasons),
                "review_reasons": review_reasons, "policy_version": self.config["version"],
                "score_calibrated": False}


class TicketService:
    def __init__(self, classifier, policy=None):
        self.classifier = classifier
        self.policy = policy or RoutingPolicy()
        for intent, category in classifier.mapping.items():
            route = self.policy.config["intents"].get(intent)
            if not route or route[0] != category:
                raise ValueError(f"Model/policy taxonomy mismatch: {intent}")

    def classify_and_route(self, text):
        text = validate_text(text)
        start = time.perf_counter()
        prediction = self.classifier.predict(text)
        result = self.policy.decide(text, prediction)
        result["latency_ms"] = round((time.perf_counter() - start) * 1000, 3)
        return result
