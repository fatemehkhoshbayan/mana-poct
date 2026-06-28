from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, func, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Session(Base):
    __tablename__ = "sessions"

    id: Mapped[str] = mapped_column(
        String, primary_key=True, server_default=text("gen_random_uuid()::text")
    )
    tenant_id: Mapped[str] = mapped_column(String, nullable=False, default="demo")
    device_serial: Mapped[str | None] = mapped_column(String, nullable=True)
    lot_number: Mapped[str | None] = mapped_column(String, nullable=True)
    status: Mapped[str] = mapped_column(String, nullable=False, default="active")
    fsm_state: Mapped[str] = mapped_column(String, nullable=False, default="GREETING")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    messages: Mapped[list[Message]] = relationship("Message", back_populates="session")
    extractions: Mapped[list[Extraction]] = relationship("Extraction", back_populates="session")
    qc_decisions: Mapped[list[QcDecision]] = relationship("QcDecision", back_populates="session")
    events: Mapped[list[Event]] = relationship("Event", back_populates="session")


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[str] = mapped_column(
        String, primary_key=True, server_default=text("gen_random_uuid()::text")
    )
    session_id: Mapped[str] = mapped_column(String, ForeignKey("sessions.id"), nullable=False)
    role: Mapped[str] = mapped_column(String, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False, default="")
    tool_calls: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    tool_results: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    input_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    output_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    session: Mapped[Session] = relationship("Session", back_populates="messages")


class Extraction(Base):
    __tablename__ = "extractions"

    id: Mapped[str] = mapped_column(
        String, primary_key=True, server_default=text("gen_random_uuid()::text")
    )
    session_id: Mapped[str] = mapped_column(String, ForeignKey("sessions.id"), nullable=False)
    state: Mapped[dict] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    session: Mapped[Session] = relationship("Session", back_populates="extractions")


class QcDecision(Base):
    __tablename__ = "qc_decisions"

    id: Mapped[str] = mapped_column(
        String, primary_key=True, server_default=text("gen_random_uuid()::text")
    )
    session_id: Mapped[str] = mapped_column(String, ForeignKey("sessions.id"), nullable=False)
    scenario: Mapped[str] = mapped_column(String, nullable=False)
    system_action: Mapped[str] = mapped_column(String, nullable=False)
    is_qc_locked: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    session: Mapped[Session] = relationship("Session", back_populates="qc_decisions")


class Event(Base):
    __tablename__ = "events"

    id: Mapped[str] = mapped_column(
        String, primary_key=True, server_default=text("gen_random_uuid()::text")
    )
    session_id: Mapped[str] = mapped_column(String, ForeignKey("sessions.id"), nullable=False)
    type: Mapped[str] = mapped_column(String, nullable=False)
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False)
    published: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    session: Mapped[Session] = relationship("Session", back_populates="events")


class MockDevice(Base):
    __tablename__ = "mock_devices"

    serial_number: Mapped[str] = mapped_column(String, primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String, nullable=False, default="demo")
    storage_type: Mapped[str | None] = mapped_column(String, nullable=True)
    consecutive_qc_failures_30d: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class MockLot(Base):
    __tablename__ = "mock_lots"

    lot_number: Mapped[str] = mapped_column(String, primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String, nullable=False, default="demo")
    lot_expiry_date: Mapped[str | None] = mapped_column(String, nullable=True)
    open_vial_date: Mapped[str | None] = mapped_column(String, nullable=True)
