from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.services.booking_service import BookingService, get_booking_service
from app.stores.session_store import session_store


class BookingConfirmation(BaseModel):
    room_id: str
    check_in_time: str
    attendees: int | None = None
    booking_id: str | None = None


router = APIRouter(prefix="/booking", tags=["booking"])


@router.post("/{session_id}/confirm")
def confirm_booking(
    session_id: str,
    payload: BookingConfirmation,
    booking_service: BookingService = Depends(get_booking_service),
):
    session = session_store.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    booking_status = booking_service.confirm_booking(
        session_id=session_id,
        payload=payload.model_dump(exclude_none=True),
    )
    return {"status": booking_status.status, "booking": booking_status.__dict__}


@router.post("/{session_id}/key")
def regenerate_key(
    session_id: str,
    booking_service: BookingService = Depends(get_booking_service),
):
    session = session_store.get(session_id)
    if not session or not session.booking_status.booking_id:
        raise HTTPException(status_code=404, detail="Booking not found")

    booking_status = booking_service.confirm_booking(
        session_id=session_id,
        payload={
            "booking_id": session.booking_status.booking_id,
            "room_id": session.booking_status.room_id or "",
            "check_in_time": session.booking_status.check_in_time or "",
        },
    )
    return {"status": booking_status.status, "booking": booking_status.__dict__}
