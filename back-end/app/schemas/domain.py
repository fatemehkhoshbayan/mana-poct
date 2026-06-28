from __future__ import annotations

from datetime import date
from enum import Enum

from pydantic import BaseModel


class VarStatus(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"


class EqaStatus(str, Enum):
    WARN = "WARN"
    STANDARD = "STANDARD"


class Scenario(str, Enum):
    A = "A"
    B = "B"
    C = "C"
    D = "D"
    E = "E"


class Color(str, Enum):
    RED = "RED"
    YELLOW = "YELLOW"
    BLUE = "BLUE"
    GREEN = "GREEN"


class FsmState(str, Enum):
    GREETING = "GREETING"
    ASK_CONSUMABLE = "ASK_CONSUMABLE"
    ASK_STORAGE = "ASK_STORAGE"
    ASK_HISTORICAL = "ASK_HISTORICAL"
    ASK_EQA = "ASK_EQA"
    RESOLVING = "RESOLVING"
    RESOLVED = "RESOLVED"


# --- Raw extracted inputs ---

class ConsumableInput(BaseModel):
    lot_number: str | None = None
    lot_expiry_date: date | None = None
    open_vial_date: date | None = None
    open_vial_age_days: int | None = None


class StorageInput(BaseModel):
    storage_type: str | None = None
    max_excursion_temp_c: float | None = None
    excursion_duration_hours: float | None = None
    freeze_indicator_tripped: bool | None = None


class HistoricalInput(BaseModel):
    consecutive_qc_failures_30d: int | None = None
    device_serial: str | None = None


class EqaInput(BaseModel):
    eqa_deadline_date: date | None = None
    eqa_submission_status: str | None = None
    has_active_cycle: bool | None = None


class ExtractionState(BaseModel):
    consumable: ConsumableInput = ConsumableInput()
    storage: StorageInput = StorageInput()
    historical: HistoricalInput = HistoricalInput()
    eqa: EqaInput = EqaInput()
    consumable_known: bool = False
    storage_known: bool = False
    historical_known: bool = False
    eqa_known: bool = False


# --- Final decision payload ---

class Decision(BaseModel):
    session_id: str
    tenant_id: str
    device_serial: str | None = None
    lot_number: str | None = None
    variables: dict[str, str]
    scenario: Scenario
    scenario_name: str
    color: Color
    system_action: str
    is_qc_locked: bool
    resolved_action: str
    directives: list[str]
    resolved_at: str
