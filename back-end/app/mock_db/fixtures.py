"""Static fixture data for mock_devices and mock_lots.

Each row is a plain dict matching the DB column names.
Covers all five QC scenarios so the 'I don't know' fallback path can be
demonstrated for every outcome.

Today (relative to deadline): 2026-06-29
Scenario mapping:
  A — Hard Block         : LOT-EXPIRED (expiry in the past)
                           LOT-OLD-VIAL (vial open > 30 days)
  B — Env Breach         : comes from storage temp/freeze-indicator (no lot lookup needed)
  C — Hardware Drift     : SN-FAIL-HIST-* (≥ 2 consecutive failures)
  D — High-Priority EQA  : SN-CLEAN-* or SN-EQA-D (0 failures; EQA state set in conversation)
  E — Standard Clearance : SN-CLEAN-* + LOT-FRESH-* (all pass)
"""

from __future__ import annotations

MOCK_DEVICES: list[dict] = [
    # -- Scenario C triggers (consecutive_qc_failures_30d >= 2) --
    {
        "serial_number": "SN-FAIL-HIST-1",
        "tenant_id": "demo",
        "storage_type": "refrigerated",
        "consecutive_qc_failures_30d": 2,
    },
    {
        "serial_number": "SN-FAIL-HIST-2",
        "tenant_id": "demo",
        "storage_type": "refrigerated",
        "consecutive_qc_failures_30d": 3,
    },
    # -- PASS on historical (consecutive < 2) — used for Scenarios D and E --
    {
        "serial_number": "SN-CLEAN-1",
        "tenant_id": "demo",
        "storage_type": "refrigerated",
        "consecutive_qc_failures_30d": 0,
    },
    {
        "serial_number": "SN-CLEAN-2",
        "tenant_id": "demo",
        "storage_type": "room_temperature",
        "consecutive_qc_failures_30d": 1,
    },
    {
        "serial_number": "SN-DEVICE-D",
        "tenant_id": "demo",
        "storage_type": "refrigerated",
        "consecutive_qc_failures_30d": 0,
    },
    {
        "serial_number": "SN-DEVICE-E",
        "tenant_id": "demo",
        "storage_type": "room_temperature",
        "consecutive_qc_failures_30d": 0,
    },
]

MOCK_LOTS: list[dict] = [
    # -- Scenario A: expired lot --
    {
        "lot_number": "LOT-EXPIRED-1",
        "tenant_id": "demo",
        "lot_expiry_date": "2026-01-15",
        "open_vial_date": "2026-01-01",
    },
    # -- Scenario A: open-vial age > 30 days (expiry fine, but vial opened too long ago) --
    {
        "lot_number": "LOT-OLD-VIAL-1",
        "tenant_id": "demo",
        "lot_expiry_date": "2026-12-31",
        "open_vial_date": "2026-05-20",  # ~40 days before 2026-06-29
    },
    # -- PASS: fresh lot, opened recently --
    {
        "lot_number": "LOT-FRESH-1",
        "tenant_id": "demo",
        "lot_expiry_date": "2026-12-31",
        "open_vial_date": "2026-06-22",  # 7 days ago
    },
    {
        "lot_number": "LOT-FRESH-2",
        "tenant_id": "demo",
        "lot_expiry_date": "2026-11-30",
        "open_vial_date": "2026-06-15",  # 14 days ago
    },
    # -- PASS: for Scenario D / E demos --
    {
        "lot_number": "LOT-EQA-D",
        "tenant_id": "demo",
        "lot_expiry_date": "2026-09-30",
        "open_vial_date": "2026-06-25",  # 4 days ago
    },
    {
        "lot_number": "LOT-STANDARD",
        "tenant_id": "demo",
        "lot_expiry_date": "2026-10-15",
        "open_vial_date": "2026-06-28",  # 1 day ago
    },
]
