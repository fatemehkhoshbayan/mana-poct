"""Vendor-agnostic observability interface — the only surface orchestration/api code sees.

Mirrors the app/llm/ pattern: a base `Tracer` class, a `NoopTracer` default, and a real
`LangfuseTracer` chosen by `get_tracer()` depending on whether credentials are configured.
"""

from __future__ import annotations

from contextlib import contextmanager
from typing import Any, Iterator


class TraceHandle:
    """Handle yielded by a tracer's `start_*` context managers.

    Safe to call `.update()` on unconditionally — the no-op implementation simply
    discards the call, so orchestration code never has to branch on whether tracing
    is enabled.
    """

    def update(self, **kwargs: Any) -> None:
        pass


class Tracer:
    """Abstract observability interface."""

    name: str = "base"

    @contextmanager
    def start_turn(
        self, *, session_id: str, tenant_id: str, user_message: str
    ) -> Iterator[TraceHandle]:
        """Wrap one full dialogue turn (one `handle_turn()` call) as a trace."""
        raise NotImplementedError
        yield  # pragma: no cover — makes this a generator for typing purposes

    @contextmanager
    def start_generation(
        self, *, name: str, model: str, input: Any
    ) -> Iterator[TraceHandle]:
        """Wrap a single LLM stream call as a generation observation."""
        raise NotImplementedError
        yield  # pragma: no cover

    @contextmanager
    def start_span(self, *, name: str, input: Any) -> Iterator[TraceHandle]:
        """Wrap a non-LLM unit of work (e.g. a tool execution) as a span."""
        raise NotImplementedError
        yield  # pragma: no cover

    def flush(self) -> None:
        raise NotImplementedError


def get_tracer() -> Tracer:
    """Return LangfuseTracer when credentials are configured, else NoopTracer."""
    from app.config import settings  # noqa: PLC0415

    if settings.has_langfuse:
        try:
            from app.observability.langfuse_tracer import LangfuseTracer  # noqa: PLC0415

            return LangfuseTracer()
        except Exception:  # pragma: no cover — fall back if the SDK/client can't init
            import logging

            logging.getLogger(__name__).exception(
                "Failed to initialize LangfuseTracer — falling back to NoopTracer"
            )

    from app.observability.noop_tracer import NoopTracer  # noqa: PLC0415

    return NoopTracer()


_singleton: Tracer | None = None


def __getattr__(attr_name: str) -> Tracer:
    """Lazily build the module-level `tracer` singleton on first access.

    Avoids a circular import at module-load time: `noop_tracer.py` /
    `langfuse_tracer.py` both import the `Tracer` base class from this module,
    so `get_tracer()` must not run until those modules can be imported cleanly.
    """
    global _singleton
    if attr_name == "tracer":
        if _singleton is None:
            _singleton = get_tracer()
        return _singleton
    raise AttributeError(f"module {__name__!r} has no attribute {attr_name!r}")
