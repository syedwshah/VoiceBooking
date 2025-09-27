from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_session
from app.models import Booking, Room
from app.schemas.booking import AvailabilityRequest, AvailabilityResponse, AvailabilityResponseRoom, BookingSubmission, CustomerInfo
from app.services.booking_service import BookingPayload, BookingService, CustomerPayload, get_booking_service
from app.stores.event_bus import event_bus
from app.stores.session_store import SessionRecord, session_store

router = APIRouter(prefix="/vapi/tools", tags=["vapi-tools"])


@router.post("/customer")
async def store_customer_profile(payload: Dict[str, Any]) -> Dict[str, Any]:
    session_id = payload.get("session_id")
    if not session_id:
        raise HTTPException(status_code=400, detail="session_id is required")

    customer_data = payload.get("customer") or {
        "name": payload.get("name"),
        "email": payload.get("email"),
        "phone_number": payload.get("phone_number"),
        "attributes": payload.get("attributes", {}),
    }
    customer = CustomerInfo(**customer_data)

    record = session_store.get(session_id) or SessionRecord(session_id=session_id, call_type="unknown")
    record.brief.setdefault("customer", {})
    record.brief["customer"].update(customer.model_dump(exclude_none=True))
    session_store.upsert(record)

    await event_bus.publish(
        session_id,
        {
            "type": "customer.captured",
            "customer": customer.model_dump(exclude_none=True),
        },
    )
    return {"status": "stored"}


@router.post("/availability", response_model=AvailabilityResponse)
async def check_room_availability(
    payload: AvailabilityRequest,
    db: AsyncSession = Depends(get_session),
) -> AvailabilityResponse:
    stmt = select(Room).where(Room.venue_id == payload.venue_id)
    rooms = (await db.execute(stmt)).scalars().all()

    results: list[AvailabilityResponseRoom] = []
    for room in rooms:
        end_window = payload.start_time + timedelta(minutes=payload.duration_minutes)
        conflicts_stmt = select(Booking).where(
            and_(
                Booking.room_id == room.id,
                Booking.start_time.is_not(None),
                Booking.end_time.is_not(None),
                Booking.start_time < end_window,
                Booking.end_time > payload.start_time,
            )
        )
        conflicts = (await db.execute(conflicts_stmt)).scalars().all()
        available = len(conflicts) == 0
        reasons: list[str] = []
        if not available:
            reasons.append("Existing booking overlaps with requested time")
        if payload.attendee_count and room.capacity < payload.attendee_count:
            available = False
            reasons.append("Capacity too small for requested attendees")
        results.append(
            AvailabilityResponseRoom(
                room_id=room.id,
                label=room.label,
                capacity=room.capacity,
                available=available,
                reasons=reasons,
            )
        )

    response = AvailabilityResponse(
        session_id=payload.session_id,
        venue_id=payload.venue_id,
        start_time=payload.start_time,
        duration_minutes=payload.duration_minutes,
        rooms=results,
    )

    await event_bus.publish(
        payload.session_id,
        {
            "type": "availability",
            "rooms": [room.model_dump() for room in results],
        },
    )

    return response


@router.post("/booking")
async def confirm_booking(
    payload: BookingSubmission,
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
                session_id=payload.session_id,
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
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    await event_bus.publish(
        payload.session_id,
        {
            "type": "booking.confirmed",
            "booking_id": booking.id,
            "room": booking.room.to_dict(include_venue=False) if booking.room else None,
            "door_code": booking.door_access_events[0].door_code if booking.door_access_events else None,
        },
    )

    return {
        "booking_id": booking.id,
        "door_code": booking.door_access_events[0].door_code if booking.door_access_events else None,
        "status": booking.status.value,
    }


@router.post("/survey")
async def log_survey(payload: Dict[str, Any]) -> Dict[str, Any]:
    session_id = payload.get("session_id")
    if session_id:
        await event_bus.publish(session_id, {"type": "survey", "data": payload})
    return {"status": "logged"}
