"""Exercise both saved models and the routing policy using authored examples."""

import json

from src.data.inspect import ROOT
from src.inference import TicketClassifier
from src.routing import TicketService


def main():
    examples = [
        ("refund_tracking", "I need to track my refund"),
        ("urgent_payment", "URGENT: my payment failed"),
        ("account_compromise", "My account has been hacked"),
        ("outage", "The service is down for all users"),
        ("vague_request", "help"),
    ]
    results = []
    for name in ["logistic_regression", "distilbert"]:
        service = TicketService(TicketClassifier(name))
        for example, text in examples:
            result = service.classify_and_route(text)
            results.append({"example": example, "model": name, **result})
            if example == "account_compromise":
                assert result["department"] == "Account Security" and result["requires_review"]
            if example == "outage":
                assert result["priority"] == "Critical" and result["department"] == "Incident Response"
            if example == "vague_request":
                assert result["department"] == "Manual Triage" and result["requires_review"]
            print(json.dumps({"example": example, "model": name, "department": result["department"],
                              "priority": result["priority"], "requires_review": result["requires_review"]}), flush=True)
        if name == "distilbert":
            result = service.classify_and_route("refund " * 100)
            assert result["prediction"]["truncated"] and "input_truncated" in result["review_reasons"]
    destination = ROOT / "reports/routing"
    destination.mkdir(exist_ok=True)
    (destination / "demo_results.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
    print("Both models and long-input review verified; authored demo results saved")


if __name__ == "__main__":
    main()
