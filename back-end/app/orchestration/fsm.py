"""Pure FSM transition logic — no I/O, no DB."""

from __future__ import annotations

from datetime import date

from app.domain.variables import derive_consumable, derive_historical, derive_storage
from app.schemas.domain import ExtractionState, FsmState, VarStatus


def mark_known(extraction: ExtractionState, today: date | None = None) -> ExtractionState:
    """
    Re-derive all four variables from current raw inputs and flip *_known flags
    whenever enough data exists to make a determination.
    Returns a new ExtractionState (avoids mutation).
    """
    if today is None:
        today = date.today()

    updated = extraction.model_copy(deep=True)

    # Consumable: need lot_number AND expiry date — lot_number is the audit identifier.
    if (
        extraction.consumable.lot_number is not None
        and extraction.consumable.lot_expiry_date is not None
    ):
        updated.consumable_known = True

    # Storage: freeze-indicator answer is required unless excursion data alone
    # determines FAIL (refrigerated breach or room-temp breach).
    s = extraction.storage
    if s.freeze_indicator_tripped is not None:
        updated.storage_known = True
    elif (
        s.storage_type == "refrigerated"
        and s.max_excursion_temp_c is not None
        and s.max_excursion_temp_c > 8
        and s.excursion_duration_hours is not None
        and s.excursion_duration_hours > 2
    ):
        updated.storage_known = True
    elif (
        s.storage_type == "room_temperature"
        and s.max_excursion_temp_c is not None
        and s.max_excursion_temp_c > 30
    ):
        updated.storage_known = True

    # Historical: need the failure count
    if extraction.historical.consecutive_qc_failures_30d is not None:
        updated.historical_known = True

    # EQA: known when has_active_cycle is set (False = no active cycle → STANDARD)
    if extraction.eqa.has_active_cycle is not None:
        # If active, also need deadline + status
        if not extraction.eqa.has_active_cycle:
            updated.eqa_known = True
        elif (
            extraction.eqa.eqa_deadline_date is not None
            and extraction.eqa.eqa_submission_status is not None
        ):
            updated.eqa_known = True

    return updated


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
