"""Local FastAPI backend. Run: python -m uvicorn app.api:app --host 127.0.0.1"""

from contextlib import asynccontextmanager
import os
import hmac
from pathlib import Path
from threading import Lock
from uuid import UUID

from fastapi import FastAPI, HTTPException, Query
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.schemas import (AnalyticsOut, FeedbackCreate, FeedbackOut, ResultOut, TicketCreate, TicketOut, TicketPage)
from app.storage import TicketStore
from src.data.inspect import ROOT
from src.inference import TicketClassifier
from src.routing import TicketService


def create_app(db_path=None, service=None):
    @asynccontextmanager
    async def lifespan(application):
        application.state.service = service if service is not None else TicketService(TicketClassifier(os.environ.get("SUPPORT_MODEL", "distilbert")))
        application.state.inference_lock = Lock()
        if db_path is None and os.environ.get("DATABASE_URL"):
            from app.postgres_storage import PostgresTicketStore
            application.state.store = PostgresTicketStore(os.environ["DATABASE_URL"])
        else:
            application.state.store = TicketStore(db_path or Path(os.environ.get("SUPPORT_DB_PATH", str(ROOT / "data/runtime/support.sqlite3"))))
        application.state.store.initialize()
        yield

    application = FastAPI(title="Intelligent Customer Support API", version="0.1.0", lifespan=lifespan,
                          description="Local ticket classification, business-rule routing and append-only human feedback.")

    @application.middleware("http")
    async def api_access(request, call_next):
        expected = os.environ.get("SUPPORT_API_KEY", "")
        if expected and request.url.path != "/health":
            provided = request.headers.get("X-API-Key", "")
            if not hmac.compare_digest(expected.encode(), provided.encode()):
                return JSONResponse(status_code=401, content={"detail": "API key required"})
        return await call_next(request)

    @application.exception_handler(RequestValidationError)
    async def validation_error(request, error):
        # Pydantic errors can echo submitted text. Return locations and messages only.
        return JSONResponse(status_code=422, content={"detail": [{"loc": list(item["loc"]), "msg": item["msg"], "type": item["type"]} for item in error.errors()]})

    @application.get("/health")
    def health():
        with application.state.store.connection() as connection:
            connection.execute("SELECT 1")
        return {"status": "ok", "model_version": application.state.service.classifier.version,
                "policy_version": application.state.service.policy.config["version"]}

    @application.get("/taxonomy")
    def taxonomy():
        policy = application.state.service.policy.config
        departments = {pair[1] for pair in policy["intents"].values()}
        departments.update(rule["department"] for rule in policy["priority_rules"] if rule.get("department"))
        departments.add(policy["review_department"])
        return {"intents": {intent: {"category": pair[0], "department": pair[1]} for intent, pair in policy["intents"].items()},
                "departments": sorted(departments), "priorities": ["Critical", "High", "Medium", "Low"]}

    def predict(body):
        # Serialize CPU inference to avoid competing Torch thread pools.
        with application.state.inference_lock:
            return application.state.service.classify_and_route(body.text)

    @application.post("/predict", response_model=ResultOut)
    def prediction(body: TicketCreate):
        return predict(body)

    @application.post("/tickets", response_model=TicketOut, status_code=201)
    def create_ticket(body: TicketCreate):
        return application.state.store.create_ticket(body.text, predict(body))

    @application.get("/tickets", response_model=TicketPage)
    def list_tickets(limit: int = Query(20, ge=1, le=100), offset: int = Query(0, ge=0), needs_review: bool | None = None):
        return application.state.store.list_tickets(limit, offset, needs_review)

    def require_ticket(ticket_id):
        ticket = application.state.store.get_ticket(ticket_id)
        if ticket is None:
            raise HTTPException(status_code=404, detail="Ticket not found")
        return ticket

    @application.get("/tickets/{ticket_id}", response_model=TicketOut)
    def get_ticket(ticket_id: UUID):
        return require_ticket(ticket_id)

    @application.post("/tickets/{ticket_id}/feedback", response_model=FeedbackOut, status_code=201)
    def add_feedback(ticket_id: UUID, body: FeedbackCreate):
        require_ticket(ticket_id)
        labels = application.state.service.policy.config["intents"]
        if body.corrected_intent not in labels:
            raise HTTPException(status_code=422, detail="Unknown corrected intent; see /taxonomy")
        if body.corrected_department is not None and body.corrected_department not in taxonomy()["departments"]:
            raise HTTPException(status_code=422, detail="Unknown corrected department; see /taxonomy")
        values = body.model_dump()
        values["corrected_category"] = labels[body.corrected_intent][0]
        return application.state.store.add_feedback(ticket_id, values)

    @application.get("/tickets/{ticket_id}/feedback", response_model=list[FeedbackOut])
    def get_feedback(ticket_id: UUID):
        require_ticket(ticket_id)
        return application.state.store.list_feedback(ticket_id)

    @application.get("/analytics", response_model=AnalyticsOut)
    def analytics():
        return application.state.store.analytics()

    return application


app = create_app()
