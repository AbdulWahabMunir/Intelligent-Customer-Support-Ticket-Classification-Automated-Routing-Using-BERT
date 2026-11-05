# Model card

Intended use: English customer support intent classification and assisted routing in a portfolio prototype. The taxonomy contains 27 intents and 11 categories. Department and priority are separate business-rule outputs. Arbitrary technical troubleshooting, fraud diagnosis and general conversation are unsupported.

## Provenance

Baselines: word unigram/bigram TF-IDF with Logistic Regression and Multinomial Naive Bayes. Transformer: `distilbert/distilbert-base-uncased`, pretrained revision `12040accade4e8a0f71eabdb258fecc2e7e948be`, fine-tuned for three epochs with seed 42 and selected by validation macro F1. Full training completed locally on CPU; export/reload checks passed.

Bitext data revision: `430d1a89bd93bd1fa23c16f29dd53e73f0087443`. Input is only `instruction`. Deduplication precedes intent-stratified 70/15/15 splits: 16,991 train, 3,641 validation and 3,642 test messages. Source and split hashes are recorded. The source card identifies CDLA-Sharing-1.0; review its terms before redistribution. No project-wide code license has been assigned.

## Measured results

| Model | Test accuracy | Macro F1 |
| --- | ---: | ---: |
| Logistic Regression | 98.96% | 0.9885 |
| Naive Bayes | 98.49% | 0.9836 |
| DistilBERT | 99.86% | 0.9983 |

DistilBERT made five intent errors. Warm sequential local CPU inference averaged 35.62 ms versus 1.53 ms for Logistic Regression on the same 200 messages. This is not an API load test.

Raw top-score ECE on the synthetic test split was approximately 0.0012 for DistilBERT versus 0.1238 for Logistic Regression, using ten equal-width bins. No post-hoc calibrator was fitted. API scores remain marked uncalibrated; see `reports/confidence/report.md`.

## Limits

- Synthetic templates can inflate held-out metrics despite exact deduplication.
- The 108-case agent-authored pilot produced 88.9% DistilBERT anchor accuracy and 77.8% paraphrase accuracy on draft labels. One case overlaps exactly with the dataset. This is not an independently human-approved benchmark.
- Confident errors occur for vague/out-of-domain input. Score, margin, short-text and truncation rules cannot detect every failure.
- Input is truncated at 64 subword tokens and flagged for review; application text is limited to 10,000 characters.
- Priority regexes do not understand arbitrary negation or confirm incidents.
- Feedback remains pending; no automatic retraining or approval workflow exists.
- Public deployment is live at https://aw-intelligent-customer-support.streamlit.app with shared reviewer-password/API-key access. Enterprise identity and a larger independently human-reviewed challenge remain future extensions.
- A seeded template audit found 228/1,000 test messages with nearest-training character-TF-IDF cosine at least 0.95; the synthetic held-out scores should be interpreted with this similarity risk.

Evidence lives in the model comparison, confidence, robustness and API/dashboard verification reports.
