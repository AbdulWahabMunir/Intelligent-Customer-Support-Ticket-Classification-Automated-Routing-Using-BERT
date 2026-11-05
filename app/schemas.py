"""Validated API contracts; corrected categories are derived server-side."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from src.inference import validate_text

Priority = Literal["Critical", "High", "Medium", "Low"]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class TicketCreate(StrictModel):
    text: str = Field(min_length=1, max_length=10000)

    @field_validator("text")
    @classmethod
    def valid_text(cls, value):
        return validate_text(value)


class PredictionOut(StrictModel):
    intent: str
    category: str
    score: float
    margin: float
    model_version: str
    truncated: bool


class ResultOut(StrictModel):
    prediction: PredictionOut
    department: str
    priority: Priority
    priority_source: Literal["business_rules"]
    priority_reason: str
    routing_reason: str
    requires_review: bool
    review_reasons: list[str]
    policy_version: str
    score_calibrated: Literal[False]
    latency_ms: float


class TicketOut(StrictModel):
    id: UUID
    created_at: datetime
    text: str
    result: ResultOut
    feedback_count: int
    review_status: Literal["reviewed", "needs_review", "not_required"]


class TicketPage(StrictModel):
    items: list[TicketOut]
    total: int
    limit: int
    offset: int


class FeedbackCreate(StrictModel):
    corrected_intent: str = Field(min_length=1, max_length=100)
    corrected_priority: Priority | None = None
    corrected_department: str | None = Field(default=None, min_length=1, max_length=100)
    note: str = Field(default="", max_length=2000)
    reviewer: str | None = Field(default=None, min_length=1, max_length=80)


class FeedbackOut(FeedbackCreate):
    id: UUID
    ticket_id: UUID
    created_at: datetime
    corrected_category: str
    training_status: Literal["pending"]


class FeedbackSubmission(FeedbackCreate):
    ticket_id: UUID


class AnalyticsOut(StrictModel):
    tickets: int
    reviewed_tickets: int
    pending_review: int
    feedback_entries: int
    original_departments: dict[str, int]
    original_priorities: dict[str, int]
    corrected_tickets: int = 0
    correction_rate: float = 0
    corrected_intents: dict[str, int] = Field(default_factory=dict)
    review_activity_by_day: dict[str, dict[str, int]] = Field(default_factory=dict)
