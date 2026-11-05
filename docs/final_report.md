# Final experimental and engineering report

## Implemented system

English messages are classified into 27 Bitext intents and mapped to 11 categories. Separate rules assign priority/department or request human review. The deployed Streamlit dashboard sends HTTP requests to FastAPI; one saved DistilBERT instance serves serialized inference. Tickets, immutable original decisions, versions, latency and append-only corrections persist in Neon PostgreSQL.

Live demo: https://aw-intelligent-customer-support.streamlit.app . Source is published on GitHub; raw datasets, runtime databases and credentials are excluded. The approved model bundle is published separately in Release `v1.0.0`.

## Bitext experiment

Pinned revision `430d1a89bd93bd1fa23c16f29dd53e73f0087443`: 26,872 raw rows, 2,598 normalized duplicates removed, no missing inputs/labels or conflicting normalized labels. Seed-42 intent-stratified split: 16,991 train / 3,641 validation / 3,642 test. Vectorizers fit training text only; checkpoint/model selection uses validation macro-F1.

| Model | Test accuracy | Macro-F1 |
|---|---:|---:|
| TF-IDF + Naive Bayes | 98.49% | 0.9836 |
| TF-IDF + Logistic Regression | 98.96% | 0.9885 |
| Fine-tuned DistilBERT | 99.86% | 0.9983 |

DistilBERT trained for three full epochs, learning rate 2e-5, batch size 16, maximum sequence length 64, seed 42. The exported checkpoint was reloaded. Five test intents were incorrect; weighted-F1 was 0.9986. Synthetic random-split scores are not real-customer reliability estimates.

## Cost, confidence and robustness

- Same-process warm CPU inference over 200 messages: DistilBERT mean 35.62 ms / p95 43.30 ms; Logistic Regression mean 1.53 ms / p95 1.99 ms. The held-out gain has a substantial latency/memory cost.
- Actual-model local ASGI benchmark: 35 warm requests, mean 54.70 ms / p95 136.65 ms, zero unexpected HTTP errors. Empty/whitespace/oversized validation returned 422. Internet latency, free-cloud throttling and cold starts are excluded.
- Ten-bin raw-score ECE: DistilBERT about 0.0012, Logistic Regression about 0.1238. No fitted calibrator is deployed; API scores remain marked uncalibrated.
- Paired 108-case draft diagnostic: DistilBERT anchor accuracy 88.9%, paraphrase 77.8%; Logistic Regression anchor 77.8%, paraphrase 66.7%. One exact dataset overlap is disclosed. Labels are not independently human-approved.
- Similarity audit: 228 of 1,000 seeded test messages have nearest-training character-TF-IDF cosine at least 0.95 (493 at least 0.90). Template-similarity risk remains despite exact-disjoint splits. No threshold was selected to improve reported results.

## Additional BANKING77 experiment

Official data pinned to `57ec275d8078af65b7731c2a98be812d844a6d6b`, attributed to PolyAI/Casanueva et al. (2020), CC BY 4.0. After removal of 11 training duplicate/test-overlap rows, train/validation/official test sizes are 8,493/1,499/3,080. Fixed TF-IDF baselines were selected on validation macro-F1.

Naive Bayes test accuracy/macro-F1: 78.93% / 0.7741. Logistic Regression: 85.00% / 0.8482. This is a separate 77-intent experiment, not a cross-domain score for the deployed 27-intent model. No second transformer was trained. Full per-class results and attribution are in `reports/banking77`.

## Serving and persistence

All 50 unit/widget tests passed. PostgreSQL contract checks passed. Actual DistilBERT, API-key protection, truncation, feedback and restart persistence passed in a 512 MiB Docker container without extra swap. The combined Streamlit/FastAPI layout passed locally against live Neon.

After cloud update, isolated headless Edge confirmed API connected, application 1.1.1, new filters and pre-update ticket `a623e207` still Reviewed. Live screenshots were inspected. Source-refresh handling retires the previous owned API child before starting a new release.

## Limits and future research

Closed-set models can confidently mishandle unseen or multi-issue messages. Score/margin/truncation review rules are provisional. Priority regexes do not understand arbitrary negation. Feedback is collected and measured but not automatically approved/retrained. The larger independently human-reviewed 300–500-case challenge, enterprise identity and production SLA are future extensions. Free hosting can sleep and provider limits can change.
