from __future__ import annotations

import json
import logging
import uuid
from datetime import date as _date
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sse_starlette import EventSourceResponse

from app.db.models import Extraction, Message, QcDecision, Session
from app.db.session import get_session
from app.domain.variables import (
    derive_consumable,
    derive_eqa,
    derive_historical,
    derive_storage,
)
from app.llm.factory import get_provider
from app.orchestration.orchestrator import (
    DecisionEvent,
    ErrorEvent,
    Orchestrator,
    StateEvent,
    TokenEvent,
)
from app.orchestration.prompts import GREETING
from app.schemas.api import (
    CreateSessionResponse,
    SendMessageRequest,
    SessionDetail,
    SessionMessage,
)
from app.schemas.domain import ExtractionState, FsmState
from app.schemas.llm import LlmMessage

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/sessions", tags=["sessions"])


# ---------------------------------------------------------------------------
# POST /api/sessions  — create a new session
# ---------------------------------------------------------------------------


@router.post(
    "",
    response_model=CreateSessionResponse,
    summary="Create a new QC session",
    description="Creates a conversation session and returns the greeting message.",
)
async def create_session(
    x_tenant_id: str = Header(default="demo", alias="X-Tenant-ID"),
    db: AsyncSession = Depends(get_session),
) -> CreateSessionResponse:
    session_id = str(uuid.uuid4())

    session = Session(
        id=session_id,
        tenant_id=x_tenant_id,
        status="active",
        fsm_state=FsmState.GREETING.value,
    )
    db.add(session)

    greeting_msg = Message(
        id=str(uuid.uuid4()),
        session_id=session_id,
        role="assistant",
        content=GREETING,
    )
    db.add(greeting_msg)

    # Persist initial empty extraction state
    extraction = Extraction(
        id=str(uuid.uuid4()),
        session_id=session_id,
        state=ExtractionState().model_dump(mode="json"),
    )
    db.add(extraction)

    await db.commit()
    logger.info("create_session: session_id=%s  tenant=%s", session_id, x_tenant_id)

    return CreateSessionResponse(
        session_id=session_id,
        state=FsmState.GREETING,
        greeting=GREETING,
    )


# ---------------------------------------------------------------------------
# POST /api/sessions/{id}/messages  — stream a turn
# ---------------------------------------------------------------------------


@router.post(
    "/{session_id}/messages",
    summary="Send a message and stream the assistant reply",
    description="""
Streams the assistant's reply as Server-Sent Events.

**SSE event types:**
- `token` — raw text chunk (not JSON); append to the streaming bubble
- `state` — JSON `ExtractionState` + `{current_state, current_objective}`; drives ProgressPanel
- `decision` — JSON `Decision`; rendered as the final DecisionCard
- `error` — JSON `{message}`; show inline
- `done` — `[DONE]` (not JSON); end of turn
""",
)
async def send_message(
    session_id: str,
    body: SendMessageRequest,
    x_tenant_id: str = Header(default="demo", alias="X-Tenant-ID"),
    db: AsyncSession = Depends(get_session),
) -> EventSourceResponse:
    # Load session
    session = await db.get(Session, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Load message history
    result = await db.execute(
        select(Message).where(Message.session_id == session_id).order_by(Message.created_at)
    )
    db_messages = result.scalars().all()
    history = _db_messages_to_llm(db_messages)

    # Load latest extraction state
    ext_result = await db.execute(
        select(Extraction)
        .where(Extraction.session_id == session_id)
        .order_by(Extraction.created_at.desc())
        .limit(1)
    )
    ext_row = ext_result.scalar_one_or_none()
    extraction = (
        ExtractionState.model_validate(ext_row.state) if ext_row else ExtractionState()
    )

    # Persist user message
    user_msg_id = str(uuid.uuid4())
    db.add(
        Message(
            id=user_msg_id,
            session_id=session_id,
            role="user",
            content=body.message,
        )
    )
    await db.commit()

    async def generate():
        nonlocal extraction

        provider = get_provider()
        orchestrator = Orchestrator(provider)

        logger.info(
            "send_message: session=%s  user_msg=%r  provider=%s",
            session_id,
            body.message[:80],
            provider.name,
        )

        assistant_text = ""
        input_tokens = 0
        output_tokens = 0

        try:
            async for event in orchestrator.handle_turn(
                session_id=session_id,
                tenant_id=x_tenant_id,
                history=history,
                user_message=body.message,
                extraction=extraction,
            ):
                if isinstance(event, TokenEvent):
                    assistant_text += event.text
                    yield {"event": "token", "data": event.text}

                elif isinstance(event, StateEvent):
                    extraction = event.extraction
                    today = _date.today()
                    ext = event.extraction
                    variable_statuses: dict[str, str] = {}
                    if ext.consumable_known:
                        variable_statuses["consumable_status"] = (
                            derive_consumable(ext.consumable, today).value
                        )
                    if ext.storage_known:
                        variable_statuses["storage_condition"] = (
                            derive_storage(ext.storage).value
                        )
                    if ext.historical_known:
                        variable_statuses["historical_error_flag"] = (
                            derive_historical(ext.historical).value
                        )
                    if ext.eqa_known:
                        variable_statuses["eqa_status"] = derive_eqa(ext.eqa, today).value
                    state_payload = {
                        **event.extraction.model_dump(mode="json"),
                        "current_state": event.current_state.value,
                        "current_objective": event.current_objective,
                        "variable_statuses": variable_statuses,
                    }
                    yield {"event": "state", "data": json.dumps(state_payload)}

                elif isinstance(event, DecisionEvent):
                    d = event.decision

                    # Persist decision
                    async with db.begin():
                        db.add(
                            QcDecision(
                                id=str(uuid.uuid4()),
                                session_id=session_id,
                                scenario=d.scenario.value,
                                system_action=d.system_action,
                                is_qc_locked=d.is_qc_locked,
                                payload=d.model_dump(mode="json"),
                            )
                        )
                        # Update session status
                        session.status = "resolved"
                        session.fsm_state = "RESOLVED"
                        session.resolved_at = datetime.now(tz=timezone.utc).replace(tzinfo=None)
                        db.add(session)

                    yield {"event": "decision", "data": d.model_dump_json()}

                elif isinstance(event, ErrorEvent):
                    yield {"event": "error", "data": json.dumps({"message": event.message})}

        except GeneratorExit:
            return
        except Exception as exc:
            logger.exception("Orchestrator error in session %s", session_id)
            yield {"event": "error", "data": json.dumps({"message": str(exc)})}
        finally:
            # Persist assistant reply and updated extraction
            try:
                async with db.begin():
                    db.add(
                        Message(
                            id=str(uuid.uuid4()),
                            session_id=session_id,
                            role="assistant",
                            content=assistant_text,
                            input_tokens=input_tokens or None,
                            output_tokens=output_tokens or None,
                        )
                    )
                    db.add(
                        Extraction(
                            id=str(uuid.uuid4()),
                            session_id=session_id,
                            state=extraction.model_dump(mode="json"),
                        )
                    )
            except Exception:
                logger.exception("Failed to persist turn for session %s", session_id)

            yield {"event": "done", "data": "[DONE]"}

    return EventSourceResponse(generate(), headers={"X-Accel-Buffering": "no"})


# ---------------------------------------------------------------------------
# GET /api/sessions/{id}
# ---------------------------------------------------------------------------


@router.get(
    "/{session_id}",
    response_model=SessionDetail,
    summary="Get full session state",
)
async def get_session_detail(
    session_id: str,
    db: AsyncSession = Depends(get_session),
) -> SessionDetail:
    session = await db.get(Session, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    msg_result = await db.execute(
        select(Message).where(Message.session_id == session_id).order_by(Message.created_at)
    )
    messages = msg_result.scalars().all()

    ext_result = await db.execute(
        select(Extraction)
        .where(Extraction.session_id == session_id)
        .order_by(Extraction.created_at.desc())
        .limit(1)
    )
    ext_row = ext_result.scalar_one_or_none()

    dec_result = await db.execute(
        select(QcDecision)
        .where(QcDecision.session_id == session_id)
        .order_by(QcDecision.created_at.desc())
        .limit(1)
    )
    dec_row = dec_result.scalar_one_or_none()

    from app.schemas.domain import Decision  # noqa: PLC0415

    return SessionDetail(
        session_id=session.id,
        tenant_id=session.tenant_id,
        fsm_state=FsmState(session.fsm_state),
        status=session.status,
        device_serial=session.device_serial,
        lot_number=session.lot_number,
        created_at=session.created_at.isoformat(),
        updated_at=session.updated_at.isoformat(),
        resolved_at=session.resolved_at.isoformat() if session.resolved_at else None,
        messages=[
            SessionMessage(
                id=m.id,
                session_id=m.session_id,
                role=m.role,
                content=m.content,
                created_at=m.created_at.isoformat(),
            )
            for m in messages
        ],
        extraction=ExtractionState.model_validate(ext_row.state) if ext_row else None,
        decision=Decision.model_validate(dec_row.payload) if dec_row else None,
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _db_messages_to_llm(db_messages: list[Message]) -> list[LlmMessage]:
    result = []
    for m in db_messages:
        if m.role == "tool":
            result.append(
                LlmMessage(
                    role="tool",
                    content=m.content,
                    tool_call_id=(m.tool_results or {}).get("tool_call_id"),
                )
            )
        else:
            result.append(LlmMessage(role=m.role, content=m.content))
    return result
