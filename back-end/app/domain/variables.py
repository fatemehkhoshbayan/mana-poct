from __future__ import annotations

from datetime import date

from app.schemas.domain import (
    ConsumableInput,
    EqaInput,
    EqaStatus,
    HistoricalInput,
    StorageInput,
    VarStatus,
)


def derive_consumable(c: ConsumableInput, today: date) -> VarStatus:
    """PASS iff lot not expired AND open-vial age ≤ 30 days."""
    if c.lot_expiry_date is None:
        return VarStatus.FAIL

    if c.lot_expiry_date < today:
        return VarStatus.FAIL

    # Compute open-vial age
    age: int | None = c.open_vial_age_days
    if age is None and c.open_vial_date is not None:
        age = (today - c.open_vial_date).days

    if age is not None and age > 30:
        return VarStatus.FAIL

    return VarStatus.PASS


def derive_storage(s: StorageInput) -> VarStatus:
    """FAIL on tripped freeze-indicator, or temperature excursion breach."""
    if s.freeze_indicator_tripped:
        return VarStatus.FAIL

    if s.storage_type == "refrigerated":
        if (
            s.max_excursion_temp_c is not None
            and s.max_excursion_temp_c > 8
            and s.excursion_duration_hours is not None
            and s.excursion_duration_hours > 2
        ):
            return VarStatus.FAIL

    elif s.storage_type == "room_temperature":
        if s.max_excursion_temp_c is not None and s.max_excursion_temp_c > 30:
            return VarStatus.FAIL

    return VarStatus.PASS


def derive_historical(h: HistoricalInput) -> VarStatus:
    """FAIL if ≥ 2 consecutive QC failures in last 30 days."""
    if h.consecutive_qc_failures_30d is not None and h.consecutive_qc_failures_30d >= 2:
        return VarStatus.FAIL
    return VarStatus.PASS


def derive_eqa(e: EqaInput, today: date) -> EqaStatus:
    """WARN if active cycle with deadline ≤ 7 days away and still PENDING."""
    if (
        e.has_active_cycle
        and e.eqa_deadline_date is not None
        and 0 <= (e.eqa_deadline_date - today).days <= 7
        and e.eqa_submission_status == "PENDING"
    ):
        return EqaStatus.WARN
    return EqaStatus.STANDARD
