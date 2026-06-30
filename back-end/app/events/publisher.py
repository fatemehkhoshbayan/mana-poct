"""Vendor-agnostic event publisher interface — the only surface outbox.py sees.

Mirrors the app/llm/ and app/observability/ pattern: an abstract `EventPublisher`,
several concrete implementations, and a `get_publisher()` factory that fans out to
whichever sinks are configured.
"""

from __future__ import annotations

from typing import Any


class EventPublisher:
    """Abstract sink for outbox events. Implementations live in app/events/."""

    name: str = "base"

    async def publish(self, event_type: str, payload: dict[str, Any]) -> None:
        raise NotImplementedError
