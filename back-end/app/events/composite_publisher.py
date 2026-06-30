"""Fans an event out to multiple publishers (e.g. Kafka + ntfy + log) at once.

A single failing sink never blocks the others — each publish is isolated and
logged; the outbox relay only marks the event published once ALL sinks succeed
(so a transient failure is retried next pass, per-sink-idempotent operations
permitting).
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from app.events.publisher import EventPublisher

logger = logging.getLogger(__name__)


class CompositePublisher(EventPublisher):
    name = "composite"

    def __init__(self, publishers: list[EventPublisher]) -> None:
        self._publishers = publishers

    async def publish(self, event_type: str, payload: dict[str, Any]) -> None:
        results = await asyncio.gather(
            *(p.publish(event_type, payload) for p in self._publishers),
            return_exceptions=True,
        )
        failures = [
            (p.name, r)
            for p, r in zip(self._publishers, results)
            if isinstance(r, Exception)
        ]
        if failures:
            logger.warning(
                "composite publish: %d/%d sinks failed: %s",
                len(failures),
                len(self._publishers),
                failures,
            )
            raise failures[0][1]
