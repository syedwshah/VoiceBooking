from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Any, Dict, Optional

from sqlalchemy import DateTime, Enum as PgEnum, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from app.db.base import Base

try:  # pragma: no cover
    from sqlalchemy.dialects.postgresql import JSONB as JSONType  # type: ignore
except ImportError:  # pragma: no cover
    JSONType = JSON  # type: ignore

if TYPE_CHECKING:  # pragma: no cover
    from .customer import Customer
    from .venue import Room, Venue


class BookingStatus(str, Enum):
    DRAFT = "DRAFT"
    PENDING = "PENDING"
    CONFIRMED = "CONFIRMED"
    CANCELLED = "CANCELLED"


class PaymentStatus(str, Enum):
    PENDING = "PENDING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    REFUNDED = "REFUNDED"


class PaymentProvider(str, Enum):
    MCP_SANDBOX = "MCP_SANDBOX"
    MANUAL = "MANUAL"


class Booking(Base):
    __tablename__ = "bookings"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    session_id: Mapped[str | None] = mapped_column(String(64), index=True)
    customer_id: Mapped[int | None] = mapped_column(ForeignKey("customers.id", ondelete="SET NULL"))
    venue_id: Mapped[str] = mapped_column(ForeignKey("venues.id", ondelete="CASCADE"), nullable=False)
    room_id: Mapped[str | None] = mapped_column(ForeignKey("rooms.id", ondelete="SET NULL"))
    status: Mapped[BookingStatus] = mapped_column(PgEnum(BookingStatus, name="booking_status"), default=BookingStatus.DRAFT, nullable=False)
    start_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    end_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    duration_minutes: Mapped[int | None] = mapped_column(Integer)
    attendee_count: Mapped[int | None] = mapped_column(Integer)
    notes: Mapped[str | None] = mapped_column(Text)
    details: Mapped[Dict[str, Any]] = mapped_column(JSONType, default=dict)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now(), nullable=False)

    customer: Mapped[Optional["Customer"]] = relationship(back_populates="bookings", lazy="selectin")
    venue: Mapped["Venue"] = relationship(back_populates="bookings", lazy="joined")
    room: Mapped[Optional["Room"]] = relationship(back_populates="bookings", lazy="joined")
    payments: Mapped[list["Payment"]] = relationship(back_populates="booking", cascade="all, delete-orphan", lazy="selectin")
    door_access_events: Mapped[list["DoorAccessEvent"]] = relationship(back_populates="booking", cascade="all, delete-orphan", lazy="selectin")
    survey_responses: Mapped[list["SurveyResponse"]] = relationship(back_populates="booking", cascade="all, delete-orphan", lazy="selectin")
    call_logs: Mapped[list["CallLog"]] = relationship(back_populates="booking", cascade="all, delete-orphan", lazy="selectin")


class Payment(Base):
    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    booking_id: Mapped[int] = mapped_column(ForeignKey("bookings.id", ondelete="CASCADE"), nullable=False)
    provider: Mapped[PaymentProvider] = mapped_column(PgEnum(PaymentProvider, name="payment_provider"), nullable=False)
    status: Mapped[PaymentStatus] = mapped_column(PgEnum(PaymentStatus, name="payment_status"), default=PaymentStatus.PENDING, nullable=False)
    amount: Mapped[Optional[float]] = mapped_column(Numeric(10, 2))
    currency: Mapped[str | None] = mapped_column(String(8))
    sandbox_reference: Mapped[str | None] = mapped_column(String(128))
    extras: Mapped[Dict[str, Any]] = mapped_column(JSONType, default=dict)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now(), nullable=False)

    booking: Mapped[Booking] = relationship(back_populates="payments")


class DoorAccessEvent(Base):
    __tablename__ = "door_access_events"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    booking_id: Mapped[int] = mapped_column(ForeignKey("bookings.id", ondelete="CASCADE"), nullable=False)
    door_code: Mapped[str] = mapped_column(String(32))
    instructions: Mapped[str | None] = mapped_column(Text)
    issued_at: Mapped[datetime] = mapped_column(server_default=func.now(), nullable=False)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    context: Mapped[Dict[str, Any]] = mapped_column(JSONType, default=dict)

    booking: Mapped[Booking] = relationship(back_populates="door_access_events")

    __table_args__ = (UniqueConstraint("booking_id", name="uq_door_event_booking"),)


class SurveyResponse(Base):
    __tablename__ = "survey_responses"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    booking_id: Mapped[int] = mapped_column(ForeignKey("bookings.id", ondelete="CASCADE"), nullable=False)
    rating: Mapped[int | None] = mapped_column(Integer)
    comments: Mapped[str | None] = mapped_column(Text)
    transcript: Mapped[str | None] = mapped_column(Text)
    action_items: Mapped[list[str]] = mapped_column(JSONType, default=list)
    context: Mapped[Dict[str, Any]] = mapped_column(JSONType, default=dict)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now(), nullable=False)

    booking: Mapped[Booking] = relationship(back_populates="survey_responses")


class CallLog(Base):
    __tablename__ = "call_logs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    booking_id: Mapped[int | None] = mapped_column(ForeignKey("bookings.id", ondelete="SET NULL"))
    session_id: Mapped[str | None] = mapped_column(String(64), index=True)
    call_type: Mapped[str | None] = mapped_column(String(32))
    payload: Mapped[Dict[str, Any]] = mapped_column(JSONType, default=dict)
    transcript: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now(), nullable=False)

    booking: Mapped[Optional[Booking]] = relationship(back_populates="call_logs")
