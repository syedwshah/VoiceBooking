from __future__ import annotations

import logging
import uuid
from dataclasses import asdict
from typing import Any, Dict

from app.services.key_service import KeyService, get_key_service
from app.stores.session_store import BookingStatus, session_store

logger = logging.getLogger(__name__)


class BookingService:
    def __init__(self, key_service: KeyService | None = None) -> None:
        self.key_service = key_service or get_key_service()

    def confirm_booking(self, session_id: str, payload: Dict[str, Any]) -> BookingStatus:
        booking_id = str(payload.get("booking_id") or uuid.uuid4())
        booking_status = BookingStatus(
            status="confirmed",
            booking_id=booking_id,
            room_id=payload.get("room_id"),
            check_in_time=payload.get("check_in_time"),
        )

        key_token = self.key_service.issue_key(booking_id=booking_id, session_id=session_id)
        booking_status.key_token = key_token

        session_store.update_booking_status(session_id, booking_status)
        logger.info("Booking confirmed", extra={"session_id": session_id, "booking_status": asdict(booking_status)})
        return booking_status

    def require_payment(self, session_id: str) -> BookingStatus:
        status = BookingStatus(status="pending", payment_required=True)
        session_store.update_booking_status(session_id, status)
        logger.info("Payment required before booking confirmation", extra={"session_id": session_id})
        return status


_booking_service: BookingService | None = None


def get_booking_service() -> BookingService:
    global _booking_service
    if not _booking_service:
        _booking_service = BookingService()
    return _booking_service
