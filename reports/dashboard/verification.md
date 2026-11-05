# Dashboard verification

Story: a reviewer submits a ticket in Streamlit, the dashboard calls FastAPI over HTTP, DistilBERT classifies it, SQLite stores the result, and the reviewer records feedback without changing the original prediction.

| Boundary | Result | Evidence |
| --- | --- | --- |
| Dashboard startup | Passed | Streamlit served on `127.0.0.1:8501`; root HTML and health endpoint returned 200 |
| UI navigation and empty state | Passed | AppTest rendered zero-count overview and navigated to the new-ticket form |
| Form validation | Passed | Blank messages showed a validation error and saved no ticket |
| UI to real HTTP API | Passed | AppTest submitted an authored `help` ticket to the isolated API on port 8001 using the actual dashboard HTTP client |
| API to trained model and SQLite | Passed | Model `distilbert:130e8686af8b` flagged the vague request for review; its original result was persisted |
| Feedback form to history | Passed | Intent correction saved as pending; original prediction was unchanged and direct SQLite readback found the feedback |
| Queue and analytics refresh | Passed | Reviewed ticket left the outstanding queue; overview counts and charts rendered |
| API unavailable | Passed | Simulated backend failure rendered an actionable error without a Streamlit exception |
| Main workspace isolation | Passed | The default API on port 8000 still contained zero tickets after verification |
| Browser overview | Passed for desktop overview | A real headless Edge capture waited for rendered API-connected content; `reports/screenshots/overview.png` was inspected at 1440×1100. Other browser workflows and mobile/accessibility layouts were not audited. |

All **31 automated tests** passed, including five dashboard tests. The additional real-model widget-to-HTTP flow is recorded in `verification.json`. Tests used temporary databases or `data/runtime/verification.sqlite3`; the temporary verification API was stopped afterward. The main API and dashboard remain available locally.

No public hosting, authentication, automatic retraining or visual accessibility audit was performed in this stage.
