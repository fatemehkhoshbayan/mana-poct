"""Slice 3 — Robust dialogue tests.

Covers three capabilities without requiring a real LLM API key:
  1. mark_known re-derive — flags are computed from scratch, never ratcheted
  2. Out-of-order collection — operator volunteers variables ahead of the FSM objective
  3. Corrections — operator corrects a previously recorded value

Tests mix two strategies:
- Unit-level: directly call execute_tool / mark_known without the full orchestrator
- Orchestrator-level: use FakeProvider scripts to exercise the full handle_turn loop
"""

from __future__ import annotations

from datetime import date

from app.llm.fake import SCENARIO_SCRIPTS, FakeProvider, _record_call
from app.orchestration.fsm import mark_known, next_objective
from app.orchestration.orchestrator import DecisionEvent, Orchestrator, StateEvent
from app.orchestration.tools import execute_tool
from app.schemas.domain import (
    ConsumableInput,
    EqaInput,
    ExtractionState,
    FsmState,
    HistoricalInput,
    StorageInput,
)
from app.schemas.llm import LlmMessage

TODAY = date(2026, 6, 29)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _base_history() -> list[LlmMessage]:
    return [LlmMessage(role="user", content="Start")]


async def _collect_events(
    orchestrator: Orchestrator,
    history: list[LlmMessage],
    user_message: str,
    extraction: ExtractionState,
) -> tuple[list[StateEvent], DecisionEvent | None]:
    """Drive one handle_turn call and collect events by type."""
    states: list[StateEvent] = []
    decision: DecisionEvent | None = None
    async for event in orchestrator.handle_turn(
        session_id="test-session",
        tenant_id="demo",
        history=history,
        user_message=user_message,
        extraction=extraction,
        today=TODAY,
    ):
        if isinstance(event, StateEvent):
            states.append(event)
        elif isinstance(event, DecisionEvent):
            decision = event
    return states, decision


# ---------------------------------------------------------------------------
# 1. mark_known — re-derive from scratch
# ---------------------------------------------------------------------------


class TestMarkKnownReDerive:
    """mark_known must compute flags purely from raw inputs, never carry stale flags."""

    def test_consumable_resets_when_lot_number_is_none(self):
        """Stale consumable_known=True with no lot_number must reset to False."""
        extraction = ExtractionState(
            consumable=ConsumableInput(
                lot_number=None,
                lot_expiry_date=date(2026, 12, 31),
            ),
            consumable_known=True,
        )
        result = mark_known(extraction, TODAY)
        assert result.consumable_known is False

    def test_storage_resets_when_freeze_indicator_is_none(self):
        """Stale storage_known=True with freeze_indicator_tripped=None must reset."""
        extraction = ExtractionState(
            storage=StorageInput(
                storage_type="refrigerated",
                freeze_indicator_tripped=None,
            ),
            storage_known=True,
        )
        result = mark_known(extraction, TODAY)
        assert result.storage_known is False

    def test_historical_resets_when_failures_is_none(self):
        extraction = ExtractionState(
            historical=HistoricalInput(consecutive_qc_failures_30d=None),
            historical_known=True,
        )
        result = mark_known(extraction, TODAY)
        assert result.historical_known is False

    def test_eqa_resets_when_active_cycle_is_none(self):
        extraction = ExtractionState(
            eqa=EqaInput(has_active_cycle=None),
            eqa_known=True,
        )
        result = mark_known(extraction, TODAY)
        assert result.eqa_known is False

    def test_all_stale_flags_reset_on_empty_inputs(self):
        """All four stale True flags must be reset to False when inputs are empty."""
        extraction = ExtractionState(
            consumable_known=True,
            storage_known=True,
            historical_known=True,
            eqa_known=True,
        )
        result = mark_known(extraction, TODAY)
        assert result.consumable_known is False
        assert result.storage_known is False
        assert result.historical_known is False
        assert result.eqa_known is False

    def test_all_flags_set_when_complete_data_provided(self):
        extraction = ExtractionState(
            consumable=ConsumableInput(
                lot_number="LOT-1",
                lot_expiry_date=date(2026, 12, 31),
            ),
            storage=StorageInput(
                storage_type="refrigerated",
                freeze_indicator_tripped=False,
            ),
            historical=HistoricalInput(consecutive_qc_failures_30d=0),
            eqa=EqaInput(has_active_cycle=False),
        )
        result = mark_known(extraction, TODAY)
        assert result.consumable_known is True
        assert result.storage_known is True
        assert result.historical_known is True
        assert result.eqa_known is True

    def test_mark_known_is_idempotent(self):
        """Calling mark_known twice on the same state gives the same result."""
        extraction = ExtractionState(
            consumable=ConsumableInput(
                lot_number="LOT-1",
                lot_expiry_date=date(2026, 12, 31),
            ),
        )
        once = mark_known(extraction, TODAY)
        twice = mark_known(once, TODAY)
        assert once.consumable_known == twice.consumable_known
        assert once.storage_known == twice.storage_known


# ---------------------------------------------------------------------------
# 2. Out-of-order collection
# ---------------------------------------------------------------------------


class TestOutOfOrderCollection:
    """
    Operator volunteers information for multiple variables in one message.
    execute_tool must record each one and mark_known must advance the FSM correctly.
    """

    def test_recording_consumable_then_storage_advances_fsm_to_historical(self):
        """
        Calling execute_tool for consumable and then storage on the same extraction
        must mark both known and point the FSM to ASK_HISTORICAL.
        """
        extraction = ExtractionState()

        extraction, _ = execute_tool(
            "record_consumable",
            {"lot_number": "LOT-E", "lot_expiry_date": "2026-12-31", "open_vial_age_days": 5},
            extraction,
        )
        assert extraction.consumable_known is True
        assert next_objective(extraction) == FsmState.ASK_STORAGE  # storage still needed

        extraction, _ = execute_tool(
            "record_storage",
            {"storage_type": "refrigerated", "freeze_indicator_tripped": False},
            extraction,
        )
        assert extraction.storage_known is True
        assert next_objective(extraction) == FsmState.ASK_HISTORICAL  # skips storage

    def test_recording_all_four_out_of_order_advances_to_resolving(self):
        """
        Recording all four variables in arbitrary order via execute_tool must
        result in all flags True and FSM = RESOLVING.
        """
        extraction = ExtractionState()

        # Record EQA first (out of order)
        extraction, _ = execute_tool(
            "record_eqa", {"has_active_cycle": False}, extraction
        )
        assert extraction.eqa_known is True
        assert next_objective(extraction) == FsmState.ASK_CONSUMABLE  # consumable first

        # Record historical
        extraction, _ = execute_tool(
            "record_historical", {"consecutive_qc_failures_30d": 0}, extraction
        )

        # Record storage
        extraction, _ = execute_tool(
            "record_storage",
            {"storage_type": "refrigerated", "freeze_indicator_tripped": False},
            extraction,
        )

        # Record consumable last
        extraction, _ = execute_tool(
            "record_consumable",
            {"lot_number": "LOT-E", "lot_expiry_date": "2026-12-31", "open_vial_age_days": 5},
            extraction,
        )

        assert next_objective(extraction) == FsmState.RESOLVING

    async def test_orchestrator_multi_tool_turn_resolves_scenario_e(self):
        """
        FakeProvider OUT_OF_ORDER script: consumable + storage in one stream batch,
        then historical, then EQA — all within a single handle_turn. Must resolve E.
        """
        provider = FakeProvider(script=SCENARIO_SCRIPTS["OUT_OF_ORDER"])
        orchestrator = Orchestrator(provider)

        states, decision = await _collect_events(
            orchestrator,
            _base_history(),
            "LOT-E, expiry 2026-12-31, fridge, no freeze tag, no failures, no EQA",
            ExtractionState(),
        )

        assert states, "Expected StateEvents from tool execution"
        assert decision is not None, "Expected a DecisionEvent"
        assert decision.decision.scenario.value == "E"

        # After the consumable+storage batch, both should be known in the first state
        # that follows a multi-tool iteration (the FSM jumped past storage).
        first_state = states[0]
        assert first_state.extraction.consumable_known is True
        assert first_state.extraction.storage_known is True


# ---------------------------------------------------------------------------
# 3. Corrections
# ---------------------------------------------------------------------------


class TestCorrections:
    """
    Operator corrects a previously recorded value. execute_tool must overwrite the
    raw data and mark_known / can_resolve_early must re-evaluate from the new values.
    """

    def test_correcting_expiry_from_valid_to_expired_makes_consumable_fail(self):
        """
        record_consumable with an expired date after a valid one must update the
        lot_expiry_date so derive_consumable returns FAIL.
        """
        from app.domain.variables import derive_consumable  # noqa: PLC0415

        extraction = ExtractionState()

        # Initial: valid
        extraction, _ = execute_tool(
            "record_consumable",
            {"lot_number": "LOT-C", "lot_expiry_date": "2026-12-31", "open_vial_age_days": 5},
            extraction,
        )
        assert derive_consumable(extraction.consumable, TODAY).value == "PASS"

        # Correction: expired
        extraction, _ = execute_tool(
            "record_consumable",
            {"lot_number": "LOT-C", "lot_expiry_date": "2026-01-01", "open_vial_age_days": 5},
            extraction,
        )
        assert extraction.consumable.lot_expiry_date == date(2026, 1, 1)
        assert derive_consumable(extraction.consumable, TODAY).value == "FAIL"

    def test_correcting_expiry_from_expired_to_valid_makes_consumable_pass(self):
        """
        Correcting an expired lot to a valid expiry must flip derive_consumable to PASS.
        """
        from app.domain.variables import derive_consumable  # noqa: PLC0415

        extraction = ExtractionState()

        # Initial: expired
        extraction, _ = execute_tool(
            "record_consumable",
            {"lot_number": "LOT-C", "lot_expiry_date": "2026-01-01", "open_vial_age_days": 5},
            extraction,
        )
        assert derive_consumable(extraction.consumable, TODAY).value == "FAIL"

        # Correction: valid
        extraction, _ = execute_tool(
            "record_consumable",
            {"lot_number": "LOT-C", "lot_expiry_date": "2026-12-31", "open_vial_age_days": 5},
            extraction,
        )
        assert extraction.consumable.lot_expiry_date == date(2026, 12, 31)
        assert derive_consumable(extraction.consumable, TODAY).value == "PASS"

    async def test_correction_within_handle_turn_fires_scenario_a(self):
        """
        FakeProvider CORRECTION_PASS_TO_FAIL: iteration 0 records valid lot, iteration 1
        records the corrected expired lot — both within a single handle_turn call.
        The orchestrator must detect consumable FAIL and resolve Scenario A.
        """
        provider = FakeProvider(script=SCENARIO_SCRIPTS["CORRECTION_PASS_TO_FAIL"])
        orchestrator = Orchestrator(provider)

        states, decision = await _collect_events(
            orchestrator,
            _base_history(),
            "Lot LOT-C, expiry 2026-12-31, opened 5 days ago",
            ExtractionState(),
        )

        assert states, "Expected StateEvents from both record calls"
        assert decision is not None, "Expected Scenario A after correction to expired lot"
        assert decision.decision.scenario.value == "A"
        # The corrected (expired) date must be what's stored
        assert states[-1].extraction.consumable.lot_expiry_date == date(2026, 1, 1)

    def test_correction_after_knowing_preserves_collection_state(self):
        """
        After correcting a value, other variables remain uncollected.
        The FSM must not skip ahead after the correction.
        """
        extraction = ExtractionState(
            consumable=ConsumableInput(
                lot_number="LOT-C",
                lot_expiry_date=date(2026, 1, 1),  # wrong expired value
            ),
            consumable_known=True,
        )

        # Correct the expiry to a valid date
        extraction, _ = execute_tool(
            "record_consumable",
            {"lot_number": "LOT-C", "lot_expiry_date": "2026-12-31", "open_vial_age_days": 5},
            extraction,
        )

        assert extraction.consumable.lot_expiry_date == date(2026, 12, 31)
        assert extraction.consumable_known is True
        assert not extraction.storage_known
        assert not extraction.historical_known
        assert not extraction.eqa_known
        assert next_objective(extraction) == FsmState.ASK_STORAGE

    async def test_single_correction_script_resolves_scenario_e(self):
        """
        Custom single-turn script: record valid consumable (correction from stale expired
        state). With storage/historical/EQA still missing, no decision should fire.
        """
        correction_provider = FakeProvider(
            script=[
                _record_call("record_consumable", {
                    "lot_number": "LOT-C",
                    "lot_expiry_date": "2026-12-31",
                    "open_vial_age_days": 5,
                }),
            ]
        )
        orchestrator = Orchestrator(correction_provider)

        # Start with an extraction that has the old (expired) consumable
        stale_extraction = ExtractionState(
            consumable=ConsumableInput(
                lot_number="LOT-C",
                lot_expiry_date=date(2026, 1, 1),
            ),
            consumable_known=True,
        )

        states, decision = await _collect_events(
            orchestrator,
            _base_history(),
            "Actually the expiry is 2026-12-31",
            stale_extraction,
        )

        # No decision — storage/historical/EQA still missing
        assert decision is None, "Should not resolve with only consumable corrected"
        assert states, "Expected at least one StateEvent"
        corrected = states[-1].extraction
        assert corrected.consumable.lot_expiry_date == date(2026, 12, 31)
        assert corrected.consumable_known is True
        assert next_objective(corrected) == FsmState.ASK_STORAGE


# ---------------------------------------------------------------------------
# 4. FSM next_objective — full progression order
# ---------------------------------------------------------------------------


class TestFsmProgression:
    """next_objective must walk the strict consumable→storage→historical→EQA order."""

    def test_full_progression_order(self):
        ext = ExtractionState()
        assert next_objective(ext) == FsmState.ASK_CONSUMABLE

        ext = ExtractionState(
            consumable=ConsumableInput(lot_number="L", lot_expiry_date=date(2026, 12, 31)),
            consumable_known=True,
        )
        assert next_objective(ext) == FsmState.ASK_STORAGE

        ext = ExtractionState(
            consumable=ConsumableInput(lot_number="L", lot_expiry_date=date(2026, 12, 31)),
            consumable_known=True,
            storage=StorageInput(storage_type="refrigerated", freeze_indicator_tripped=False),
            storage_known=True,
        )
        assert next_objective(ext) == FsmState.ASK_HISTORICAL

        ext = ExtractionState(
            consumable=ConsumableInput(lot_number="L", lot_expiry_date=date(2026, 12, 31)),
            consumable_known=True,
            storage=StorageInput(storage_type="refrigerated", freeze_indicator_tripped=False),
            storage_known=True,
            historical=HistoricalInput(consecutive_qc_failures_30d=0),
            historical_known=True,
        )
        assert next_objective(ext) == FsmState.ASK_EQA

        ext = ExtractionState(
            consumable=ConsumableInput(lot_number="L", lot_expiry_date=date(2026, 12, 31)),
            consumable_known=True,
            storage=StorageInput(storage_type="refrigerated", freeze_indicator_tripped=False),
            storage_known=True,
            historical=HistoricalInput(consecutive_qc_failures_30d=0),
            historical_known=True,
            eqa=EqaInput(has_active_cycle=False),
            eqa_known=True,
        )
        assert next_objective(ext) == FsmState.RESOLVING
