from __future__ import annotations

from pydantic import BaseModel, Field

from app.schemas.domain import Decision, ExtractionState, FsmState


class CreateSessionResponse(BaseModel):
    session_id: str = Field(..., examples=["550e8400-e29b-41d4-a716-446655440000"])
    state: FsmState = Field(..., examples=[FsmState.GREETING])
    greeting: str = Field(
        ...,
        examples=["Hello! I'm the MANA POCT QC Assistant. Let's work through this QC issue together."],  # noqa: E501
    )


class SendMessageRequest(BaseModel):
    message: str = Field(
        ...,
        min_length=1,
        max_length=4000,
        examples=["The reagent lot expired last week."],
    )


class SessionMessage(BaseModel):
    id: str
    session_id: str
    role: str
    content: str
    created_at: str


class SessionDetail(BaseModel):
    session_id: str
    tenant_id: str
    fsm_state: FsmState
    status: str
    device_serial: str | None = None
    lot_number: str | None = None
    created_at: str
    updated_at: str
    resolved_at: str | None = None
    messages: list[SessionMessage] = []
    extraction: ExtractionState | None = None
    decision: Decision | None = None


class HealthResponse(BaseModel):
    status: str = Field(..., examples=["ok"])
