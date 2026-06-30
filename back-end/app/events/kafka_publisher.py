"""Kafka publisher — real event-bus dispatch (Slice 6 stretch goal).

Uses `aiokafka` against any Kafka-API-compatible broker. The bundled docker-compose
`kafka` profile runs a single-node, KRaft-mode Apache Kafka container (free,
Apache-2.0, no ZooKeeper needed) so this is free and quick to stand up locally.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from app.events.publisher import EventPublisher

logger = logging.getLogger(__name__)


class KafkaPublisher(EventPublisher):
    name = "kafka"

    def __init__(self, bootstrap_servers: str, topic: str) -> None:
        self._bootstrap_servers = bootstrap_servers
        self._topic = topic
        self._producer = None  # lazily started on first publish

    async def _get_producer(self):
        if self._producer is None:
            from aiokafka import AIOKafkaProducer  # noqa: PLC0415

            self._producer = AIOKafkaProducer(
                bootstrap_servers=self._bootstrap_servers,
                value_serializer=lambda v: json.dumps(v).encode("utf-8"),
            )
            await self._producer.start()
        return self._producer

    async def publish(self, event_type: str, payload: dict[str, Any]) -> None:
        producer = await self._get_producer()
        key = (payload.get("device_serial") or payload.get("session_id") or "").encode(
            "utf-8"
        )
        await producer.send_and_wait(
            self._topic,
            value={"event_type": event_type, **payload},
            key=key or None,
        )
        logger.info("kafka: published %s to topic=%s", event_type, self._topic)

    async def close(self) -> None:
        if self._producer is not None:
            await self._producer.stop()
