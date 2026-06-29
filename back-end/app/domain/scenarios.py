from __future__ import annotations

from dataclasses import dataclass, field

from app.schemas.domain import Color, Scenario


@dataclass(frozen=True)
class ScenarioMeta:
    name: str
    color: Color
    system_action: str
    is_qc_locked: bool
    resolved_action: str
    directives: list[str] = field(default_factory=list)


SCENARIO_TABLE: dict[Scenario, ScenarioMeta] = {
    Scenario.A: ScenarioMeta(
        name="Hard Block",
        color=Color.RED,
        system_action="LOCKDOWN_DEVICE",
        is_qc_locked=True,
        resolved_action=(
            "Device locked down immediately. Flag the reagent lot number and block all patient "
            "testing until a replacement consumable is verified."
        ),
        directives=["flag_lot_number", "block_patient_testing", "set_qc_locked"],
    ),
    Scenario.B: ScenarioMeta(
        name="Environmental Breach",
        color=Color.YELLOW,
        system_action="FAIL_QC_SESSION",
        is_qc_locked=False,
        resolved_action=(
            "Current QC session invalidated. Quarantine the affected reagent lot and require "
            "re-calibration before the device is returned to service."
        ),
        directives=["invalidate_qc_run", "quarantine_lot", "force_recalibration"],
    ),
    Scenario.C: ScenarioMeta(
        name="Suspected Hardware Drift",
        color=Color.BLUE,
        system_action="TRIGGER_SECONDARY_BIO_REF_RUN",
        is_qc_locked=False,
        resolved_action=(
            "Device restricted to supervisor-only use. Request a higher-tier reference run and "
            "notify the facility manager within 1 hour."
        ),
        directives=["restrict_to_supervisor", "request_reference_run", "notify_facility_manager"],
    ),
    Scenario.D: ScenarioMeta(
        name="High-Priority Sprint",
        color=Color.GREEN,
        system_action="PASS_QC_HIGH_PRIORITY",
        is_qc_locked=False,
        resolved_action=(
            "Device cleared for patient testing. EQA submission deadline is imminent — "
            "queue EQA result submission immediately."
        ),
        directives=["clear_device", "queue_eqa_submission"],
    ),
    Scenario.E: ScenarioMeta(
        name="Standard Clearance",
        color=Color.GREEN,
        system_action="PASS_QC",
        is_qc_locked=False,
        resolved_action="Device cleared for patient testing. All QC checks passed.",
        directives=["clear_device"],
    ),
}
