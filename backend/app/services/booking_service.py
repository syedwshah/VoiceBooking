from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any, Dict, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Booking, BookingStatus, Customer, Room, Venue
from app.services.door_access_service import DoorAccessService, get_door_access_service
from app.services.payment_service import PaymentService, get_payment_service


@dataclass
class CustomerPayload:
    name: Optional[str]
    email: Optional[str]
    phone_number: Optional[str]
    attributes: Dict[str, Any]


@dataclass
class BookingPayload:
    session_id: Optional[str]
    venue_id: str
    room_id: Optional[str]
    start_time: Optional[datetime]
    duration_minutes: Optional[int]
    attendee_count: Optional[int]
    notes: Optional[str]
    details: Dict[str, Any]
    payment_amount: Optional[Decimal]
    payment_currency: str


class BookingService:
    """Coordinates persistence of bookings, payments, and door access."""

    def __init__(
        self,
        payment_service: PaymentService | None = None,
        door_access_service: DoorAccessService | None = None,
    ) -> None:
        self.payment_service = payment_service or get_payment_service()
        self.door_access_service = door_access_service or get_door_access_service()

    async def _upsert_customer(self, session: AsyncSession, payload: CustomerPayload) -> Customer:
        if payload.email:
            stmt = select(Customer).where(Customer.email == payload.email)
            existing = (await session.execute(stmt)).scalar_one_or_none()
            if existing:
                existing.name = payload.name or existing.name
                existing.phone_number = payload.phone_number or existing.phone_number
                if payload.attributes:
                    existing.attributes.update(payload.attributes)
                await session.flush()
                return existing

        customer = Customer(
            name=payload.name,
            email=payload.email,
            phone_number=payload.phone_number,
            attributes=payload.attributes,
        )
        session.add(customer)
        await session.flush()
        return customer

    async def _load_room_and_venue(self, session: AsyncSession, venue_id: str, room_id: Optional[str]) -> tuple[Venue, Optional[Room]]:
        venue = await session.get(Venue, venue_id)
        if not venue:
            raise ValueError("Venue not found")

        room = None
        if room_id:
            room = await session.get(Room, room_id)
            if not room:
                raise ValueError("Room not found")
        return venue, room

    async def confirm_booking(
        self,
        session: AsyncSession,
        customer_payload: CustomerPayload,
        booking_payload: BookingPayload,
    ) -> Booking:
        customer = await self._upsert_customer(session, customer_payload)
        venue, room = await self._load_room_and_venue(session, booking_payload.venue_id, booking_payload.room_id)

        start_time = booking_payload.start_time
        if start_time is None:
            start_time = datetime.now(timezone.utc)
        end_time = booking_payload.details.get("end_time")
        if isinstance(end_time, str):
            end_time = datetime.fromisoformat(end_time)
        if not end_time and booking_payload.duration_minutes:
            end_time = start_time + timedelta(minutes=booking_payload.duration_minutes)

        booking = Booking(
            session_id=booking_payload.session_id,
            customer=customer,
            venue=venue,
            room=room,
            status=BookingStatus.CONFIRMED,
            start_time=start_time,
            end_time=end_time,
            duration_minutes=booking_payload.duration_minutes,
            attendee_count=booking_payload.attendee_count,
            notes=booking_payload.notes,
            details=booking_payload.details,
        )
        session.add(booking)
        await session.flush()

        if booking_payload.payment_amount is not None:
            amount = Decimal(booking_payload.payment_amount)
            await self.payment_service.record_payment(
                session=session,
                booking=booking,
                amount=amount,
                currency=booking_payload.payment_currency,
                metadata={"source": "seed"},
            )

        await session.refresh(
            booking,
            attribute_names=["payments", "door_access_events", "customer", "room", "venue"],
        )
        await session.flush()
        await self.door_access_service.issue_access(session=session, booking=booking)

        await session.commit()
        await session.refresh(
            booking,
            attribute_names=["payments", "door_access_events", "customer", "room", "venue"],
        )
        return booking

    async def regenerate_door_code(self, session: AsyncSession, booking_id: int) -> Booking:
        booking = await session.get(Booking, booking_id)
        if not booking:
            raise ValueError("Booking not found")
        await self.door_access_service.issue_access(session=session, booking=booking)
        await session.commit()
        await session.refresh(
            booking,
            attribute_names=["door_access_events", "customer", "room", "venue"],
        )
        return booking

    async def list_bookings(self, session: AsyncSession, limit: int = 25) -> list[Booking]:
        stmt = select(Booking).order_by(Booking.start_time.desc()).limit(limit)
        result = await session.execute(stmt)
        return result.scalars().unique().all()


def get_booking_service() -> BookingService:
    return BookingService()
