from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_session
from app.models import Booking
from app.services.booking_service import (
    BookingPayload,
    BookingService,
    CustomerPayload,
    get_booking_service,
)
from app.stores.session_store import BookingStatus as StoreBookingStatus
from app.stores.session_store import session_store


class CustomerInfo(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    phone_number: Optional[str] = None
    attributes: Dict[str, Any] = Field(default_factory=dict)


class BookingConfirmation(BaseModel):
    venue_id: str
    room_id: Optional[str] = None
    start_time: Optional[datetime] = None
    duration_minutes: Optional[int] = None
    attendee_count: Optional[int] = None
    notes: Optional[str] = None
    details: Dict[str, Any] = Field(default_factory=dict)
    customer: CustomerInfo
    payment_amount: Optional[Decimal] = None
    payment_currency: str = "USD"


router = APIRouter(prefix="/booking", tags=["booking"])


def _serialize_booking(booking: Booking) -> Dict[str, Any]:
    door_event = booking.door_access_events[0] if booking.door_access_events else None
    payment = booking.payments[0] if booking.payments else None
    return {
        "id": booking.id,
        "session_id": booking.session_id,
        "status": booking.status.value.lower(),
        "customer": {
            "id": booking.customer.id if booking.customer else None,
            "name": booking.customer.name if booking.customer else None,
            "email": booking.customer.email if booking.customer else None,
            "phone_number": booking.customer.phone_number if booking.customer else None,
        },
        "venue": {
            "id": booking.venue.id,
            "name": booking.venue.name,
        },
        "room": {
            "id": booking.room.id,
            "label": booking.room.label,
        } if booking.room else None,
        "start_time": booking.start_time.isoformat() if booking.start_time else None,
        "end_time": booking.end_time.isoformat() if booking.end_time else None,
        "duration_minutes": booking.duration_minutes,
        "attendee_count": booking.attendee_count,
        "notes": booking.notes,
        "details": booking.details,
        "payment": {
            "status": payment.status.value.lower(),
            "amount": str(payment.amount) if payment.amount is not None else None,
            "currency": payment.currency,
            "provider": payment.provider.value.lower(),
        } if payment else None,
        "door_access": {
            "code": door_event.door_code,
            "instructions": door_event.instructions,
            "expires_at": door_event.expires_at.isoformat() if door_event.expires_at else None,
        } if door_event else None,
    }


@router.post("/{session_id}/confirm")
async def confirm_booking(
    session_id: str,
    payload: BookingConfirmation,
    db: AsyncSession = Depends(get_session),
    booking_service: BookingService = Depends(get_booking_service),
) -> Dict[str, Any]:
    try:
        booking = await booking_service.confirm_booking(
            session=db,
            customer_payload=CustomerPayload(
                name=payload.customer.name,
                email=payload.customer.email,
                phone_number=payload.customer.phone_number,
                attributes=payload.customer.attributes,
            ),
            booking_payload=BookingPayload(
                session_id=session_id,
                venue_id=payload.venue_id,
                room_id=payload.room_id,
                start_time=payload.start_time,
                duration_minutes=payload.duration_minutes,
                attendee_count=payload.attendee_count,
                notes=payload.notes,
                details=payload.details,
                payment_amount=payload.payment_amount,
                payment_currency=payload.payment_currency,
            ),
        )
    except ValueError as exc:  # venue / room not found
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    # Update in-memory session snapshot for existing flows
    store_record = StoreBookingStatus(
        status=booking.status.value.lower(),
        booking_id=str(booking.id),
        room_id=booking.room.id if booking.room else None,
        check_in_time=booking.start_time.isoformat() if booking.start_time else None,
    )
    if booking.door_access_events:
        store_record.key_token = booking.door_access_events[0].door_code
    store_record.payment_required = False
    session_store.update_booking_status(session_id, store_record)

    return {"booking": _serialize_booking(booking)}


@router.post("/{booking_id}/door-code")
async def regenerate_door_code(
    booking_id: int,
    db: AsyncSession = Depends(get_session),
    booking_service: BookingService = Depends(get_booking_service),
) -> Dict[str, Any]:
    try:
        booking = await booking_service.regenerate_door_code(db, booking_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    if booking.session_id:
        store_record = StoreBookingStatus(
            status=booking.status.value.lower(),
            booking_id=str(booking.id),
            room_id=booking.room.id if booking.room else None,
            check_in_time=booking.start_time.isoformat() if booking.start_time else None,
        )
        store_record.key_token = booking.door_access_events[0].door_code
        store_record.payment_required = False
        session_store.update_booking_status(booking.session_id, store_record)

    return {"booking": _serialize_booking(booking)}


@router.get("/recent")
async def list_recent_bookings(
    limit: int = 25,
    db: AsyncSession = Depends(get_session),
    booking_service: BookingService = Depends(get_booking_service),
) -> Dict[str, Any]:
    bookings = await booking_service.list_bookings(db, limit=limit)
    return {"bookings": [_serialize_booking(booking) for booking in bookings]}
