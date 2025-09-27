from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Booking, DoorAccessEvent


class DoorAccessService:
    """Generates and persists mock door codes for bookings."""

    def __init__(self, code_length: int = 4, expiry_offset: timedelta = timedelta(hours=2)) -> None:
        self.code_length = code_length
        self.expiry_offset = expiry_offset

    def _generate_code(self) -> str:
        return "".join(secrets.choice("0123456789") for _ in range(self.code_length))

    async def issue_access(
        self,
        session: AsyncSession,
        booking: Booking,
        instructions: Optional[str] = None,
    ) -> DoorAccessEvent:
        # Reuse existing event if present
        existing = booking.door_access_events[0] if booking.door_access_events else None

        door_code = self._generate_code()
        expires_at = (booking.end_time or booking.start_time or datetime.now(timezone.utc)) + self.expiry_offset
        instructions = instructions or "Use the provided code at the main entrance keypad."

        if existing:
            existing.door_code = door_code
            existing.instructions = instructions
            existing.expires_at = expires_at
            await session.flush()
            return existing

        event = DoorAccessEvent(
            booking=booking,
            door_code=door_code,
            instructions=instructions,
            expires_at=expires_at,
            context={"source": "demo"},
        )
        session.add(event)
        await session.flush()
        return event


def get_door_access_service() -> DoorAccessService:
    return DoorAccessService()
