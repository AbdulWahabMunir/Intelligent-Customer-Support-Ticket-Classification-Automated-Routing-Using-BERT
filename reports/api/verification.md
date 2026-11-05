# Verification: ticket API, persistence and feedback

Story: submit a ticket over HTTP, classify and route it with the completed DistilBERT checkpoint, persist the original decision in SQLite, record human feedback and retrieve the unchanged original plus its review history.

| Boundary | Status | Evidence |
| --- | --- | --- |
| Server startup and dependencies | Passed | Uvicorn reported application startup complete; pip check reported no broken requirements |
| Interactive API entry point | HTTP verified | `/docs` returned 200 and `/openapi.json` contained ticket and feedback contracts; browser rendering was not tested |
| HTTP to classifier and routing | Passed | `/predict` returned 200 and predicted `track_refund`; loaded version `distilbert:130e8686af8b` |
| API to SQLite | Passed | Two ticket requests returned 201; direct SQLite readback matched the original response snapshot |
| Review queue and human feedback | Passed | Vague `help` ticket entered review; three feedback requests returned 201; reviewed ticket left outstanding queue |
| Feedback to retrieval | Passed | Two corrections remained ordered; original result stayed identical; training status remained pending |
| Error responses | Passed | Invalid ticket/unknown intent returned 422; nonexistent ticket returned 404 |
| Restart persistence and contract edge cases | Passed | Automated tests used a second app instance over the same database and checked pagination, SQL characters, schema errors and immutable results |

All **26 automated tests** passed. API contract tests inject a deterministic classifier and temporary SQLite databases. The real HTTP flow separately used the trained DistilBERT checkpoint and `data/runtime/verification.sqlite3`; its aggregate evidence is in `http_verification.json`. Verification tickets are separate from the default main database.

No dashboard, browser interaction, public deployment, authentication or automatic retraining was tested or implemented in this stage. The server remains a local single-user prototype. Classifier scores remain uncalibrated.
