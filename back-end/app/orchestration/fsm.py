"""Pure FSM transition logic — no I/O, no DB."""

from __future__ import annotations

from datetime import date

from app.domain.variables import derive_consumable, derive_historical, derive_storage
from app.schemas.domain import ExtractionState, FsmState, VarStatus


def mark_known(extraction: ExtractionState, today: date | None = None) -> ExtractionState:
    """
    Re-derive all four *_known flags from scratch based on current raw inputs.

    Each flag is computed fresh — flags are never carried over from the incoming
    ExtractionState. This makes the function idempotent and supports corrections:
    if an operator corrects a value that previously satisfied the known-condition,
    the flag resets to False until the corrected data again satisfies it.

    Returns a new ExtractionState (avoids mutation).
    """
    if today is None:
        today = date.today()

    # Consumable: need lot_number AND expiry date — lot_number is the audit identifier.
    consumable_known = (
        extraction.consumable.lot_number is not None
        and extraction.consumable.lot_expiry_date is not None
    )

    # Storage: freeze-indicator answer is required unless excursion data alone
    # determines FAIL (refrigerated breach or room-temp breach).
    s = extraction.storage
    storage_known = False
    if s.freeze_indicator_tripped is not None:
        storage_known = True
    elif (
        s.storage_type == "refrigerated"
        and s.max_excursion_temp_c is not None
        and s.max_excursion_temp_c > 8
        and s.excursion_duration_hours is not None
        and s.excursion_duration_hours > 2
    ):
        storage_known = True
    elif (
        s.storage_type == "room_temperature"
        and s.max_excursion_temp_c is not None
        and s.max_excursion_temp_c > 30
    ):
        storage_known = True

    # Historical: need the failure count
    historical_known = extraction.historical.consecutive_qc_failures_30d is not None

    # EQA: known when has_active_cycle is set (False = no active cycle → STANDARD)
    eqa_known = False
    if extraction.eqa.has_active_cycle is not None:
        if not extraction.eqa.has_active_cycle:
            eqa_known = True
        elif (
            extraction.eqa.eqa_deadline_date is not None
            and extraction.eqa.eqa_submission_status is not None
        ):
            eqa_known = True

    return extraction.model_copy(
        update={
            "consumable_known": consumable_known,
            "storage_known": storage_known,
            "historical_known": historical_known,
            "eqa_known": eqa_known,
        }
    )


def next_objective(extraction: ExtractionState) -> FsmState:
    """Return the FSM state for the next variable to collect, or RESOLVING."""
    if not extraction.consumable_known:
        return FsmState.ASK_CONSUMABLE
    if not extraction.storage_known:
        return FsmState.ASK_STORAGE
    if not extraction.historical_known:
        return FsmState.ASK_HISTORICAL
    if not extraction.eqa_known:
        return FsmState.ASK_EQA
    return FsmState.RESOLVING


def all_known(extraction: ExtractionState) -> bool:
    return (
        extraction.consumable_known
        and extraction.storage_known
        and extraction.historical_known
        and extraction.eqa_known
    )


def can_resolve_early(extraction: ExtractionState, today: date | None = None) -> bool:
    """
    True when the QC outcome is certain before all 4 variables are collected.

    Mirrors the precedence chain from §2.2:
      consumable FAIL → Scenario A (storage/historical/EQA cannot change it)
      consumable PASS + storage FAIL → Scenario B (historical/EQA cannot change it)
      consumable PASS + storage PASS + historical FAIL → Scenario C (EQA cannot change it)
    """
    if today is None:
        today = date.today()

    if extraction.consumable_known:
        if derive_consumable(extraction.consumable, today) == VarStatus.FAIL:
            return True

    if extraction.consumable_known and extraction.storage_known:
        if derive_storage(extraction.storage) == VarStatus.FAIL:
            return True

    if extraction.consumable_known and extraction.storage_known and extraction.historical_known:
        if derive_historical(extraction.historical) == VarStatus.FAIL:
            return True

    return False
