"""FakeProvider — replays a scripted sequence of StreamEvents.
Used in tests and when OPENROUTER_API_KEY is not set.
"""

from __future__ import annotations

from typing import AsyncIterator

from app.llm.base import LLMProvider
from app.schemas.llm import (
    LlmMessage,
    StreamDone,
    TextDelta,
    ToolCall,
    ToolCallDelta,
    ToolSpec,
    Usage,
)

# ---------------------------------------------------------------------------
# Canned scripts for each happy-path scenario (used by tests)
# ---------------------------------------------------------------------------

_GREET = [TextDelta("Hello! Let's work through this QC issue. "), StreamDone()]

# Record-only scripts: each emits one tool call then a closing text delta.

def _record_call(name: str, args: dict) -> list:
    return [
        ToolCallDelta(call=ToolCall(id=f"fake-{name}", name=name, arguments=args)),
        StreamDone(),
    ]


SCENARIO_SCRIPTS: dict[str, list[list]] = {
    # Scenario A — expired lot
    "A": [
        _GREET,
        _record_call("record_consumable", {
            "lot_number": "LOT-A",
            "lot_expiry_date": "2026-06-01",
            "open_vial_age_days": 5,
        }),
        _record_call("record_storage", {"storage_type": "refrigerated"}),
        _record_call("record_historical", {"consecutive_qc_failures_30d": 0}),
        _record_call("record_eqa", {"has_active_cycle": False}),
    ],
    # Scenario E — all clear
    "E": [
        _GREET,
        _record_call("record_consumable", {
            "lot_number": "LOT-E",
            "lot_expiry_date": "2026-12-31",
            "open_vial_age_days": 5,
        }),
        _record_call("record_storage", {"storage_type": "refrigerated"}),
        _record_call("record_historical", {"consecutive_qc_failures_30d": 0}),
        _record_call("record_eqa", {"has_active_cycle": False}),
    ],
}


class FakeProvider(LLMProvider):
    """
    Replays a fixed list of StreamEvents per call.
    Pass `script` as a list of StreamEvent lists (one per turn) or a flat list
    for a single-turn scenario.
    """

    name = "fake"
    model = "fake/scripted"

    def __init__(self, script: list | None = None) -> None:
        # script is a list of turn-scripts; each turn-script is a list of events
        self._turns: list[list] = script or [_GREET]
        self._call_count = 0

    async def stream(
        self,
        *,
        system: str,
        messages: list[LlmMessage],
        tools: list[ToolSpec],
    ) -> AsyncIterator[TextDelta | ToolCallDelta | Usage | StreamDone]:
        if self._call_count < len(self._turns):
            turn = self._turns[self._call_count]
        else:
            turn = [TextDelta("Done."), StreamDone()]
        self._call_count += 1

        for event in turn:
            yield event
