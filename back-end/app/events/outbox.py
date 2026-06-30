"""Transactional outbox + background relay.

`write_outbox_event` must be called inside the SAME DB transaction that writes
the triggering decision row — that's what makes the dispatch atomic (the event
either commits with the decision or not at all; no dual-write problem).

`relay_loop` is a separate, decoupled step: it polls for unpublished rows and
hands them to whichever `EventPublisher` is configured, marking each row
published only on success. A publish failure leaves the row unpublished so the
next pass retries it — the durability guarantee a real Kafka Connect / Debezium
relay would give you, just running in-process for this PoC.
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Event
from app.events.publisher import EventPublisher

logger = logging.getLogger(__name__)


def write_outbox_event(
    db: AsyncSession,
    *,
    session_id: str,
    event_type: str,
    payload: dict[str, Any],
) -> Event:
    """Stage an outbox row on the given session. Caller commits (or rolls back)
    the surrounding transaction — this function only calls `db.add()`."""
    event = Event(
        id=str(uuid.uuid4()),
        session_id=session_id,
        type=event_type,
        payload=payload,
        published=False,
    )
    db.add(event)
    return event


async def drain_outbox_once(db: AsyncSession, publisher: EventPublisher) -> int:
    """Publish all unpublished outbox rows. Returns the count successfully published."""
    result = await db.execute(select(Event).where(Event.published.is_(False)))
    pending = result.scalars().all()

    published_count = 0
    for event in pending:
        try:
            await publisher.publish(event.type, event.payload)
        except Exception:
            logger.exception(
                "outbox: publish failed for event=%s type=%s — will retry next pass",
                event.id,
                event.type,
            )
            continue
        event.published = True
        db.add(event)
        published_count += 1

    if published_count:
        await db.commit()
    return published_count


async def relay_loop(
    session_factory,
    publisher: EventPublisher,
    interval_seconds: float = 3.0,
) -> None:
    """Background task: poll the outbox forever until cancelled."""
    logger.info(
        "event relay started — publisher=%s interval=%ss",
        publisher.name,
        interval_seconds,
    )
    try:
        while True:
            try:
                async with session_factory() as db:
                    count = await drain_outbox_once(db, publisher)
                    if count:
                        logger.info("event relay: published %d event(s)", count)
            except Exception:
                logger.exception("event relay: pass failed, will retry")
            await asyncio.sleep(interval_seconds)
    except asyncio.CancelledError:
        logger.info("event relay stopped")
        raise
