"""In-memory MockRepository backed by static fixtures.

The seeder writes the same data to PostgreSQL for inspection/audit, but tool
executors use this in-memory lookup so no async DB call is needed mid-turn.
"""

from __future__ import annotations

from app.mock_db.fixtures import MOCK_DEVICES, MOCK_LOTS

_devices: dict[str, dict] = {d["serial_number"]: d for d in MOCK_DEVICES}
_lots: dict[str, dict] = {lot["lot_number"]: lot for lot in MOCK_LOTS}


class MockRepository:
    """Synchronous lookup against the in-memory fixture index."""

    def get_device(self, serial_number: str) -> dict | None:
        """Return the mock device record for *serial_number*, or None if not found."""
        return _devices.get(serial_number)

    def get_lot(self, lot_number: str) -> dict | None:
        """Return the mock lot record for *lot_number*, or None if not found."""
        return _lots.get(lot_number)

    def list_device_serials(self) -> list[str]:
        return list(_devices.keys())

    def list_lot_numbers(self) -> list[str]:
        return list(_lots.keys())


repository = MockRepository()
