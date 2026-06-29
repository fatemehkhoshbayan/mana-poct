"""Pure FSM transition logic — no I/O, no DB."""

from __future__ import annotations

from datetime import date

from app.schemas.domain import ExtractionState, FsmState


def mark_known(extraction: ExtractionState, today: date | None = None) -> ExtractionState:
    """
    Re-derive all four variables from current raw inputs and flip *_known flags
    whenever enough data exists to make a determination.
    Returns a new ExtractionState (avoids mutation).
    """
    if today is None:
        today = date.today()

    updated = extraction.model_copy(deep=True)

    # Consumable: need at least expiry date
    if extraction.consumable.lot_expiry_date is not None:
        updated.consumable_known = True

    # Storage: need either freeze indicator or (storage_type + temp data)
    s = extraction.storage
    if s.freeze_indicator_tripped is not None:
        updated.storage_known = True
    elif s.storage_type is not None and s.max_excursion_temp_c is not None:
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
