# Ticket classification and routing

`TicketClassifier` loads the completed DistilBERT checkpoint or Logistic Regression baseline once. It predicts intent, category, top score and top-two score margin. `RoutingPolicy` makes operational decisions using `config/routing.json`. `TicketService` combines both and records warm prediction/routing latency. Model load time is excluded. Nothing is persisted or sent to another service at this stage.

## Try it locally

```powershell
.venv\Scripts\python.exe -m src.route_ticket "I need to track my refund"
.venv\Scripts\python.exe -m src.route_ticket "URGENT: my payment failed"
.venv\Scripts\python.exe -m src.route_ticket "My account has been hacked"
.venv\Scripts\python.exe -m src.route_ticket "What delivery options are available?" --model logistic_regression
```

The JSON output keeps the model prediction separate from department, priority and review reasons. It includes a hash-based model version, policy version and end-to-end inference/routing latency. The score is explicitly marked uncalibrated. CLI output omits ticket text; the caller already holds it.

## Current business rules

All 27 dataset intents have explicit department mappings. No technical-support/crash category or subscription-cancellation intent is invented: these are absent from this trained taxonomy. Startup rejects a model/policy taxonomy mismatch.

| Condition | Decision |
| --- | --- |
| Score below 0.80 or top-two margin below 0.15 | Human review in Manual Triage |
| Unknown intent, category mismatch, or truncated model input | Human review in Manual Triage |
| Fewer than three words (configurable) | Human review for insufficient context, regardless of model score |
| Reported service outage matching the configured phrase | Critical priority, Incident Response, human review |
| Reported account compromise or unauthorized charge/access matching the configured phrase | High priority, Account Security, human review |
| Explicit urgent/ASAP wording | High priority; normal review checks still apply |
| Confident informational intent in the configured list | Low priority |
| Otherwise | Medium priority; department from intent mapping |

The first matching priority rule wins. Incident/security escalation routes to a specialist review team even if the prediction is uncertain; it does not change the predicted intent or category. Text patterns are case-insensitive and scan the full text even when model input is truncated. Empty tickets and text over 10,000 characters are rejected.

The thresholds are provisional business settings, not fitted or calibrated reliability guarantees. Different models have different score behavior. A high score does not detect every out-of-domain message. Priority is not learned from dataset labels, and no priority-accuracy claim is made.

Integration checks found that DistilBERT confidently assigns an intent to `help`. The minimum-word rule therefore requests review independently of model confidence. It is deliberately conservative: meaningful two-word requests also need review under the current setting. Longer out-of-domain requests can still receive confident incorrect predictions. The demo outputs are integration examples, not a measured routing benchmark.

Regex patterns recognize a few explicit phrases, not arbitrary negation, incident confirmation or general meaning. For example, `service is not down` does not match the outage pattern, but more complex negation can still produce false escalations. Human review remains necessary for escalated cases. Rules, taxonomy coverage and edge-case behavior are covered by unit tests; real operational policy needs business review.

Next stage: expose the service through FastAPI, save tickets/predictions in SQLite, and collect human corrections without automatic retraining.
