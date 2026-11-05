# No-card Streamlit Community Cloud deployment

Deploy `community_full/streamlit_app.py` from the `free-hosting` branch and select Python 3.14. This entrypoint retains the complete architecture: Streamlit frontend → loopback HTTP → FastAPI backend → fine-tuned DistilBERT and Neon PostgreSQL. It does not replace FastAPI with direct model calls.

The app starts one cached FastAPI subprocess after reviewer login. API inference is serialized, and Uvicorn uses one worker. If the child exits, the cached resource is invalidated and the next rerun starts it again. The subprocess uses the same Python environment as Streamlit. Community Cloud sleeping/rebooting stops both processes; the model can be downloaded again, while tickets and append-only feedback remain in Neon.

Set five Streamlit secrets: `DATABASE_URL`, `SUPPORT_API_KEY`, `SUPPORT_DASHBOARD_PASSWORD`, `MODEL_BUNDLE_URL`, `MODEL_BUNDLE_SHA256`. The prepared local secrets file is `data/runtime/streamlit-cloud-secrets.toml` and is excluded from Git. Paste its contents into the deployment's Advanced settings → Secrets. Do not commit it.

No separate public API URL or Render account is required. Render Free remains an optional alternative, but this account's service-creation attempt required payment information and no service was created. No paid resources are authorized by this setup.

Initial model download/startup can take a few minutes. Cloud resource limits still apply; local verification does not establish that a cloud deploy is live. Use synthetic examples in this shared-password portfolio demo.
