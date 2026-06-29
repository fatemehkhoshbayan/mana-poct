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


def _record_call(name: str, args: dict) -> list:
    """Single tool call turn — no text, just one tool call then done."""
    return [
        ToolCallDelta(call=ToolCall(id=f"fake-{name}", name=name, arguments=args)),
        StreamDone(),
    ]


def _multi_record_call(*calls: tuple[str, dict]) -> list:
    """Multiple tool calls in a single turn (simulates out-of-order recording)."""
    events: list = []
    for name, args in calls:
        events.append(
            ToolCallDelta(call=ToolCall(id=f"fake-{name}", name=name, arguments=args))
        )
    events.append(StreamDone())
    return events


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
    # Slice 3: out-of-order — operator volunteers storage + consumable in one message.
    # No greeting turn — each list entry maps directly to one handle_turn() call.
    "OUT_OF_ORDER": [
        # Turn 1: LLM records BOTH consumable AND storage from one message
        _multi_record_call(
            ("record_consumable", {
                "lot_number": "LOT-E",
                "lot_expiry_date": "2026-12-31",
                "open_vial_age_days": 5,
            }),
            ("record_storage", {
                "storage_type": "refrigerated",
                "freeze_indicator_tripped": False,
            }),
        ),
        # Turn 2: historical
        _record_call("record_historical", {"consecutive_qc_failures_30d": 0}),
        # Turn 3: EQA
        _record_call("record_eqa", {"has_active_cycle": False}),
    ],
    # Slice 3: correction — operator first gives wrong expiry, then corrects it.
    # No greeting turn.
    "CORRECTION_PASS_TO_FAIL": [
        # Turn 1: records consumable with initially valid expiry (PASS)
        _record_call("record_consumable", {
            "lot_number": "LOT-C",
            "lot_expiry_date": "2026-12-31",
            "open_vial_age_days": 5,
        }),
        # Turn 2: operator corrects the expiry to an expired date (FAIL)
        _record_call("record_consumable", {
            "lot_number": "LOT-C",
            "lot_expiry_date": "2026-01-01",
            "open_vial_age_days": 5,
        }),
        # Remaining turns are never reached — early resolution fires after turn 2
        _record_call("record_storage", {"storage_type": "refrigerated"}),
        _record_call("record_historical", {"consecutive_qc_failures_30d": 0}),
        _record_call("record_eqa", {"has_active_cycle": False}),
    ],
    # Slice 3: correction — operator first gives expired lot (FAIL), then corrects to valid.
    # No greeting turn.
    "CORRECTION_FAIL_TO_PASS": [
        # Turn 1: records consumable with expired lot (FAIL)
        _record_call("record_consumable", {
            "lot_number": "LOT-C",
            "lot_expiry_date": "2026-01-01",
            "open_vial_age_days": 5,
        }),
        # Turn 2: operator corrects to valid expiry
        _record_call("record_consumable", {
            "lot_number": "LOT-C",
            "lot_expiry_date": "2026-12-31",
            "open_vial_age_days": 5,
        }),
        # Turn 3: storage
        _record_call("record_storage", {
            "storage_type": "refrigerated",
            "freeze_indicator_tripped": False,
        }),
        # Turn 4: historical
        _record_call("record_historical", {"consecutive_qc_failures_30d": 0}),
        # Turn 5: EQA
        _record_call("record_eqa", {"has_active_cycle": False}),
    ],
}


class FakeProvider(LLMProvider):
    """
    Replays a fixed list of StreamEvents per call.
    Pass `script` as a list of StreamEvent lists (one per turn).
    When the script is exhausted, subsequent calls return a plain text "Done." response.
    """

    name = "fake"
    model = "fake/scripted"

    def __init__(self, script: list | None = None) -> None:
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
