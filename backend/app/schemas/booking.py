from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class CustomerInfo(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    phone_number: Optional[str] = None
    attributes: Dict[str, Any] = Field(default_factory=dict)


class BookingSubmission(BaseModel):
    session_id: str
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


class AvailabilityRequest(BaseModel):
    session_id: str
    start_time: datetime
    duration_minutes: int
    attendee_count: Optional[int] = None
    notes: Optional[str] = None


class AvailabilityResponseRoom(BaseModel):
    room_id: str
    label: str
    capacity: int
    available: bool
    reasons: list[str] = Field(default_factory=list)


class AvailabilityResponse(BaseModel):
    session_id: str
    venue_id: str
    start_time: datetime
    duration_minutes: int
    rooms: list[AvailabilityResponseRoom]
