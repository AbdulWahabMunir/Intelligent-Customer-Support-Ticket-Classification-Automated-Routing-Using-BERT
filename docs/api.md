# Support API — local and hosted

The API loads the completed DistilBERT checkpoint once during FastAPI lifespan startup. Synchronous routes run outside the event loop; inference uses a process-local lock to avoid competing CPU thread pools. SQLite uses one closed connection per operation, transactions, foreign keys, and WAL mode. Tickets and feedback are stored in separate tables.

## Start

From the project root in PowerShell:

```powershell
.venv\Scripts\python.exe -m pip install -r requirements-api.txt
.venv\Scripts\python.exe -m uvicorn app.api:app --host 127.0.0.1 --port 8000
```

Open http://127.0.0.1:8000/docs for interactive endpoint documentation. Model artifacts must already exist; startup does not download or train a model. Use one worker for this local CPU app. Each additional worker would load its own model.

Optional process environment variables:

| Variable | Default | Purpose |
| --- | --- | --- |
| `SUPPORT_MODEL` | `distilbert` | Select `distilbert` or `logistic_regression` at startup |
| `SUPPORT_DB_PATH` | `data/runtime/support.sqlite3` under the project root | SQLite database file; parent directories are created |

The runtime directory is excluded from version control. `requirements-api-lock.txt` records all installed packages for the tested Windows environment.

## Endpoints

| Method | Path | Behavior |
| --- | --- | --- |
| GET | `/health` | Checks database connectivity; returns application, model and policy versions |
| GET | `/taxonomy` | Lists allowed intents, categories, departments and priorities |
| POST | `/predict` | Classifies and routes without saving a ticket |
| POST | `/tickets` | Classifies, routes and saves a ticket with its original result |
| GET | `/tickets` | Paginated list; `limit` 1–100, `offset`, `needs_review`, `category`, `priority`, literal case-insensitive `search` |
| GET | `/tickets/{id}` | Retrieves one stored ticket |
| POST | `/tickets/{id}/feedback` | Appends a correction or confirmation |
| POST | `/feedback` | Same operation with `ticket_id` supplied in the JSON body |
| GET | `/tickets/{id}/feedback` | Returns feedback history in submission order |
| GET | `/analytics` | Counts tickets, outstanding reviews, reviewed tickets, feedback and original routing/priority distributions |

Create or predict body:

```json
{"text": "I need to track my refund"}
```

Feedback body:

```json
{
  "corrected_intent": "get_refund",
  "corrected_priority": "Medium",
  "corrected_department": "Finance",
  "note": "Customer requests a new refund, rather than tracking an existing one",
  "reviewer": "local-reviewer"
}
```

Only `corrected_intent` is required. Category is derived from the configured taxonomy and cannot be supplied by the client. Priority, department, note and reviewer are optional. Unknown labels/teams and extra fields return 422. A confirmation can use the original intent. Reviewer is a caller-provided label, not authenticated identity.

Tickets retain the original normalized text, prediction, model version, score, routing, priority, policy version and inference latency. UUIDs identify tickets and feedback; timestamps are UTC with offsets. Empty/whitespace or over-10,000-character text is rejected before inference. Validation responses omit echoed input values. No application logging records ticket text.

## Review and feedback semantics

- An original result is immutable through this API. Corrections are separate append-only records; multiple corrections remain visible in order.
- `review_status` becomes `reviewed` after any feedback. `needs_review=true` selects tickets originally flagged for review that have no feedback yet; `false` selects the complement. The original `result.requires_review` remains unchanged as part of the prediction snapshot.
- Feedback has `training_status: pending`. Label validation is not dataset approval. No approval, export-to-training or automatic retraining is implemented.
- Corrections do not silently reroute or rewrite a ticket. Clients should show the original result and review history separately. Analytics department/priority distributions refer to original decisions.

The local runner may operate without an API key on loopback. Hosted mode requires an API key of at least 32 characters and an external PostgreSQL URL; every endpoint except `/health` requires `X-API-Key`. The live Streamlit frontend calls a loopback-only FastAPI child server-side after reviewer password login. Neon stores live tickets; SQLite remains the local default. No multi-user enterprise identity is claimed.

Analytics includes `corrected_tickets`, `correction_rate`, `corrected_intents` and `review_activity_by_day`. Each ticket contributes only its latest review to correction metrics; confirmations are not corrections. Counts/charts are operational review measurements, not unbiased model accuracy. Category/priority/search filters compose with review state and pagination; `%` and `_` are literal search characters, not SQL wildcards.

## Verification

```powershell
.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Unit tests inject a deterministic classifier and temporary database. Actual DistilBERT and PostgreSQL are verified separately over HTTP and in a constrained container. Local ASGI response-time/edge-case measurements are in `reports/api/performance.json`; live browser evidence is in `reports/deployment/live-updated-verification.json`.

Implementation references: FastAPI's [lifespan documentation](https://fastapi.tiangolo.com/advanced/events/) and [testing guide](https://fastapi.tiangolo.com/tutorial/testing/).
