# Project status ? verified portfolio release 1.1.1

Live application: https://aw-intelligent-customer-support.streamlit.app

Streamlit ? internal HTTP ? FastAPI ? fine-tuned DistilBERT and separate business rules ? Neon PostgreSQL. Login, prediction, feedback, analytics and ticket management work in the deployed app. An isolated Edge browser confirmed version 1.1.1, new category/priority/search controls and the pre-update ticket a623e207 still Reviewed after the API child was replaced. Evidence: reports/deployment/live-updated-verification.json and inspected live screenshots.

The final audit added missing filters/search, correction analytics and the POST /feedback compatibility route; executed EDA/comparison notebooks; completed the BANKING77 baseline experiment and near-template audit; and measured API latency/error handling. All 50 tests passed. PostgreSQL and actual-model Docker restart checks passed, including the 512 MiB memory constraint. Source is synchronized to main and free-hosting; the approved model is in GitHub Release v1.0.0.

See [requirement audit](requirements_audit.md) and [final report](final_report.md).

The completed linguistic robustness deliverable is a qualified 108-case draft diagnostic. An independently human-reviewed 300?500-case research benchmark, feedback approval/retraining and enterprise identity remain future extensions; they are not represented as completed research or production readiness. Free hosting may sleep and impose limits.

No paid resources were created. Render Free required payment information, so the live app uses Streamlit Community Cloud and Neon. The Render configurations remain unused alternatives.
