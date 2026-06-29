"""Tool registry — ToolSpec definitions and executors for record_* and lookup_* tools."""

from __future__ import annotations

import logging
from datetime import date
from typing import Any

from app.orchestration.fsm import mark_known
from app.schemas.domain import (
    ExtractionState,
)
from app.schemas.llm import ToolSpec

logger = logging.getLogger(__name__)

_PLACEHOLDER_VALUES = frozenset(
    {
        "unknown",
        "dont know",
        "don't know",
        "do not know",
        "not sure",
        "n/a",
        "na",
        "none",
        "no idea",
        "unsure",
        "idk",
    }
)


def _is_placeholder(value: str) -> bool:
    normalized = " ".join(value.strip().lower().split())
    return normalized in _PLACEHOLDER_VALUES or normalized.startswith("i don")


def _sanitize_storage_args(arguments: dict[str, Any]) -> dict[str, Any]:
    """Drop inferred freeze-indicator / misread current temp from model tool calls."""
    args = {k: v for k, v in arguments.items() if v is not None}
    max_temp = args.get("max_excursion_temp_c")
    duration = args.get("excursion_duration_hours")

    # A normal fridge reading (≤ 8 °C) with no duration is not an excursion.
    if max_temp is not None and duration is None and max_temp <= 8:
        args.pop("max_excursion_temp_c", None)
        if args.get("freeze_indicator_tripped") is False:
            args.pop("freeze_indicator_tripped", None)

    return args

# ---------------------------------------------------------------------------
# ToolSpec registry (what the LLM sees)
# ---------------------------------------------------------------------------

RECORD_CONSUMABLE = ToolSpec(
    name="record_consumable",
    description=(
        "Record what the operator tells you about the reagent consumable. "
        "Call this whenever you have any of: lot number, lot expiry date, "
        "date the vial was first opened, or open-vial age in days."
    ),
    parameters={
        "type": "object",
        "properties": {
            "lot_number": {"type": "string", "description": "Reagent lot number."},
            "lot_expiry_date": {
                "type": "string",
                "format": "date",
                "description": (
                    "Lot expiry date (YYYY-MM-DD). "
                    "If the operator omits the year, use the current year."
                ),
            },
            "open_vial_date": {
                "type": "string",
                "format": "date",
                "description": "Date the vial was first opened (YYYY-MM-DD).",
            },
            "open_vial_age_days": {
                "type": "integer",
                "description": "Days since vial was first opened.",
            },
        },
    },
)

RECORD_STORAGE = ToolSpec(
    name="record_storage",
    description=(
        "Record the storage conditions for the reagent. "
        "You may call this with ONLY storage_type if the operator gave storage info "
        "but has not yet answered about the freeze-indicator — omit freeze_indicator_tripped "
        "in that case. "
        "Set freeze_indicator_tripped ONLY after the operator explicitly confirms "
        "tripped (true) or not tripped (false). Never infer or assume it. "
        "A current fridge reading (e.g. 4 °C) is normal operating temperature — "
        "do NOT put it in max_excursion_temp_c. Only set max_excursion_temp_c when "
        "the operator reports an actual temperature excursion."
    ),
    parameters={
        "type": "object",
        "properties": {
            "storage_type": {
                "type": "string",
                "enum": ["refrigerated", "room_temperature"],
                "description": "How the reagent is stored.",
            },
            "max_excursion_temp_c": {
                "type": "number",
                "description": (
                    "Peak temperature during an excursion (°C). "
                    "Only set when the operator reports an excursion — "
                    "NOT for normal current fridge readings."
                ),
            },
            "excursion_duration_hours": {
                "type": "number",
                "description": (
                    "How long the temperature excursion lasted (hours). "
                    "Only set if an excursion actually occurred."
                ),
            },
            "freeze_indicator_tripped": {
                "type": "boolean",
                "description": (
                    "Whether the physical colour freeze-indicator tag has tripped. "
                    "Set ONLY when the operator explicitly answers — never assume."
                ),
            },
        },
    },
)

RECORD_HISTORICAL = ToolSpec(
    name="record_historical",
    description=(
        "Record the device's QC error history. "
        "Call this when you know how many consecutive QC failures occurred in the last 30 days, "
        "or when you have a device serial number for a lookup."
    ),
    parameters={
        "type": "object",
        "properties": {
            "consecutive_qc_failures_30d": {
                "type": "integer",
                "description": "Number of consecutive QC failures in the last 30 days.",
            },
            "device_serial": {
                "type": "string",
                "description": "Device serial number (used for database lookup).",
            },
        },
    },
)

RECORD_EQA = ToolSpec(
    name="record_eqa",
    description=(
        "Record the EQA (External Quality Assurance) submission status. "
        "Call this when you know whether there is an active EQA cycle, its deadline, "
        "and the submission status."
    ),
    parameters={
        "type": "object",
        "properties": {
            "has_active_cycle": {
                "type": "boolean",
                "description": "Whether there is an active EQA submission cycle.",
            },
            "eqa_deadline_date": {
                "type": "string",
                "format": "date",
                "description": "EQA submission deadline date (YYYY-MM-DD).",
            },
            "eqa_submission_status": {
                "type": "string",
                "enum": ["PENDING", "SUBMITTED", "NONE"],
                "description": "Current EQA submission status.",
            },
        },
    },
)

LOOKUP_DEVICE = ToolSpec(
    name="lookup_device",
    description=(
        "Look up a device in the system database by serial number. "
        "Call ONLY when the operator provides an actual device serial number "
        "(e.g. SN-FAIL-HIST-1). NEVER call with phrases like 'unknown', "
        "'I don't know', or 'n/a'. If the operator has no serial number, "
        "ask whether they recall any failed QC results and use record_historical instead."
    ),
    parameters={
        "type": "object",
        "properties": {
            "serial_number": {
                "type": "string",
                "description": "Device serial number to look up.",
            },
        },
        "required": ["serial_number"],
    },
)

LOOKUP_LOT = ToolSpec(
    name="lookup_lot",
    description=(
        "Look up a reagent lot in the system database by lot number. "
        "Call this when the operator does not know the lot expiry date or vial open date "
        "and provides a lot number. The system will return expiry and open-vial date "
        "and automatically record them."
    ),
    parameters={
        "type": "object",
        "properties": {
            "lot_number": {
                "type": "string",
                "description": "Reagent lot number to look up.",
            },
        },
        "required": ["lot_number"],
    },
)

ALL_TOOLS: list[ToolSpec] = [
    RECORD_CONSUMABLE,
    RECORD_STORAGE,
    RECORD_HISTORICAL,
    RECORD_EQA,
    LOOKUP_DEVICE,
    LOOKUP_LOT,
]


# ---------------------------------------------------------------------------
# Executors
# ---------------------------------------------------------------------------


def _parse_date(raw: str, field_name: str) -> date | None:
    """Parse an ISO date string, returning None and logging a warning on failure."""
    try:
        return date.fromisoformat(raw)
    except ValueError:
        logger.warning(
            "execute_tool: could not parse %s=%r as ISO date — value ignored",
            field_name,
            raw,
        )
        return None


def execute_tool(
    tool_name: str,
    arguments: dict[str, Any],
    extraction: ExtractionState,
) -> tuple[ExtractionState, str]:
    """
    Execute a record_* tool call. Returns (updated_extraction, result_json_string).
    """
    import json  # noqa: PLC0415

    logger.info("execute_tool: %s  args=%r", tool_name, arguments)

    if tool_name == "record_consumable":
        # Apply scalar fields first (without validation — model_copy is unvalidated)
        _date_keys = ("lot_expiry_date", "open_vial_date")
        scalar_args = {k: v for k, v in arguments.items() if v is not None and k not in _date_keys}
        updated_consumable = extraction.consumable.model_copy(update=scalar_args)

        # Parse date fields with graceful error handling
        if "lot_expiry_date" in arguments and isinstance(arguments["lot_expiry_date"], str):
            parsed = _parse_date(arguments["lot_expiry_date"], "lot_expiry_date")
            if parsed is not None:
                updated_consumable = updated_consumable.model_copy(
                    update={"lot_expiry_date": parsed}
                )

        if "open_vial_date" in arguments and isinstance(arguments["open_vial_date"], str):
            parsed = _parse_date(arguments["open_vial_date"], "open_vial_date")
            if parsed is not None:
                updated_consumable = updated_consumable.model_copy(
                    update={"open_vial_date": parsed}
                )

        new_ext = extraction.model_copy(update={"consumable": updated_consumable})
        logger.info(
            "execute_tool: consumable updated → expiry=%s age=%s",
            updated_consumable.lot_expiry_date,
            updated_consumable.open_vial_age_days,
        )

    elif tool_name == "record_storage":
        storage_args = _sanitize_storage_args(arguments)
        updated_storage = extraction.storage.model_copy(update=storage_args)
        new_ext = extraction.model_copy(update={"storage": updated_storage})
        logger.info(
            "execute_tool: storage updated → type=%s freeze=%s temp=%s hrs=%s",
            updated_storage.storage_type,
            updated_storage.freeze_indicator_tripped,
            updated_storage.max_excursion_temp_c,
            updated_storage.excursion_duration_hours,
        )

    elif tool_name == "record_historical":
        updated_hist = extraction.historical.model_copy(
            update={k: v for k, v in arguments.items() if v is not None}
        )
        new_ext = extraction.model_copy(update={"historical": updated_hist})
        logger.info(
            "execute_tool: historical updated → failures=%s serial=%s",
            updated_hist.consecutive_qc_failures_30d,
            updated_hist.device_serial,
        )

    elif tool_name == "record_eqa":
        scalar_eqa_args = {
            k: v for k, v in arguments.items() if v is not None and k != "eqa_deadline_date"
        }
        updated_eqa = extraction.eqa.model_copy(update=scalar_eqa_args)

        if "eqa_deadline_date" in arguments and isinstance(arguments["eqa_deadline_date"], str):
            parsed = _parse_date(arguments["eqa_deadline_date"], "eqa_deadline_date")
            if parsed is not None:
                updated_eqa = updated_eqa.model_copy(update={"eqa_deadline_date": parsed})

        new_ext = extraction.model_copy(update={"eqa": updated_eqa})
        logger.info(
            "execute_tool: eqa updated → active=%s deadline=%s status=%s",
            updated_eqa.has_active_cycle,
            updated_eqa.eqa_deadline_date,
            updated_eqa.eqa_submission_status,
        )

    elif tool_name == "lookup_device":
        return _execute_lookup_device(arguments, extraction)

    elif tool_name == "lookup_lot":
        return _execute_lookup_lot(arguments, extraction)

    else:
        logger.warning("execute_tool: unknown tool %r", tool_name)
        return extraction, json.dumps({"error": f"unknown tool: {tool_name}"})

    new_ext = mark_known(new_ext)
    return new_ext, json.dumps({"status": "recorded", "tool": tool_name})


# ---------------------------------------------------------------------------
# Lookup executors — call MockRepository and auto-merge results
# ---------------------------------------------------------------------------


def _execute_lookup_device(
    arguments: dict[str, Any],
    extraction: ExtractionState,
) -> tuple[ExtractionState, str]:
    import json  # noqa: PLC0415

    from app.mock_db.repository import repository  # noqa: PLC0415

    serial = arguments.get("serial_number", "")
    if not serial or _is_placeholder(serial):
        logger.warning("lookup_device: rejected placeholder serial %r", serial)
        return extraction, json.dumps(
            {
                "found": False,
                "serial_number": serial,
                "message": (
                    "No valid device serial number was provided. "
                    "Do NOT call lookup_device with 'unknown' or similar phrases. "
                    "If the operator does not have a serial number, ask whether they "
                    "recall any failed QC results in the last 30 days (none / one / two or more) "
                    "and record the answer with record_historical."
                ),
            }
        )

    record = repository.get_device(serial)

    if record is None:
        logger.warning("lookup_device: serial %r not found in mock DB", serial)
        return extraction, json.dumps(
            {
                "found": False,
                "serial_number": serial,
                "message": (
                    f"No device record found for serial '{serial}'. "
                    "Please ask the operator to double-check the serial number."
                ),
            }
        )

    failures = record.get("consecutive_qc_failures_30d", 0)
    storage_type = record.get("storage_type")

    updated_hist = extraction.historical.model_copy(
        update={"consecutive_qc_failures_30d": failures, "device_serial": serial}
    )
    new_ext = extraction.model_copy(update={"historical": updated_hist})
    new_ext = mark_known(new_ext)

    logger.info(
        "lookup_device: serial=%r → failures=%d storage_type=%s",
        serial,
        failures,
        storage_type,
    )

    result = {
        "found": True,
        "serial_number": serial,
        "consecutive_qc_failures_30d": failures,
        "storage_type": storage_type,
        "message": (
            f"Device {serial} found. "
            f"Consecutive QC failures (last 30 days): {failures}. "
            f"Storage type: {storage_type or 'unknown'}."
        ),
    }
    return new_ext, json.dumps(result)


def _execute_lookup_lot(
    arguments: dict[str, Any],
    extraction: ExtractionState,
) -> tuple[ExtractionState, str]:
    import json  # noqa: PLC0415

    from app.mock_db.repository import repository  # noqa: PLC0415

    lot = arguments.get("lot_number", "")
    if not lot or _is_placeholder(lot):
        logger.warning("lookup_lot: rejected placeholder lot %r", lot)
        return extraction, json.dumps(
            {
                "found": False,
                "lot_number": lot,
                "message": (
                    "No valid lot number was provided. "
                    "Do NOT call lookup_lot with 'unknown' or similar phrases. "
                    "Ask the operator to read the lot number from the packaging."
                ),
            }
        )

    record = repository.get_lot(lot)

    if record is None:
        logger.warning("lookup_lot: lot %r not found in mock DB", lot)
        return extraction, json.dumps(
            {
                "found": False,
                "lot_number": lot,
                "message": (
                    f"No lot record found for lot number '{lot}'. "
                    "Please ask the operator to double-check the lot number on the packaging."
                ),
            }
        )

    expiry_str = record.get("lot_expiry_date")
    open_vial_str = record.get("open_vial_date")

    updated_consumable = extraction.consumable.model_copy(update={"lot_number": lot})

    if expiry_str:
        parsed_expiry = _parse_date(expiry_str, "lot_expiry_date")
        if parsed_expiry is not None:
            updated_consumable = updated_consumable.model_copy(
                update={"lot_expiry_date": parsed_expiry}
            )

    if open_vial_str:
        parsed_open = _parse_date(open_vial_str, "open_vial_date")
        if parsed_open is not None:
            updated_consumable = updated_consumable.model_copy(
                update={"open_vial_date": parsed_open}
            )

    new_ext = extraction.model_copy(update={"consumable": updated_consumable})
    new_ext = mark_known(new_ext)

    logger.info(
        "lookup_lot: lot=%r → expiry=%s open_vial=%s",
        lot,
        expiry_str,
        open_vial_str,
    )

    result = {
        "found": True,
        "lot_number": lot,
        "lot_expiry_date": expiry_str,
        "open_vial_date": open_vial_str,
        "message": (
            f"Lot {lot} found. "
            f"Expiry date: {expiry_str or 'unknown'}. "
            f"Date first opened: {open_vial_str or 'unknown'}."
        ),
    }
    return new_ext, json.dumps(result)
