# Project status

The local application is implemented: dataset/EDA pipeline, deduplicated splits, both traditional baselines, fully fine-tuned DistilBERT, evaluation/error/calibration diagnostics, routing/priority policy, FastAPI, SQLite, append-only feedback, Streamlit and a robustness pilot. The source also includes CI configuration, release packaging, a hosted process supervisor and optional shared-password access.

Windows was upgraded from build 21996 to 26300. Docker Desktop 4.98.0, CLI/engine 29.9.2 and Compose 5.6.1 are working with WSL 3.0.3. The Linux VM starts successfully. Both Docker images build successfully. Container prediction, ticket/feedback storage, API restart persistence and dashboard health passed; see `reports/containers/runtime.json`. All 41 local tests also passed after the Windows upgrade.

## Remaining publication work

Source and the approved model bundle (`v1.0.0` Release) are published at https://github.com/AbdulWahabMunir/Intelligent-Customer-Support-Ticket-Classification-Automated-Routing-Using-BERT. The selected free path is Render Free FastAPI + DistilBERT, Streamlit Community Cloud, and Neon Free PostgreSQL. `render-free.yaml` passes schema validation. All 45 tests pass; actual DistilBERT, API-key access, long inputs, PostgreSQL feedback and restart persistence passed in a 512 MiB container with no extra swap. The Neon connection and Streamlit account configuration are still required before live cloud verification.

The Render Free create request returned HTTP 402 requiring payment information; no service or paid resource was created. The chosen no-card path is now `community_full/streamlit_app.py` on Streamlit Community Cloud: frontend plus internal FastAPI/DistilBERT, with live Neon PostgreSQL. This layout passed login, actual model prediction, feedback and restart persistence locally. All 47 tests pass. Streamlit account authorization and live publishing are still required. The original `render.yaml` remains a separate paid proposal and must not be applied for this free deployment.

Human review of challenge labels, production identity and cloud verification are not implied by software test success. See the model card and deployment guide for exact limits.
