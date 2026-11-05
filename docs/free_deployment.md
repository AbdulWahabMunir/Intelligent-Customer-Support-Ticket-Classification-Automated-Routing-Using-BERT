# Free deployment: FastAPI + DistilBERT + Streamlit + PostgreSQL

Use Render Free for the FastAPI backend, Streamlit Community Cloud for the dashboard, and Neon Free for durable PostgreSQL tickets and feedback. No paid resources are required by this configuration. Render's free web service has no fixed trial expiry, but sleeps on inactivity and has monthly usage limits. Do not use Render Free Postgres: it expires after 30 days. Cloud providers may change their free plans; this is a portfolio deployment without an uptime guarantee.

The existing fine-tuned DistilBERT model is retained. Locally, its API passed prediction, feedback and restart tests with a hard 512 MiB Docker memory limit and no additional swap. This establishes local feasibility, not an equivalent cloud runtime guarantee. The frontend does not load PyTorch or model weights. Inference is serialized in the API.

## Backend

`render-free.yaml` describes the free backend (the original `render.yaml` remains a separate paid proposal). Build installs CPU PyTorch, API dependencies and psycopg, then downloads the approved GitHub Release model bundle and verifies its SHA-256. The weights are build artifacts; recreating an ephemeral service can fetch them again. One Uvicorn worker listens on Render's `PORT`.

Configure `DATABASE_URL` with a Neon Free PostgreSQL URL using TLS (`sslmode=require`). Configure a random `SUPPORT_API_KEY` with at least 32 characters. `/health` is public; all other routes require the `X-API-Key` header. The dashboard makes server-side API calls, so this key is not sent to the browser. The public API runner refuses to start without PostgreSQL and an API key; it never silently falls back to disposable SQLite.

## Dashboard

In https://share.streamlit.io sign in with GitHub, create an app from this repository, branch `free-hosting`, entrypoint `community/streamlit_app.py`. Select Python 3.14. The requirements file beside that entrypoint installs only the UI dependencies. The verified hosting changes are on `free-hosting`; GitHub returned server errors when updating `main`.

Set these Streamlit secrets in the deployment UI (never commit their values):

```toml
SUPPORT_API_URL = "https://your-backend.onrender.com"
SUPPORT_API_KEY = "same-random-key-as-backend"
SUPPORT_DASHBOARD_PASSWORD = "a-long-unique-workspace-password"
```

The API client allows a 120-second timeout for a sleeping backend to wake. The dashboard requires its reviewer password before loading tickets. This is a shared-password portfolio demo, not enterprise user identity. Use synthetic tickets in the public demo.

## Verify after deployment

Confirm `/health` is ready; unauthenticated `/analytics` returns 401. Sign into the dashboard, submit a ticket, verify DistilBERT intent/category and policy-derived priority/department, save a correction, restart the backend and confirm the original prediction plus feedback remain in PostgreSQL. Do not claim a cloud deployment passed until these checks actually succeed.

The local PostgreSQL contract verification is recorded in `reports/deployment/postgres-verification.json`; it uses a fixture classifier to isolate storage behavior. Container runtime verification separately uses the actual DistilBERT model.
