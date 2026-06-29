"""Idempotent async seeder — writes mock fixtures to PostgreSQL on startup.

This is separate from the in-memory MockRepository (repository.py). The DB
rows exist for auditability and inspection via SQL; the tool executors use the
in-memory dict for zero-latency lookups.
"""

from __future__ import annotations

import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import MockDevice, MockLot
from app.db.session import async_session
from app.mock_db.fixtures import MOCK_DEVICES, MOCK_LOTS

logger = logging.getLogger(__name__)


async def seed_mock_db() -> None:
    """Upsert all fixture rows — safe to call multiple times."""
    async with async_session() as session:
        await _seed_devices(session)
        await _seed_lots(session)
        await session.commit()
    logger.info("mock_db seeded: %d devices, %d lots", len(MOCK_DEVICES), len(MOCK_LOTS))


async def _seed_devices(session: AsyncSession) -> None:
    for row in MOCK_DEVICES:
        existing = await session.get(MockDevice, row["serial_number"])
        if existing is None:
            session.add(
                MockDevice(
                    serial_number=row["serial_number"],
                    tenant_id=row["tenant_id"],
                    storage_type=row.get("storage_type"),
                    consecutive_qc_failures_30d=row.get("consecutive_qc_failures_30d", 0),
                )
            )


async def _seed_lots(session: AsyncSession) -> None:
    for row in MOCK_LOTS:
        existing = await session.get(MockLot, row["lot_number"])
        if existing is None:
            session.add(
                MockLot(
                    lot_number=row["lot_number"],
                    tenant_id=row["tenant_id"],
                    lot_expiry_date=row.get("lot_expiry_date"),
                    open_vial_date=row.get("open_vial_date"),
                )
            )
