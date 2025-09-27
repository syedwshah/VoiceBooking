from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from sqlalchemy import ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from app.db.base import Base

try:  # pragma: no cover - optional Postgres optimization
    from sqlalchemy.dialects.postgresql import JSONB as JSONType  # type: ignore
except ImportError:  # pragma: no cover
    JSONType = JSON  # type: ignore

if TYPE_CHECKING:  # pragma: no cover
    from .booking import Booking


class Venue(Base):
    __tablename__ = "venues"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    address: Mapped[Optional[str]] = mapped_column(String(255))
    contact: Mapped[Optional[str]] = mapped_column(String(255))
    policies: Mapped[Dict[str, Any]] = mapped_column(JSONType, default=dict)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now(), nullable=False)

    rooms: Mapped[List["Room"]] = relationship(
        back_populates="venue",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    bookings: Mapped[List["Booking"]] = relationship(
        back_populates="venue",
        lazy="selectin",
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "address": self.address,
            "contact": self.contact,
            "policies": self.policies or {},
            "rooms": [room.to_dict(include_venue=False) for room in self.rooms],
        }


class Room(Base):
    __tablename__ = "rooms"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    venue_id: Mapped[str] = mapped_column(ForeignKey("venues.id", ondelete="CASCADE"), nullable=False, index=True)
    label: Mapped[str] = mapped_column(String(255), nullable=False)
    capacity: Mapped[int] = mapped_column(Integer, nullable=False)
    amenities: Mapped[List[str]] = mapped_column(JSONType, default=list)
    availability: Mapped[Dict[str, Any]] = mapped_column(JSONType, default=dict)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now(), nullable=False)

    venue: Mapped[Venue] = relationship(back_populates="rooms", lazy="joined")
    bookings: Mapped[List["Booking"]] = relationship(
        "Booking",
        back_populates="room",
        lazy="selectin",
    )

    def to_dict(self, include_venue: bool = True) -> Dict[str, Any]:
        data: Dict[str, Any] = {
            "id": self.id,
            "venue_id": self.venue_id,
            "label": self.label,
            "capacity": self.capacity,
            "amenities": self.amenities or [],
            "availability": self.availability or {},
        }
        if include_venue:
            data["venue"] = {
                "id": self.venue.id,
                "name": self.venue.name,
            }
        return data
