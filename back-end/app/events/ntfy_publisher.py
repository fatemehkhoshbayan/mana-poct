"""ntfy.sh publisher — a real, free, zero-signup push notification.

Viewing it requires no setup at all: open https://ntfy.sh/<topic> in any browser
(or the ntfy mobile app) and the notification appears live, no account needed.
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

from app.events.publisher import EventPublisher

logger = logging.getLogger(__name__)


class NtfyPublisher(EventPublisher):
    name = "ntfy"

    def __init__(self, topic: str, server: str = "https://ntfy.sh") -> None:
        self._url = f"{server.rstrip('/')}/{topic}"

    async def publish(self, event_type: str, payload: dict[str, Any]) -> None:
        device = (
            payload.get("device_serial")
            or payload.get("lot_number")
            or "unknown device"
        )
        action = payload.get("system_action", event_type)
        message = (
            f"Device/Lot: {device}\n"
            f"Action: {action}\n"
            f"Session: {payload.get('session_id', '?')}"
        )
        title = f"MANA POCT - {event_type}".encode("ascii", errors="replace").decode(
            "ascii"
        )
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                await client.post(
                    self._url,
                    content=message.encode("utf-8"),
                    headers={
                        "Title": title,
                        "Priority": "urgent",
                        "Tags": "rotating_light",
                    },
                )
            logger.info("ntfy: published %s to %s", event_type, self._url)
        except Exception:
            logger.exception("ntfy: failed to publish %s", event_type)
            raise
