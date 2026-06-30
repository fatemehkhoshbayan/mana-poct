"""Default tracer when no LangFuse credentials are configured (mirrors llm/fake.py)."""

from __future__ import annotations

from contextlib import contextmanager
from typing import Any, Iterator

from app.observability.tracer import TraceHandle, Tracer


class NoopTracer(Tracer):
    name = "noop"

    @contextmanager
    def start_turn(self, **_kwargs: Any) -> Iterator[TraceHandle]:
        yield TraceHandle()

    @contextmanager
    def start_generation(self, **_kwargs: Any) -> Iterator[TraceHandle]:
        yield TraceHandle()

    @contextmanager
    def start_span(self, **_kwargs: Any) -> Iterator[TraceHandle]:
        yield TraceHandle()

    def flush(self) -> None:
        pass
