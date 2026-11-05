# Original brief audit — release 1.1.1

Audited against the user-provided Project 5 brief on 2026-11-05. Repository/folder names and hosting placement follow the user's later choices. Illustrative labels are replaced by the actual Bitext taxonomy. Priority is never presented as supervised ground truth.

| Final deliverable | Evidence and verification |
|---|---|
| EDA notebook | Executed `notebooks/01_data_exploration.ipynb`; charts/findings in `reports/eda_report.html` |
| Cleaned dataset pipeline | Pinned hashes, deduplication and stratification in `src/data`; split manifest/report |
| TF-IDF + Naive Bayes | Saved/evaluated baseline; `reports/baselines/metrics.json` |
| TF-IDF + Logistic Regression | Saved/evaluated baseline selected on validation; same report |
| Fine-tuned DistilBERT | Full three-epoch checkpoint and reload verification; `distilbert:130e8686af8b` |
| Model comparison/evaluation | Executed `notebooks/03_model_comparison.ipynb`; per-class, confusion/error, confidence, similarity and performance reports |
| Classification/routing engine | `src/inference.py`, `src/routing.py`; score/margin/truncation review policy |
| Priority detection | Four business-rule levels in `config/routing.json`, independently tested |
| FastAPI REST API | Prediction, tickets, health, analytics, taxonomy and both feedback routes; validation/key protection and latency logging without message text |
| Streamlit dashboard | Live submission/results, review, category/priority filters, literal search, pagination and analytics |
| Human feedback collection | Immutable originals, append-only corrections, timestamps, pending training status; Neon persistence |
| Linguistic robustness evaluation | 108-case paired diagnostic evaluated for both models; hashes/overlap/condition drops recorded. Draft labels are not independent human ground truth |
| Docker configuration | API/dashboard/hosted targets; actual DistilBERT/PostgreSQL integration under 512 MiB verified |
| GitHub documentation/screenshots | README, API/model/data/deployment docs, executed notebooks and inspected live screenshots |
| Deployed demonstration | https://aw-intelligent-customer-support.streamlit.app ; login, API version 1.1.1, filters and pre-update reviewed ticket verified |

## Detailed gaps closed in the final audit

- BANKING77: separate 77-class baseline experiment with fixed validation selection, official 3,080-example test, pinned source and attribution. The deployed taxonomy is unchanged.
- Near-duplicate risk: seeded 1,000-test-message character-TF-IDF nearest-training audit, in addition to exact overlap assertions.
- Edge cases: normal, short, long, misspelled, ambiguous, multi-issue, empty, whitespace, oversized and unseen-topic messages; observed results in `reports/api/performance.json`.
- API latency/error rate: 35 warm local ASGI requests plus validation cases; internet/cold-start exclusions stated.
- Human correction rate: latest review per ticket, confirmations excluded. Daily review activity is not unbiased accuracy over time.
- Cloud persistence: the original user-submitted ticket and Reviewed status survived replacement of the FastAPI process by version 1.1.1.

## Optional research extension and scope boundaries

The brief proposes an independently manually reviewed 300–500-case linguistic challenge as an additional research component. A human linguist has not reviewed such a set. The completed robustness deliverable is the qualified 108-case diagnostic, with an approved-only evaluator and annotation protocol. Do not claim the larger human-reviewed benchmark, real-customer accuracy, improvement from feedback, or production readiness.

The Colab notebook is an optional training alternative; full fine-tuning was actually completed locally. No automatic approval/retraining cycle is claimed. Equivalent implemented pipelines replace illustrative library/snippet choices where appropriate.
