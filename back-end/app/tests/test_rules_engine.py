from __future__ import annotations

from datetime import date, timedelta

from app.domain.rules_engine import resolve
from app.schemas.domain import (
    Color,
    ConsumableInput,
    EqaInput,
    ExtractionState,
    HistoricalInput,
    Scenario,
    StorageInput,
    VarStatus,
)

TODAY = date(2026, 6, 28)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_extraction(
    *,
    lot_expiry: date | None = None,
    open_vial_age_days: int | None = None,
    open_vial_date: date | None = None,
    lot_number: str | None = "LOT-001",
    storage_type: str | None = "refrigerated",
    max_temp: float | None = None,
    excursion_hours: float | None = None,
    freeze_tripped: bool | None = None,
    failures: int | None = 0,
    device_serial: str | None = "DEV-001",
    eqa_deadline: date | None = None,
    eqa_status: str | None = None,
    has_active_cycle: bool | None = False,
) -> ExtractionState:
    return ExtractionState(
        consumable=ConsumableInput(
            lot_number=lot_number,
            lot_expiry_date=lot_expiry,
            open_vial_age_days=open_vial_age_days,
            open_vial_date=open_vial_date,
        ),
        storage=StorageInput(
            storage_type=storage_type,
            max_excursion_temp_c=max_temp,
            excursion_duration_hours=excursion_hours,
            freeze_indicator_tripped=freeze_tripped,
        ),
        historical=HistoricalInput(
            consecutive_qc_failures_30d=failures,
            device_serial=device_serial,
        ),
        eqa=EqaInput(
            eqa_deadline_date=eqa_deadline,
            eqa_submission_status=eqa_status,
            has_active_cycle=has_active_cycle,
        ),
        consumable_known=True,
        storage_known=True,
        historical_known=True,
        eqa_known=True,
    )


def decision(extraction: ExtractionState) -> tuple[Scenario, Color, bool]:
    d = resolve(extraction, session_id="test", tenant_id="demo", today=TODAY)
    return d.scenario, d.color, d.is_qc_locked


# ---------------------------------------------------------------------------
# Scenario A — Hard Block (Consumable FAIL)
# ---------------------------------------------------------------------------


def test_scenario_A_expired_lot():
    ext = make_extraction(lot_expiry=TODAY - timedelta(days=1), open_vial_age_days=5)
    s, c, locked = decision(ext)
    assert s == Scenario.A
    assert c == Color.RED
    assert locked is True


def test_scenario_A_open_vial_31_days():
    ext = make_extraction(lot_expiry=TODAY + timedelta(days=30), open_vial_age_days=31)
    s, _, _ = decision(ext)
    assert s == Scenario.A


def test_scenario_A_open_vial_from_date():
    """open_vial_age_days computed from open_vial_date."""
    ext = make_extraction(
        lot_expiry=TODAY + timedelta(days=30),
        open_vial_date=TODAY - timedelta(days=31),
    )
    s, _, _ = decision(ext)
    assert s == Scenario.A


# ---------------------------------------------------------------------------
# Consumable boundary: exactly today / age=30 → PASS
# ---------------------------------------------------------------------------


def test_consumable_expiry_today_is_pass():
    ext = make_extraction(lot_expiry=TODAY, open_vial_age_days=0)
    d = resolve(ext, session_id="t", tenant_id="demo", today=TODAY)
    assert d.variables["consumable_status"] == VarStatus.PASS.value


def test_consumable_age_30_is_pass():
    ext = make_extraction(lot_expiry=TODAY + timedelta(days=10), open_vial_age_days=30)
    d = resolve(ext, session_id="t", tenant_id="demo", today=TODAY)
    assert d.variables["consumable_status"] == VarStatus.PASS.value


# ---------------------------------------------------------------------------
# Scenario B — Environmental Breach (Storage FAIL, Consumable PASS)
# ---------------------------------------------------------------------------


def test_scenario_B_refrigerated_breach():
    ext = make_extraction(
        lot_expiry=TODAY + timedelta(days=30),
        open_vial_age_days=5,
        storage_type="refrigerated",
        max_temp=9.0,
        excursion_hours=3.0,
    )
    s, c, _ = decision(ext)
    assert s == Scenario.B
    assert c == Color.YELLOW


def test_scenario_B_freeze_indicator_tripped():
    ext = make_extraction(
        lot_expiry=TODAY + timedelta(days=30),
        open_vial_age_days=5,
        freeze_tripped=True,
    )
    s, _, _ = decision(ext)
    assert s == Scenario.B


def test_scenario_B_room_temp_breach():
    ext = make_extraction(
        lot_expiry=TODAY + timedelta(days=30),
        open_vial_age_days=5,
        storage_type="room_temperature",
        max_temp=30.1,
    )
    s, _, _ = decision(ext)
    assert s == Scenario.B


def test_storage_refrigerated_8_1c_for_1_9h_is_pass():
    """Duration 1.9 h does NOT trigger breach (must be > 2)."""
    ext = make_extraction(
        lot_expiry=TODAY + timedelta(days=30),
        open_vial_age_days=5,
        storage_type="refrigerated",
        max_temp=8.1,
        excursion_hours=1.9,
    )
    d = resolve(ext, session_id="t", tenant_id="demo", today=TODAY)
    assert d.variables["storage_condition"] == VarStatus.PASS.value


def test_storage_refrigerated_8_1c_for_2_1h_is_fail():
    ext = make_extraction(
        lot_expiry=TODAY + timedelta(days=30),
        open_vial_age_days=5,
        storage_type="refrigerated",
        max_temp=8.1,
        excursion_hours=2.1,
    )
    d = resolve(ext, session_id="t", tenant_id="demo", today=TODAY)
    assert d.variables["storage_condition"] == VarStatus.FAIL.value


def test_storage_room_temp_exactly_30_is_pass():
    ext = make_extraction(
        lot_expiry=TODAY + timedelta(days=30),
        open_vial_age_days=5,
        storage_type="room_temperature",
        max_temp=30.0,
    )
    d = resolve(ext, session_id="t", tenant_id="demo", today=TODAY)
    assert d.variables["storage_condition"] == VarStatus.PASS.value


# ---------------------------------------------------------------------------
# Scenario C — Suspected Hardware Drift (Historical FAIL)
# ---------------------------------------------------------------------------


def test_scenario_C_two_failures():
    ext = make_extraction(
        lot_expiry=TODAY + timedelta(days=30),
        open_vial_age_days=5,
        failures=2,
    )
    s, c, _ = decision(ext)
    assert s == Scenario.C
    assert c == Color.BLUE


def test_historical_1_failure_is_pass():
    ext = make_extraction(
        lot_expiry=TODAY + timedelta(days=30),
        open_vial_age_days=5,
        failures=1,
    )
    d = resolve(ext, session_id="t", tenant_id="demo", today=TODAY)
    assert d.variables["historical_error_flag"] == VarStatus.PASS.value


# ---------------------------------------------------------------------------
# Scenario D — High-Priority Sprint (EQA WARN)
# ---------------------------------------------------------------------------


def test_scenario_D_eqa_deadline_in_3_days():
    ext = make_extraction(
        lot_expiry=TODAY + timedelta(days=30),
        open_vial_age_days=5,
        failures=0,
        eqa_deadline=TODAY + timedelta(days=3),
        eqa_status="PENDING",
        has_active_cycle=True,
    )
    s, c, _ = decision(ext)
    assert s == Scenario.D
    assert c == Color.GREEN


def test_eqa_deadline_exactly_7_days_pending_is_warn():
    ext = make_extraction(
        lot_expiry=TODAY + timedelta(days=30),
        open_vial_age_days=5,
        failures=0,
        eqa_deadline=TODAY + timedelta(days=7),
        eqa_status="PENDING",
        has_active_cycle=True,
    )
    d = resolve(ext, session_id="t", tenant_id="demo", today=TODAY)
    assert d.variables["eqa_status"] == "WARN"


def test_eqa_deadline_8_days_is_standard():
    ext = make_extraction(
        lot_expiry=TODAY + timedelta(days=30),
        open_vial_age_days=5,
        failures=0,
        eqa_deadline=TODAY + timedelta(days=8),
        eqa_status="PENDING",
        has_active_cycle=True,
    )
    d = resolve(ext, session_id="t", tenant_id="demo", today=TODAY)
    assert d.variables["eqa_status"] == "STANDARD"


def test_eqa_submitted_is_standard():
    ext = make_extraction(
        lot_expiry=TODAY + timedelta(days=30),
        open_vial_age_days=5,
        failures=0,
        eqa_deadline=TODAY + timedelta(days=3),
        eqa_status="SUBMITTED",
        has_active_cycle=True,
    )
    d = resolve(ext, session_id="t", tenant_id="demo", today=TODAY)
    assert d.variables["eqa_status"] == "STANDARD"


# ---------------------------------------------------------------------------
# Scenario E — Standard Clearance (all PASS)
# ---------------------------------------------------------------------------


def test_scenario_E_all_clear():
    ext = make_extraction(
        lot_expiry=TODAY + timedelta(days=30),
        open_vial_age_days=5,
        failures=0,
        has_active_cycle=False,
    )
    s, c, locked = decision(ext)
    assert s == Scenario.E
    assert c == Color.GREEN
    assert locked is False


# ---------------------------------------------------------------------------
# Precedence: Consumable FAIL + Storage FAIL → still A
# ---------------------------------------------------------------------------


def test_precedence_A_beats_B():
    ext = make_extraction(
        lot_expiry=TODAY - timedelta(days=1),  # consumable FAIL
        open_vial_age_days=5,
        storage_type="refrigerated",
        max_temp=9.0,
        excursion_hours=3.0,  # storage FAIL too
    )
    s, _, _ = decision(ext)
    assert s == Scenario.A


def test_precedence_B_beats_C():
    ext = make_extraction(
        lot_expiry=TODAY + timedelta(days=30),
        open_vial_age_days=5,
        freeze_tripped=True,  # storage FAIL
        failures=2,  # historical FAIL too
    )
    s, _, _ = decision(ext)
    assert s == Scenario.B


def test_precedence_C_beats_D():
    ext = make_extraction(
        lot_expiry=TODAY + timedelta(days=30),
        open_vial_age_days=5,
        failures=2,  # historical FAIL
        eqa_deadline=TODAY + timedelta(days=3),
        eqa_status="PENDING",
        has_active_cycle=True,  # eqa WARN too
    )
    s, _, _ = decision(ext)
    assert s == Scenario.C


# ---------------------------------------------------------------------------
# Decision payload shape
# ---------------------------------------------------------------------------


def test_decision_payload_fields():
    ext = make_extraction(
        lot_expiry=TODAY + timedelta(days=10),
        open_vial_age_days=5,
    )
    d = resolve(ext, session_id="sess-1", tenant_id="acme", today=TODAY)
    assert d.session_id == "sess-1"
    assert d.tenant_id == "acme"
    assert set(d.variables.keys()) == {
        "consumable_status",
        "storage_condition",
        "historical_error_flag",
        "eqa_status",
    }
    assert d.scenario_name
    assert d.system_action
    assert d.resolved_at
