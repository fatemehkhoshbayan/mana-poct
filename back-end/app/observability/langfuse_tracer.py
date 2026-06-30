"""LangFuse-backed Tracer (OTEL-based Python SDK v4).

See https://langfuse.com/docs/observability/sdk/instrumentation — observations are
created with `start_as_current_observation()` so child spans/generations nest
automatically via the active OpenTelemetry context, and trace-level attributes
(session_id, tags) are correlated via `propagate_attributes()`.
"""

from __future__ import annotations

import logging
from contextlib import contextmanager
from typing import Any, Iterator

from app.config import settings
from app.observability.tracer import TraceHandle, Tracer

logger = logging.getLogger(__name__)


class _LangfuseHandle(TraceHandle):
    def __init__(self, observation: Any) -> None:
        self._observation = observation

    def update(self, **kwargs: Any) -> None:
        try:
            self._observation.update(**kwargs)
        except Exception:
            logger.debug("LangFuse observation.update() failed", exc_info=True)


class LangfuseTracer(Tracer):
    name = "langfuse"

    def __init__(self) -> None:
        from langfuse import Langfuse  # noqa: PLC0415

        self._client = Langfuse(
            public_key=settings.LANGFUSE_PUBLIC_KEY,
            secret_key=settings.LANGFUSE_SECRET_KEY,
            host=settings.LANGFUSE_HOST,
        )

    @contextmanager
    def start_turn(
        self, *, session_id: str, tenant_id: str, user_message: str
    ) -> Iterator[TraceHandle]:
        from langfuse import propagate_attributes  # noqa: PLC0415

        try:
            with propagate_attributes(
                trace_name="qc_turn",
                session_id=session_id,
                tags=[f"tenant:{tenant_id}"],
            ):
                with self._client.start_as_current_observation(
                    as_type="span",
                    name="qc_turn",
                    input={"user_message": user_message},
                ) as span:
                    yield _LangfuseHandle(span)
        except Exception:
            logger.debug("LangFuse start_turn failed — tracing skipped", exc_info=True)
            yield TraceHandle()

    @contextmanager
    def start_generation(self, *, name: str, model: str, input: Any) -> Iterator[TraceHandle]:
        try:
            with self._client.start_as_current_observation(
                as_type="generation",
                name=name,
                model=model,
                input=input,
            ) as generation:
                yield _LangfuseHandle(generation)
        except Exception:
            logger.debug("LangFuse start_generation failed — tracing skipped", exc_info=True)
            yield TraceHandle()

    @contextmanager
    def start_span(self, *, name: str, input: Any) -> Iterator[TraceHandle]:
        try:
            with self._client.start_as_current_observation(
                as_type="span",
                name=name,
                input=input,
            ) as span:
                yield _LangfuseHandle(span)
        except Exception:
            logger.debug("LangFuse start_span failed — tracing skipped", exc_info=True)
            yield TraceHandle()

    def flush(self) -> None:
        try:
            self._client.flush()
        except Exception:
            logger.debug("LangFuse flush failed", exc_info=True)
