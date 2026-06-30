from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import health, hello, sessions
from app.config import settings

logging.basicConfig(
    level=settings.LOG_LEVEL,
    format="%(asctime)s %(levelname)-8s %(name)s  %(message)s",
    datefmt="%H:%M:%S",
)

logger = logging.getLogger(__name__)


def _run_migrations() -> None:
    """Run Alembic migrations synchronously (called in a thread executor)."""
    from alembic import command  # noqa: PLC0415, I001
    from alembic.config import Config as AlembicConfig  # noqa: PLC0415

    alembic_cfg = AlembicConfig("alembic.ini")
    command.upgrade(alembic_cfg, "head")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Run Alembic migrations via thread executor to avoid event-loop nesting
    try:
        import asyncio  # noqa: PLC0415

        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, _run_migrations)
        logger.info("Alembic migrations applied")
    except Exception as exc:
        logger.warning("Alembic migration failed (non-fatal on first boot): %s", exc)

    # Seed mock DB (idempotent upsert)
    try:
        from app.mock_db.seed import seed_mock_db  # noqa: PLC0415

        await seed_mock_db()
    except Exception as exc:
        logger.warning("mock_db seed failed (non-fatal): %s", exc)

    # Start the outbox relay (Surface I) — drains Hard Block events to whichever
    # EventPublisher sinks are configured (log always; ntfy/Kafka opt-in).
    relay_task = None
    try:
        import asyncio  # noqa: PLC0415

        from app.db.session import async_session  # noqa: PLC0415
        from app.events.factory import get_publisher  # noqa: PLC0415
        from app.events.outbox import relay_loop  # noqa: PLC0415

        relay_task = asyncio.create_task(
            relay_loop(
                async_session,
                get_publisher(),
                interval_seconds=settings.EVENT_RELAY_INTERVAL_SECONDS,
            )
        )
    except Exception:
        logger.exception("Failed to start event relay (non-fatal)")

    yield

    if relay_task is not None:
        relay_task.cancel()
        try:
            await relay_task
        except Exception:
            pass

    # Flush tracer on shutdown (Surface H)
    try:
        from app.observability.tracer import tracer  # noqa: PLC0415

        tracer.flush()
    except Exception:
        pass


app = FastAPI(
    title="MANA POCT QC Assistant API",
    version="0.1.0",
    description=(
        "Intelligent QC Assistant for Point-of-Care Testing. "
        "Drives a structured diagnostic dialogue to resolve a deterministic "
        "Device Status / System Action."
    ),
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(hello.router)
app.include_router(sessions.router)

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
