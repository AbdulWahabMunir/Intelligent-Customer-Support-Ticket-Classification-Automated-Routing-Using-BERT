# Linguistic robustness pilot

The fixed pilot contains 108 agent-authored synthetic examples: one anchor, one paraphrase, one deterministic spelling swap and one polite wrapper for each of 27 intents. Cases are in `data/robustness/pilot.json`, with every label marked `draft` pending human linguistic review. No dataset messages were copied into the authoring script; exact overlap with the dataset is measured separately.

```powershell
.venv\Scripts\python.exe -m src.evaluate_robustness
```

The evaluator loads each existing model once and never trains it. It records the set hash, model artifact versions, per-condition accuracy/macro F1, accuracy drop from anchors in percentage points, prediction consistency, and variant accuracy conditional on a correct anchor. Predictions are recorded by case ID. Shared incorrect predictions can produce high consistency, so consistency alone is not a correctness metric.

Results appear in `reports/robustness-pilot/report.md`. These are diagnostic measurements on proposed labels, not a human-approved independent benchmark. The original synthetic Bitext test metrics must not be treated as real-ticket reliability. Paraphrases may introduce ambiguity; a spelling swap may affect an unimportant word. The set does not yet cover systematic negation, naturally occurring customer errors or the proposed 300–500-example research challenge.

For human review, inspect label correctness, intent preservation and distinctness from training templates. Approve complete four-case groups by changing their `review_status` to `approved`; then run:

```powershell
.venv\Scripts\python.exe -m src.evaluate_robustness --approved-only
```

This mode rejects empty/incomplete approved groups rather than reporting misleading zero- or partial-case scores. Keep the reviewed set separate from training data. Do not revise examples or tune model parameters after inspecting scores to improve the reported result. A larger independently reviewed set remains required before research claims.
