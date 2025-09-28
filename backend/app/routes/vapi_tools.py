from __future__ import annotations

import asyncio
from collections import deque
from datetime import date, datetime, time, timedelta, timezone
import logging
from decimal import Decimal, InvalidOperation
from typing import Any, Deque, Dict

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_session
from app.models import Booking, Room, Payment, PaymentStatus
from app.schemas.booking import (
    AvailabilityRequest,
    AvailabilityResponse,
    AvailabilityResponseRoom,
    BookingSubmission,
    CustomerInfo,
)
from app.services.booking_service import BookingPayload, BookingService, CustomerPayload, get_booking_service
from app.services.payment_service import PaymentService, get_payment_service
from app.stores.event_bus import event_bus
from app.stores.session_store import SessionRecord, session_store

router = APIRouter(prefix="/vapi/tools", tags=["vapi-tools"])
logger = logging.getLogger(__name__)


_mock_payment_events: Deque[dict[str, Any]] = deque(maxlen=50)


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
    logger.info(
        "session_event",
        extra={
            "session_id": session_id,
            "event": "customer.captured",
            "customer": customer.model_dump(exclude_none=True),
        },
    )
    return {"status": "stored"}


DEFAULT_VENUE_ID = "aurora-hall"


def _convert_workflow_payload(raw: Dict[str, Any]) -> AvailabilityRequest:
    def _ensure_datetime(value: str) -> datetime:
        if value.endswith("Z"):
            value = value[:-1] + "+00:00"
        dt = datetime.fromisoformat(value)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt

    try:
        session_id = raw["session_id"]
    except KeyError as exc:
        raise HTTPException(status_code=400, detail=f"Missing field: {exc.args[0]}") from exc

    if isinstance(raw.get("preferences"), dict):
        preferences = raw["preferences"]
        try:
            date_str = preferences["date"]
            start_time_str = preferences["startTime"]
            duration_hours = float(preferences["durationHours"])
        except KeyError as exc:
            raise HTTPException(status_code=400, detail=f"Missing preference field: {exc.args[0]}") from exc
        except (TypeError, ValueError) as exc:
            raise HTTPException(status_code=400, detail="durationHours must be numeric") from exc

        try:
            booking_date = date.fromisoformat(date_str)
            start_time_obj = time.fromisoformat(start_time_str)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="date or startTime format invalid") from exc

        start_datetime = datetime.combine(booking_date, start_time_obj, tzinfo=timezone.utc)
        duration_minutes = int(duration_hours * 60)
        attendee_count = preferences.get("attendeeCount") or preferences.get("attendees")
        notes = preferences.get("notes")
    else:
        try:
            start_time_str = raw["startTime"]
            duration_minutes = int(raw["durationMinutes"])
        except KeyError as exc:
            raise HTTPException(status_code=400, detail=f"Missing field: {exc.args[0]}") from exc
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="durationMinutes must be integer") from exc

        if duration_minutes <= 0:
            raise HTTPException(status_code=400, detail="durationMinutes must be positive")

        try:
            start_datetime = _ensure_datetime(start_time_str)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="startTime must be ISO date-time") from exc

        attendee_count = raw.get("attendeeCount") or raw.get("attendees")
        notes = raw.get("notes")

    return AvailabilityRequest(
        session_id=session_id,
        start_time=start_datetime,
        duration_minutes=duration_minutes,
        attendee_count=attendee_count,
        notes=notes,
    )


@router.post("/availability", response_model=AvailabilityResponse)
async def check_room_availability(
    payload: Dict[str, Any],
    db: AsyncSession = Depends(get_session),
) -> AvailabilityResponse:
    try:
        request_payload = AvailabilityRequest.model_validate(payload)
    except Exception:  # Payload did not match direct schema; attempt workflow conversion
        request_payload = _convert_workflow_payload(payload)

    stmt = select(Room).where(Room.venue_id == DEFAULT_VENUE_ID)
    rooms = (await db.execute(stmt)).scalars().all()

    results: list[AvailabilityResponseRoom] = []
    for room in rooms:
        end_window = request_payload.start_time + timedelta(minutes=request_payload.duration_minutes)
        conflicts_stmt = select(Booking).where(
            and_(
                Booking.room_id == room.id,
                Booking.start_time.is_not(None),
                Booking.end_time.is_not(None),
                Booking.start_time < end_window,
                Booking.end_time > request_payload.start_time,
            )
        )
        conflicts = (await db.execute(conflicts_stmt)).scalars().all()
        available = len(conflicts) == 0
        reasons: list[str] = []
        if not available:
            reasons.append("Existing booking overlaps with requested time")
        if request_payload.attendee_count and room.capacity < request_payload.attendee_count:
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
        session_id=request_payload.session_id,
        venue_id=DEFAULT_VENUE_ID,
        start_time=request_payload.start_time,
        duration_minutes=request_payload.duration_minutes,
        rooms=results,
    )

    await event_bus.publish(
        request_payload.session_id,
        {
            "type": "availability",
            "rooms": [room.model_dump() for room in results],
        },
    )
    logger.info(
        "session_event",
        extra={
            "session_id": request_payload.session_id,
            "event": "availability",
            "requested_start": request_payload.start_time.isoformat(),
            "duration_minutes": request_payload.duration_minutes,
            "available_rooms": [r.room_id for r in results if r.available],
        },
    )

    return response


@router.get("/availability")
async def availability_help() -> Dict[str, Any]:
    """Simple helper so GET probes return 200 instead of 405."""

    return {
        "message": "Use POST /api/vapi/tools/availability with JSON body.",
        "required": {
            "session_id": "string",
            "preferences": {
                "date": "YYYY-MM-DD",
                "startTime": "HH:MM",
                "durationHours": "float (>0)",
                "notes": "optional",
                "attendeeCount": "optional integer"
            }
        }
    }


def _normalize_booking_payload(raw: Dict[str, Any]) -> BookingSubmission:
    try:
        session_id = raw["session_id"]
        room_id = raw.get("room_id") or raw.get("roomId")
        venue_id = raw.get("venue_id") or raw.get("venueId") or DEFAULT_VENUE_ID
    except KeyError as exc:
        raise HTTPException(status_code=400, detail=f"Missing field: {exc.args[0]}") from exc

    def _ensure_datetime(value: str) -> datetime:
        if value.endswith("Z"):
            value = value[:-1] + "+00:00"
        dt = datetime.fromisoformat(value)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt

    start_time = raw.get("start_time") or raw.get("startTime")
    duration_minutes = raw.get("duration_minutes") or raw.get("durationMinutes")

    if start_time is None or duration_minutes is None:
        raise HTTPException(status_code=400, detail="startTime and durationMinutes are required")

    try:
        start_dt = _ensure_datetime(start_time)
        duration_minutes = int(duration_minutes)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="startTime must be ISO and durationMinutes integer") from exc

    selected_slot = raw.get("selectedSlot") or raw.get("slot") or {}

    customer = raw.get("customer") or {}
    customer_normalized = CustomerInfo(**{
        "name": customer.get("name"),
        "email": customer.get("email"),
        "phone_number": customer.get("phone_number") or customer.get("phoneNumber"),
        "attributes": customer.get("attributes", {}),
    })


    return BookingSubmission(
        session_id=session_id,
        venue_id=venue_id,
        room_id=selected_slot.get("roomId") or selected_slot.get("slotId") or room_id,
        start_time=start_dt,
        duration_minutes=duration_minutes,
        attendee_count=raw.get("attendee_count") or raw.get("attendeeCount"),
        notes=raw.get("notes") or selected_slot.get("notes"),
        details=raw.get("details", {}),
        customer=customer_normalized,
        payment_amount=raw.get("payment_amount") or raw.get("paymentAmount"),
        payment_currency=raw.get("payment_currency") or raw.get("paymentCurrency", "USD"),
    )


@router.post("/booking")
async def confirm_booking(
    payload: Dict[str, Any],
    db: AsyncSession = Depends(get_session),
    booking_service: BookingService = Depends(get_booking_service),
) -> Dict[str, Any]:
    try:
        submission = BookingSubmission.model_validate(payload)
    except Exception:
        submission = _normalize_booking_payload(payload)

    existing_stmt = select(Booking).where(
        Booking.session_id == submission.session_id,
        Booking.room_id == submission.room_id,
        Booking.start_time == submission.start_time,
    )
    existing = (await db.execute(existing_stmt)).scalar_one_or_none()

    if existing:
        logger.info(
            "session_event",
            extra={
                "session_id": submission.session_id,
                "event": "booking.already_exists",
                "booking_id": existing.id,
            },
        )
        return {
            "booking_id": existing.id,
            "door_code": existing.door_access_events[0].door_code if existing.door_access_events else None,
            "status": existing.status.value,
        }

    try:
        booking = await booking_service.confirm_booking(
            session=db,
            customer_payload=CustomerPayload(
                name=submission.customer.name,
                email=submission.customer.email,
                phone_number=submission.customer.phone_number,
                attributes=submission.customer.attributes,
            ),
            booking_payload=BookingPayload(
                session_id=submission.session_id,
                venue_id=submission.venue_id,
                room_id=submission.room_id,
                start_time=submission.start_time,
                duration_minutes=submission.duration_minutes,
                attendee_count=submission.attendee_count,
                notes=submission.notes,
                details=submission.details,
                payment_amount=submission.payment_amount,
                payment_currency=submission.payment_currency,
            ),
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    await event_bus.publish(
        submission.session_id,
        {
            "type": "booking.confirmed",
            "booking_id": booking.id,
            "room": booking.room.to_dict(include_venue=False) if booking.room else None,
            "door_code": booking.door_access_events[0].door_code if booking.door_access_events else None,
        },
    )
    logger.info(
        "session_event",
        extra={
            "session_id": submission.session_id,
            "event": "booking.confirmed",
            "booking_id": booking.id,
            "room_id": booking.room.id if booking.room else None,
            "door_code": booking.door_access_events[0].door_code if booking.door_access_events else None,
        },
    )

    payment = booking.payments[0] if booking.payments else None
    customer = booking.customer

    return {
        "booking_id": booking.id,
        "door_code": booking.door_access_events[0].door_code if booking.door_access_events else None,
        "status": booking.status.value,
        "customer": {
            "name": customer.name if customer else None,
            "email": customer.email if customer else None,
            "phone_number": customer.phone_number if customer else None,
        },
        "payment": {
            "amount": float(payment.amount) if getattr(payment, "amount", None) is not None else None,
            "currency": payment.currency if payment else None,
            "provider": payment.provider.value if payment else None,
            "status": payment.status.value if payment else None,
        } if payment else None,
    }


@router.post("/payment/apple-pay")
async def mock_apple_pay(
    payload: Dict[str, Any],
    db: AsyncSession = Depends(get_session),
    payment_service: PaymentService = Depends(get_payment_service),
) -> Dict[str, Any]:
    session_id = payload.get("session_id") or payload.get("sessionId")
    if not session_id:
        raise HTTPException(status_code=400, detail="session_id is required")

    amount_raw = payload.get("amount") or payload.get("payment_amount")
    currency = (payload.get("currency") or payload.get("payment_currency") or "USD").upper()
    booking_id = payload.get("booking_id") or payload.get("bookingId")

    amount_decimal: Decimal | None = None
    if amount_raw is not None:
        try:
            amount_decimal = Decimal(str(amount_raw))
        except (InvalidOperation, ValueError) as exc:
            raise HTTPException(status_code=400, detail="amount must be numeric") from exc

    transaction_id = payload.get("transaction_id") or f"applepay_demo_{int(datetime.utcnow().timestamp() * 1000)}"

    await asyncio.sleep(float(payload.get("processing_delay", 1.0)))

    booking: Booking | None = None
    if booking_id is not None:
        booking = await db.get(Booking, booking_id)
        if not booking:
            raise HTTPException(status_code=404, detail="booking not found")

    if booking is not None:
        await payment_service.record_payment(
            session=db,
            booking=booking,
            amount=amount_decimal,
            currency=currency,
            metadata={
                "transaction_id": transaction_id,
                "provider": "apple_pay",
            },
            status=PaymentStatus.SUCCEEDED,
        )
        await db.commit()
    else:
        _mock_payment_events.appendleft(
            {
                "id": transaction_id,
                "provider": "apple_pay",
                "status": PaymentStatus.SUCCEEDED.value,
                "amount": float(amount_decimal) if amount_decimal is not None else None,
                "currency": currency,
                "transaction_id": transaction_id,
                "created_at": datetime.utcnow().isoformat(),
            }
        )

    record = session_store.get(session_id) or SessionRecord(session_id=session_id, call_type="booking")
    record.booking_status.payment_required = False
    session_store.upsert(record)

    event_payload = {
        "type": "payment.succeeded",
        "provider": "apple_pay",
        "amount": float(amount_decimal) if amount_decimal is not None else None,
        "currency": currency,
        "transaction_id": transaction_id,
        "booking_id": booking_id,
    }

    await event_bus.publish(session_id, event_payload)
    logger.info(
        "session_event",
        extra={
            "session_id": session_id,
            "event": "payment.succeeded",
            "amount": event_payload["amount"],
            "currency": currency,
            "booking_id": booking_id,
        },
    )

    return {
        "status": "SUCCEEDED",
        "transaction_id": transaction_id,
        "provider": "apple_pay",
        "amount": float(amount_decimal) if amount_decimal is not None else None,
        "currency": currency,
        "booking_id": booking_id,
    }


@router.post("/survey")
async def log_survey(payload: Dict[str, Any]) -> Dict[str, Any]:
    session_id = payload.get("session_id")
    if session_id:
        await event_bus.publish(session_id, {"type": "survey", "data": payload})
        logger.info(
            "session_event",
            extra={
                "session_id": session_id,
                "event": "survey",
            },
        )
    return {"status": "logged"}


@router.get("/bookings")
async def list_bookings(db: AsyncSession = Depends(get_session)) -> Dict[str, Any]:
    result = await db.execute(select(Booking))
    bookings = []
    for booking in result.scalars().unique():
        payment = booking.payments[0] if booking.payments else None
        customer = booking.customer
        bookings.append(
            {
                "id": booking.id,
                "session_id": booking.session_id,
                "venue_id": booking.venue_id,
                "room_id": booking.room_id,
                "status": booking.status.value,
                "start_time": booking.start_time.isoformat() if booking.start_time else None,
                "end_time": booking.end_time.isoformat() if booking.end_time else None,
                "attendee_count": booking.attendee_count,
                "notes": booking.notes,
                "customer": {
                    "name": customer.name if customer else None,
                    "email": customer.email if customer else None,
                    "phone_number": customer.phone_number if customer else None,
                },
                "payment": {
                    "amount": float(payment.amount) if getattr(payment, "amount", None) is not None else None,
                    "currency": payment.currency if payment else None,
                    "provider": payment.provider.value if payment else None,
                    "status": payment.status.value if payment else None,
                } if payment else None,
            }
        )
    return {"bookings": bookings}


@router.get("/payments")
async def list_payments(db: AsyncSession = Depends(get_session)) -> Dict[str, Any]:
    result = await db.execute(select(Payment).order_by(Payment.created_at.desc()))
    payments: list[dict[str, Any]] = []
    for payment in result.scalars().unique():
        extras = payment.extras or {}
        transaction_id = extras.get("transaction_id") if isinstance(extras, dict) else None
        provider_hint = extras.get("provider") if isinstance(extras, dict) else None
        payments.append(
            {
                "id": payment.id,
                "booking_id": payment.booking_id,
                "provider": payment.provider.value,
                "status": payment.status.value,
                "amount": float(payment.amount) if getattr(payment, "amount", None) is not None else None,
                "currency": payment.currency,
                "transaction_id": transaction_id,
                "provider_hint": provider_hint,
                "created_at": payment.created_at.isoformat() if payment.created_at else None,
            }
        )

    mock_payments = list(_mock_payment_events)
    combined = mock_payments + payments

    return {"payments": combined}
