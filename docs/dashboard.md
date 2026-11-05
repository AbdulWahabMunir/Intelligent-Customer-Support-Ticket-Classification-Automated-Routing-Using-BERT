# Streamlit support dashboard

The dashboard talks only to the FastAPI service over HTTP. It does not load model weights or access SQLite directly. Each API request has a timeout, closes its HTTP client and presents a concise error if the backend is unavailable.

## Run locally

Install the tested dependencies:

```powershell
.venv\Scripts\python.exe -m pip install -r requirements-dashboard.txt
```

Start the API in one terminal:

```powershell
.venv\Scripts\python.exe -m uvicorn app.api:app --host 127.0.0.1 --port 8000
```

Start the dashboard in another:

```powershell
.venv\Scripts\python.exe -m streamlit run app/dashboard.py
```

Open http://127.0.0.1:8501. The project configuration binds Streamlit to localhost, uses a light teal theme and disables usage statistics. The backend model is selected when the API starts, rather than from a browser widget.

Set `SUPPORT_API_URL` in the dashboard process environment to use another API address. It defaults to `http://127.0.0.1:8000`. The tested environment is recorded in `requirements-dashboard-lock.txt`.

## Screens

- **Overview:** live ticket counts, pending reviews, reviewed tickets, feedback entries, original routing/priority charts and recent tickets. An empty workspace links to ticket submission.
- **New ticket:** submits customer text, saves the result through the API and shows intent, department, rule-based priority, uncalibrated model score, review reasons and audit details. The submitted message remains available if a request fails. A successful submission links directly to ticket review.
- **Ticket review:** filters and paginates tickets, displays original text and decisions, and lets a reviewer confirm/correct intent, optionally correct priority/department and add a note. Feedback history remains separate from the original prediction. Saving a review refreshes the queue; reviewed tickets remain available under All tickets.

The review filter resets pagination to page one when changed. Each page contains at most 20 tickets. The Refresh workspace button fetches current API data; API results are not cached. Feedback never triggers retraining, and scores are not presented as calibrated confidence.

## Verification

Streamlit AppTest simulates widget interactions against a temporary FastAPI/SQLite stack. It checks empty navigation, blank-input rejection, ticket creation, correction submission, original-result preservation, queue refresh, populated charts and backend-unavailable rendering. The actual trained-model flow is checked separately through HTTP against an isolated verification database.

AppTest checks widget state and data flow; it is not a visual accessibility audit. A real headless Edge desktop overview screenshot was subsequently captured and inspected. Hosted mode can enable a shared-password gate using `SUPPORT_DASHBOARD_PASSWORD`; multi-user identity and roles remain unimplemented.

Reference: [Streamlit AppTest documentation](https://docs.streamlit.io/develop/api-reference/app-testing/st.testing.v1.apptest).
