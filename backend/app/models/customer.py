from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List

from sqlalchemy import String, func
from sqlalchemy.types import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

try:  # pragma: no cover
    from sqlalchemy.dialects.postgresql import JSONB as JSONType  # type: ignore
except ImportError:  # pragma: no cover
    JSONType = JSON  # type: ignore


class Customer(Base):
    __tablename__ = "customers"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    external_id: Mapped[str | None] = mapped_column(String(64), unique=True)
    name: Mapped[str | None] = mapped_column(String(255))
    email: Mapped[str | None] = mapped_column(String(255))
    phone_number: Mapped[str | None] = mapped_column(String(32))
    attributes: Mapped[Dict[str, Any]] = mapped_column(JSONType, default=dict)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now(), nullable=False)

    bookings: Mapped[List["Booking"]] = relationship(back_populates="customer", lazy="selectin")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "external_id": self.external_id,
            "name": self.name,
            "email": self.email,
            "phone_number": self.phone_number,
            "attributes": self.attributes or {},
        }
