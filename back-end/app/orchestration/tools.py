"""Tool registry — ToolSpec definitions and executors for record_* tools.
lookup_* tools are added in Slice 2.
"""

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
                "description": "Lot expiry date (YYYY-MM-DD).",
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
        "Call this when you have information about storage type, temperature, excursion duration, "
        "or whether the freeze-indicator tag has tripped."
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
                "description": "Maximum temperature reached during any excursion (°C).",
            },
            "excursion_duration_hours": {
                "type": "number",
                "description": "How long the temperature excursion lasted (hours).",
            },
            "freeze_indicator_tripped": {
                "type": "boolean",
                "description": "Whether the physical colour freeze-indicator tag has tripped.",
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

ALL_TOOLS: list[ToolSpec] = [
    RECORD_CONSUMABLE,
    RECORD_STORAGE,
    RECORD_HISTORICAL,
    RECORD_EQA,
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
        updated_storage = extraction.storage.model_copy(
            update={k: v for k, v in arguments.items() if v is not None}
        )
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

    else:
        logger.warning("execute_tool: unknown tool %r", tool_name)
        return extraction, json.dumps({"error": f"unknown tool: {tool_name}"})

    new_ext = mark_known(new_ext)
    return new_ext, json.dumps({"status": "recorded", "tool": tool_name})
