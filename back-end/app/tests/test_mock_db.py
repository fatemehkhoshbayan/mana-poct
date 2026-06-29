"""Tests for Slice 2: MockRepository + lookup_* tool executors."""

from __future__ import annotations

import json
from datetime import date

from app.mock_db.fixtures import MOCK_DEVICES, MOCK_LOTS
from app.mock_db.repository import repository
from app.orchestration.tools import execute_tool
from app.schemas.domain import ExtractionState

# ---------------------------------------------------------------------------
# MockRepository tests
# ---------------------------------------------------------------------------


def test_repository_get_known_device():
    record = repository.get_device("SN-FAIL-HIST-1")
    assert record is not None
    assert record["consecutive_qc_failures_30d"] == 2


def test_repository_get_unknown_device():
    assert repository.get_device("DOES-NOT-EXIST") is None


def test_repository_get_known_lot():
    record = repository.get_lot("LOT-EXPIRED-1")
    assert record is not None
    assert record["lot_expiry_date"] == "2026-01-15"


def test_repository_get_unknown_lot():
    assert repository.get_lot("LOT-NOPE") is None


def test_all_devices_indexed():
    for d in MOCK_DEVICES:
        assert repository.get_device(d["serial_number"]) is not None


def test_all_lots_indexed():
    for lot in MOCK_LOTS:
        assert repository.get_lot(lot["lot_number"]) is not None


# ---------------------------------------------------------------------------
# lookup_device executor tests
# ---------------------------------------------------------------------------


def test_lookup_device_found_auto_merges_failures():
    extraction = ExtractionState()
    new_ext, result_json = execute_tool(
        "lookup_device", {"serial_number": "SN-FAIL-HIST-1"}, extraction
    )
    result = json.loads(result_json)

    assert result["found"] is True
    assert result["consecutive_qc_failures_30d"] == 2
    assert new_ext.historical.consecutive_qc_failures_30d == 2
    assert new_ext.historical.device_serial == "SN-FAIL-HIST-1"
    assert new_ext.historical_known is True


def test_lookup_device_found_triggers_scenario_c():
    """Device SN-FAIL-HIST-2 has 3 failures → historical FAIL → Scenario C."""
    from app.domain.rules_engine import resolve
    from app.schemas.domain import (
        ConsumableInput,
        EqaInput,
        ExtractionState,
        StorageInput,
    )

    extraction = ExtractionState(
        consumable=ConsumableInput(
            lot_expiry_date=date(2026, 12, 31),
            open_vial_age_days=5,
        ),
        consumable_known=True,
        storage=StorageInput(
            storage_type="refrigerated",
            freeze_indicator_tripped=False,
        ),
        storage_known=True,
        eqa=EqaInput(has_active_cycle=False),
        eqa_known=True,
    )
    new_ext, _ = execute_tool(
        "lookup_device", {"serial_number": "SN-FAIL-HIST-2"}, extraction
    )
    assert new_ext.historical_known is True
    decision = resolve(new_ext, session_id="test", tenant_id="demo", today=date(2026, 6, 29))
    assert decision.scenario.value == "C"


def test_lookup_device_not_found_returns_error_payload():
    extraction = ExtractionState()
    new_ext, result_json = execute_tool(
        "lookup_device", {"serial_number": "UNKNOWN-999"}, extraction
    )
    result = json.loads(result_json)
    assert result["found"] is False
    # historical should remain unknown
    assert new_ext.historical_known is False


def test_lookup_device_rejects_placeholder_serial():
    extraction = ExtractionState()
    new_ext, result_json = execute_tool(
        "lookup_device", {"serial_number": "unknown"}, extraction
    )
    result = json.loads(result_json)
    assert result["found"] is False
    assert new_ext.historical_known is False
    assert "Do NOT call lookup_device" in result["message"]


def test_record_storage_sanitizes_inferred_freeze_from_temp_only():
    extraction = ExtractionState()
    new_ext, _ = execute_tool(
        "record_storage",
        {
            "storage_type": "refrigerated",
            "max_excursion_temp_c": 4,
            "freeze_indicator_tripped": False,
        },
        extraction,
    )
    assert new_ext.storage.storage_type == "refrigerated"
    assert new_ext.storage.max_excursion_temp_c is None
    assert new_ext.storage.freeze_indicator_tripped is None
    assert new_ext.storage_known is False


# ---------------------------------------------------------------------------
# lookup_lot executor tests
# ---------------------------------------------------------------------------


def test_lookup_lot_found_auto_merges_expiry():
    extraction = ExtractionState()
    new_ext, result_json = execute_tool(
        "lookup_lot", {"lot_number": "LOT-EXPIRED-1"}, extraction
    )
    result = json.loads(result_json)

    assert result["found"] is True
    assert result["lot_expiry_date"] == "2026-01-15"
    assert new_ext.consumable.lot_expiry_date == date(2026, 1, 15)
    assert new_ext.consumable.lot_number == "LOT-EXPIRED-1"
    assert new_ext.consumable_known is True


def test_lookup_lot_expired_triggers_scenario_a():
    """LOT-EXPIRED-1 has lot_expiry_date 2026-01-15 → consumable FAIL → Scenario A."""
    from app.domain.rules_engine import resolve
    from app.schemas.domain import (
        EqaInput,
        ExtractionState,
        HistoricalInput,
        StorageInput,
    )

    extraction = ExtractionState(
        storage=StorageInput(
            storage_type="refrigerated",
            freeze_indicator_tripped=False,
        ),
        storage_known=True,
        historical=HistoricalInput(consecutive_qc_failures_30d=0),
        historical_known=True,
        eqa=EqaInput(has_active_cycle=False),
        eqa_known=True,
    )
    new_ext, _ = execute_tool("lookup_lot", {"lot_number": "LOT-EXPIRED-1"}, extraction)
    assert new_ext.consumable_known is True

    decision = resolve(new_ext, session_id="test", tenant_id="demo", today=date(2026, 6, 29))
    assert decision.scenario.value == "A"


def test_lookup_lot_not_found():
    extraction = ExtractionState()
    new_ext, result_json = execute_tool("lookup_lot", {"lot_number": "LOT-NOPE"}, extraction)
    result = json.loads(result_json)
    assert result["found"] is False
    assert new_ext.consumable_known is False


def test_lookup_lot_fresh_is_consumable_pass():
    from app.domain.variables import derive_consumable
    from app.schemas.domain import ExtractionState

    extraction = ExtractionState()
    new_ext, _ = execute_tool("lookup_lot", {"lot_number": "LOT-FRESH-1"}, extraction)
    assert new_ext.consumable_known is True
    status = derive_consumable(new_ext.consumable, today=date(2026, 6, 29))
    assert status.value == "PASS"
