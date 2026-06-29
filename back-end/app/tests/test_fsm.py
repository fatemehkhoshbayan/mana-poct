"""Tests for FSM mark_known and can_resolve_early logic."""

from __future__ import annotations

from datetime import date

from app.orchestration.fsm import can_resolve_early, mark_known, next_objective
from app.schemas.domain import (
    ConsumableInput,
    ExtractionState,
    FsmState,
    HistoricalInput,
    StorageInput,
)


def test_storage_not_known_from_current_temp_only():
    """'4 °C' misread as max_excursion must not complete storage."""
    extraction = ExtractionState(
        consumable=ConsumableInput(
            lot_number="LOT-001",           # required for consumable_known=True
            lot_expiry_date=date(2026, 12, 31),
        ),
        consumable_known=True,
        storage=StorageInput(
            storage_type="refrigerated",
            max_excursion_temp_c=4.0,
        ),
    )
    result = mark_known(extraction)
    assert result.storage_known is False
    assert next_objective(result) == FsmState.ASK_STORAGE


def test_storage_known_with_explicit_freeze_indicator():
    extraction = ExtractionState(
        consumable=ConsumableInput(lot_expiry_date=date(2026, 12, 31)),
        consumable_known=True,
        storage=StorageInput(
            storage_type="refrigerated",
            freeze_indicator_tripped=False,
        ),
    )
    result = mark_known(extraction)
    assert result.storage_known is True


def test_storage_known_from_refrigerated_excursion_breach():
    extraction = ExtractionState(
        consumable=ConsumableInput(lot_expiry_date=date(2026, 12, 31)),
        consumable_known=True,
        storage=StorageInput(
            storage_type="refrigerated",
            max_excursion_temp_c=9.0,
            excursion_duration_hours=3.0,
        ),
    )
    result = mark_known(extraction)
    assert result.storage_known is True


def test_storage_not_known_from_partial_excursion_data():
    extraction = ExtractionState(
        consumable=ConsumableInput(lot_expiry_date=date(2026, 12, 31)),
        consumable_known=True,
        storage=StorageInput(
            storage_type="refrigerated",
            max_excursion_temp_c=9.0,
        ),
    )
    result = mark_known(extraction)
    assert result.storage_known is False


# ---------------------------------------------------------------------------
# mark_known: lot_number is now required for consumable_known
# ---------------------------------------------------------------------------

def test_consumable_not_known_without_lot_number():
    """Expiry date alone must not mark consumable as known — lot_number is required."""
    extraction = ExtractionState(
        consumable=ConsumableInput(lot_expiry_date=date(2026, 12, 31)),
    )
    result = mark_known(extraction)
    assert result.consumable_known is False


def test_consumable_known_with_lot_number_and_expiry():
    extraction = ExtractionState(
        consumable=ConsumableInput(lot_number="LOT-001", lot_expiry_date=date(2026, 12, 31)),
    )
    result = mark_known(extraction)
    assert result.consumable_known is True


# ---------------------------------------------------------------------------
# can_resolve_early
# ---------------------------------------------------------------------------

TODAY = date(2026, 6, 29)
EXPIRED = date(2026, 1, 1)
VALID = date(2026, 12, 31)


def _consumable_fail_extraction() -> ExtractionState:
    return ExtractionState(
        consumable=ConsumableInput(lot_number="LOT-EXP", lot_expiry_date=EXPIRED),
        consumable_known=True,
    )


def test_can_resolve_early_consumable_fail():
    """Expired lot → Scenario A → can resolve before storage/historical/EQA."""
    extraction = _consumable_fail_extraction()
    assert can_resolve_early(extraction, TODAY) is True


def test_cannot_resolve_early_consumable_pass_storage_not_yet_known():
    """consumable PASS but storage not collected yet — cannot resolve early."""
    extraction = ExtractionState(
        consumable=ConsumableInput(lot_number="LOT-OK", lot_expiry_date=VALID),
        consumable_known=True,
    )
    assert can_resolve_early(extraction, TODAY) is False


def test_can_resolve_early_storage_fail():
    """consumable PASS + storage FAIL → Scenario B → can resolve before historical/EQA."""
    extraction = ExtractionState(
        consumable=ConsumableInput(lot_number="LOT-OK", lot_expiry_date=VALID),
        consumable_known=True,
        storage=StorageInput(
            storage_type="refrigerated",
            freeze_indicator_tripped=True,
        ),
        storage_known=True,
    )
    assert can_resolve_early(extraction, TODAY) is True


def test_cannot_resolve_early_storage_pass_historical_not_yet_known():
    """consumable PASS + storage PASS but historical not collected — cannot resolve early."""
    extraction = ExtractionState(
        consumable=ConsumableInput(lot_number="LOT-OK", lot_expiry_date=VALID),
        consumable_known=True,
        storage=StorageInput(storage_type="refrigerated", freeze_indicator_tripped=False),
        storage_known=True,
    )
    assert can_resolve_early(extraction, TODAY) is False


def test_can_resolve_early_historical_fail():
    """consumable PASS + storage PASS + historical FAIL → Scenario C → can resolve early."""
    extraction = ExtractionState(
        consumable=ConsumableInput(lot_number="LOT-OK", lot_expiry_date=VALID),
        consumable_known=True,
        storage=StorageInput(storage_type="refrigerated", freeze_indicator_tripped=False),
        storage_known=True,
        historical=HistoricalInput(consecutive_qc_failures_30d=3),
        historical_known=True,
    )
    assert can_resolve_early(extraction, TODAY) is True


def test_cannot_resolve_early_all_pass_eqa_unknown():
    """All three PASS but EQA not yet collected — must collect EQA before resolving."""
    extraction = ExtractionState(
        consumable=ConsumableInput(lot_number="LOT-OK", lot_expiry_date=VALID),
        consumable_known=True,
        storage=StorageInput(storage_type="refrigerated", freeze_indicator_tripped=False),
        storage_known=True,
        historical=HistoricalInput(consecutive_qc_failures_30d=0),
        historical_known=True,
    )
    assert can_resolve_early(extraction, TODAY) is False
