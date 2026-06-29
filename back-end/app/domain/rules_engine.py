from __future__ import annotations

from datetime import date, datetime, timezone

from app.domain.scenarios import SCENARIO_TABLE
from app.domain.variables import derive_consumable, derive_eqa, derive_historical, derive_storage
from app.schemas.domain import (
    Decision,
    EqaStatus,
    ExtractionState,
    Scenario,
    VarStatus,
)


def resolve(
    extraction: ExtractionState,
    session_id: str,
    tenant_id: str,
    today: date | None = None,
) -> Decision:
    """
    The only place a QC scenario is decided.
    Derives the 4 variables from raw inputs, applies the precedence chain, and
    returns the Decision payload. Pure — no I/O, no side effects.
    """
    if today is None:
        today = date.today()

    consumable = derive_consumable(extraction.consumable, today)
    storage = derive_storage(extraction.storage)
    historical = derive_historical(extraction.historical)
    eqa = derive_eqa(extraction.eqa, today)

    # Precedence chain (Section 2.2) — first match wins
    if consumable == VarStatus.FAIL:
        scenario = Scenario.A
    elif storage == VarStatus.FAIL:
        scenario = Scenario.B
    elif historical == VarStatus.FAIL:
        scenario = Scenario.C
    elif eqa == EqaStatus.WARN:
        scenario = Scenario.D
    else:
        scenario = Scenario.E

    meta = SCENARIO_TABLE[scenario]

    # Only include variables that were actually collected — uncollected ones stay absent
    # rather than defaulting to PASS/STANDARD, which would misrepresent the audit record.
    variables: dict[str, str] = {}
    if extraction.consumable_known:
        variables["consumable_status"] = consumable.value
    if extraction.storage_known:
        variables["storage_condition"] = storage.value
    if extraction.historical_known:
        variables["historical_error_flag"] = historical.value
    if extraction.eqa_known:
        variables["eqa_status"] = eqa.value

    return Decision(
        session_id=session_id,
        tenant_id=tenant_id,
        device_serial=extraction.historical.device_serial,
        lot_number=extraction.consumable.lot_number,
        variables=variables,
        scenario=scenario,
        scenario_name=meta.name,
        color=meta.color,
        system_action=meta.system_action,
        is_qc_locked=meta.is_qc_locked,
        resolved_action=meta.resolved_action,
        directives=meta.directives,
        resolved_at=datetime.now(tz=timezone.utc).isoformat(),
    )
