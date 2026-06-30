"""Default publisher — a structured log line. Always-on fallback (mirrors FakeProvider)."""

from __future__ import annotations

import logging
from typing import Any

from app.events.publisher import EventPublisher

logger = logging.getLogger("app.events.hardblock")


class LogPublisher(EventPublisher):
    name = "log"

    async def publish(self, event_type: str, payload: dict[str, Any]) -> None:
        logger.warning("EVENT %s  payload=%s", event_type, payload)
