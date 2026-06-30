"""Slice 4 — Observability tests.

Covers:
  1. NoopTracer — context managers are safe no-ops, never raise
  2. get_tracer() — selects NoopTracer when no LangFuse credentials are configured
  3. Orchestrator wiring — a spying Tracer receives turn/generation/span calls
     with the expected shape, without needing a real LangFuse backend
"""

from __future__ import annotations

from datetime import date

from app.llm.fake import FakeProvider, _record_call
from app.observability.noop_tracer import NoopTracer
from app.observability.tracer import TraceHandle, Tracer, get_tracer
from app.orchestration.orchestrator import DecisionEvent, Orchestrator, UsageEvent
from app.schemas.domain import ExtractionState
from app.schemas.llm import LlmMessage, StreamDone, TextDelta, ToolCall, ToolCallDelta, Usage

TODAY = date(2026, 6, 29)


# ---------------------------------------------------------------------------
# NoopTracer
# ---------------------------------------------------------------------------


def test_noop_tracer_start_turn_yields_handle_and_never_raises():
    t = NoopTracer()
    with t.start_turn(session_id="s1", tenant_id="demo", user_message="hi") as handle:
        assert isinstance(handle, TraceHandle)
        handle.update(output={"anything": "goes"})  # must not raise


def test_noop_tracer_start_generation_and_span():
    t = NoopTracer()
    with t.start_generation(name="gen", model="fake/model", input={"x": 1}) as gen:
        gen.update(output="text", usage_details={"input": 1, "output": 2})
    with t.start_span(name="tool:record_consumable", input={"lot_number": "LOT-1"}) as span:
        span.update(output='{"status": "recorded"}')


def test_noop_tracer_flush_is_a_noop():
    NoopTracer().flush()


# ---------------------------------------------------------------------------
# get_tracer() selection
# ---------------------------------------------------------------------------


def test_get_tracer_defaults_to_noop_without_langfuse_keys():
    # Test env never sets LANGFUSE_PUBLIC_KEY/SECRET_KEY (see Settings defaults)
    assert isinstance(get_tracer(), NoopTracer)


# ---------------------------------------------------------------------------
# Orchestrator <-> Tracer wiring
# ---------------------------------------------------------------------------


class _SpyTracer(Tracer):
    """Records every start_* call so tests can assert on shape without a real backend."""

    name = "spy"

    def __init__(self) -> None:
        self.turns: list[dict] = []
        self.generations: list[dict] = []
        self.spans: list[dict] = []
        self.flushed = False

    class _Handle(TraceHandle):
        def __init__(self, sink: dict) -> None:
            self._sink = sink

        def update(self, **kwargs) -> None:
            self._sink["updates"].append(kwargs)

    def start_turn(self, **kwargs):
        record = {"kwargs": kwargs, "updates": []}
        self.turns.append(record)
        return self._cm(record)

    def start_generation(self, **kwargs):
        record = {"kwargs": kwargs, "updates": []}
        self.generations.append(record)
        return self._cm(record)

    def start_span(self, **kwargs):
        record = {"kwargs": kwargs, "updates": []}
        self.spans.append(record)
        return self._cm(record)

    def flush(self) -> None:
        self.flushed = True

    @staticmethod
    def _cm(record: dict):
        from contextlib import contextmanager

        @contextmanager
        def _inner():
            yield _SpyTracer._Handle(record)

        return _inner()


async def test_orchestrator_emits_tracer_spans_for_turn_generation_and_tools():
    spy = _SpyTracer()
    provider = FakeProvider(
        script=[
            _record_call(
                "record_consumable",
                {
                    "lot_number": "LOT-E",
                    "lot_expiry_date": "2026-12-31",
                    "open_vial_age_days": 5,
                },
            )
        ]
    )
    orchestrator = Orchestrator(provider, tracer=spy)

    decision: DecisionEvent | None = None
    async for event in orchestrator.handle_turn(
        session_id="test-session",
        tenant_id="demo",
        history=[LlmMessage(role="user", content="Start")],
        user_message="Lot LOT-E, expiry 2026-12-31, opened 5 days ago",
        extraction=ExtractionState(),
        today=TODAY,
    ):
        if isinstance(event, DecisionEvent):
            decision = event

    # One turn span, opened with session/tenant/user_message and closed with an output
    assert len(spy.turns) == 1
    assert spy.turns[0]["kwargs"]["session_id"] == "test-session"
    assert spy.turns[0]["kwargs"]["tenant_id"] == "demo"
    assert spy.turns[0]["updates"], "turn span should be updated with a final output"

    # At least one LLM generation span was opened (one per iteration)
    assert len(spy.generations) >= 1
    assert spy.generations[0]["kwargs"]["model"] == provider.model

    # One tool span for the record_consumable call
    assert any(s["kwargs"]["name"] == "tool:record_consumable" for s in spy.spans)

    # Decision was reached (consumable-only happy path does not resolve early,
    # but this asserts the wiring did not interfere with normal orchestration)
    assert decision is None or decision.decision is not None


async def test_orchestrator_emits_usage_events_when_provider_reports_usage():
    provider = FakeProvider(
        script=[
            [
                TextDelta("hi"),
                ToolCallDelta(
                    call=ToolCall(id="1", name="record_historical", arguments={
                        "consecutive_qc_failures_30d": 0
                    })
                ),
                Usage(input_tokens=42, output_tokens=7),
                StreamDone(),
            ]
        ]
    )
    orchestrator = Orchestrator(provider, tracer=NoopTracer())

    usage_events: list[UsageEvent] = []
    async for event in orchestrator.handle_turn(
        session_id="test-session",
        tenant_id="demo",
        history=[LlmMessage(role="user", content="Start")],
        user_message="no failures",
        extraction=ExtractionState(),
        today=TODAY,
    ):
        if isinstance(event, UsageEvent):
            usage_events.append(event)

    assert usage_events == [UsageEvent(input_tokens=42, output_tokens=7)]
