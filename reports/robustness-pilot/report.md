# Linguistic robustness pilot

108 cases; 108 draft labels; 1 exact normalized overlaps with existing dataset messages.

This small agent-authored set is a diagnostic, not a human-approved independent benchmark. Shared templates and ambiguous expected labels can affect these results. No retraining or tuning was performed.

| Model | Condition | Accuracy | Macro F1 | Change from anchor (pp) | Anchor consistency |
| --- | --- | ---: | ---: | ---: | ---: |
| logistic_regression | anchor | 0.778 | 0.710 | 0.00 | 1.000 |
| logistic_regression | paraphrase | 0.667 | 0.593 | 11.11 | 0.556 |
| logistic_regression | polite_wrapper | 0.741 | 0.660 | 3.70 | 0.963 |
| logistic_regression | spelling_swap | 0.704 | 0.630 | 7.41 | 0.889 |
| distilbert | anchor | 0.889 | 0.852 | 0.00 | 1.000 |
| distilbert | paraphrase | 0.778 | 0.716 | 11.11 | 0.815 |
| distilbert | polite_wrapper | 0.926 | 0.901 | -3.70 | 0.963 |
| distilbert | spelling_swap | 0.815 | 0.753 | 7.41 | 0.778 |

Positive change values indicate degradation from anchor accuracy. Prediction consistency can remain high even when the anchor is wrong; metrics.json also records accuracy conditional on a correctly predicted anchor.

Before research claims: have a human review label correctness and intent preservation, expand coverage with independent sources and contrastive/negation examples, and use --approved-only. Human approval requires complete groups with an approved anchor. Do not edit examples to increase model scores.
