from __future__ import annotations

from app.events.publisher import EventPublisher


def get_publisher() -> EventPublisher:
    """Build the publisher fan-out from configured settings.

    `LogPublisher` always runs (free audit trail). `NtfyPublisher` and
    `KafkaPublisher` are added on top when their settings are configured —
    mirrors `llm/factory.py` / `observability/tracer.py`'s opt-in pattern.
    """
    from app.config import settings  # noqa: PLC0415
    from app.events.composite_publisher import CompositePublisher  # noqa: PLC0415
    from app.events.log_publisher import LogPublisher  # noqa: PLC0415

    sinks: list[EventPublisher] = [LogPublisher()]

    if settings.has_ntfy:
        from app.events.ntfy_publisher import NtfyPublisher  # noqa: PLC0415

        sinks.append(
            NtfyPublisher(topic=settings.NTFY_TOPIC, server=settings.NTFY_SERVER)
        )

    if settings.has_kafka:
        from app.events.kafka_publisher import KafkaPublisher  # noqa: PLC0415

        sinks.append(
            KafkaPublisher(
                bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
                topic=settings.KAFKA_TOPIC,
            )
        )

    return sinks[0] if len(sinks) == 1 else CompositePublisher(sinks)
