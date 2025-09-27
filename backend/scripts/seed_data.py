from __future__ import annotations

import asyncio
import json
from pathlib import Path

from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from app.db.database import async_session_factory
from app.models import (
    Booking,
    BookingStatus,
    Customer,
    DoorAccessEvent,
    Payment,
    PaymentProvider,
    PaymentStatus,
    Room,
    SurveyResponse,
    Venue,
)
from app.utils.config import get_settings


async def seed() -> None:
    settings = get_settings()
    venue_path = Path(settings.venue_data_path)
    if not venue_path.is_absolute():
        venue_path = Path(__file__).resolve().parents[2] / venue_path
    if not venue_path.exists():
        raise FileNotFoundError(f"Seed data file not found: {venue_path}")

    payload = json.loads(venue_path.read_text(encoding="utf-8"))

    async with async_session_factory() as session:
        # Seed venues and rooms
        for venue_payload in payload:
            venue_id = str(venue_payload["id"])
            existing = await session.get(Venue, venue_id)
            if existing:
                continue

            venue = Venue(
                id=venue_id,
                name=venue_payload.get("name", venue_id.title()),
                address=venue_payload.get("address"),
                contact=venue_payload.get("contact"),
                policies=venue_payload.get("policies", {}),
            )

            for room_payload in venue_payload.get("rooms", []):
                room = Room(
                    id=str(room_payload["id"]),
                    label=room_payload.get("label", room_payload["id"]),
                    capacity=int(room_payload.get("capacity", 0)),
                    amenities=room_payload.get("amenities", []),
                    availability=room_payload.get("availability", {}),
                )
                venue.rooms.append(room)

            session.add(venue)

        await session.commit()

        # Fetch seeded data for relationships
        aurora_main = await session.get(Room, "aurora-main")
        harbor_atrium = await session.get(Room, "harbor-atrium")

        if not aurora_main or not harbor_atrium:
            return

        # Seed customers
        customers_seed = [
            {
                "name": "Jordan Michaels",
                "email": "jordan@example.com",
                "phone": "+14015551212",
                "attributes": {"organization": "FlowTech"},
            },
            {
                "name": "Priya Natarajan",
                "email": "priya@example.com",
                "phone": "+14155551313",
                "attributes": {"organization": "Northstar Ventures"},
            },
        ]

        customers: list[Customer] = []
        for record in customers_seed:
            stmt = select(Customer).where(Customer.email == record["email"])
            existing_customer = (await session.execute(stmt)).scalar_one_or_none()
            if existing_customer:
                customers.append(existing_customer)
                continue

            customer = Customer(
                name=record["name"],
                email=record["email"],
                phone_number=record["phone"],
                attributes=record["attributes"],
            )
            session.add(customer)
            customers.append(customer)

        await session.flush()

        now = datetime.now(timezone.utc)

        # Seed bookings with mock payments and door access events
        seeded_bookings = [
            {
                "room": aurora_main,
                "customer": customers[0],
                "start": now + timedelta(days=3, hours=10),
                "duration": 180,
                "attendees": 45,
                "details": {
                    "purpose": "Investor update showcase",
                    "catering": "Arranged via Brightline",
                },
            },
            {
                "room": harbor_atrium,
                "customer": customers[1],
                "start": now + timedelta(days=5, hours=13),
                "duration": 120,
                "attendees": 28,
                "details": {
                    "purpose": "Team offsite planning",
                    "layout": "Workshop clusters",
                },
            },
        ]

        for record in seeded_bookings:
            existing_stmt = select(Booking).where(
                Booking.customer_id == record["customer"].id,
                Booking.room_id == record["room"].id,
            )
            existing_booking = (await session.execute(existing_stmt)).scalar_one_or_none()
            if existing_booking:
                continue

            booking = Booking(
                customer=record["customer"],
                venue=record["room"].venue,
                room=record["room"],
                status=BookingStatus.CONFIRMED.value,
                start_time=record["start"],
                end_time=record["start"] + timedelta(minutes=record["duration"]),
                duration_minutes=record["duration"],
                attendee_count=record["attendees"],
                details=record["details"],
            )

            payment = Payment(
                booking=booking,
                provider=PaymentProvider.MCP_SANDBOX,
                status=PaymentStatus.SUCCEEDED.value,
                amount=500.00,
                currency="USD",
                extras={"sandbox_receipt": "rcpt-mock-1234"},
            )

            door_access = DoorAccessEvent(
                booking=booking,
                door_code="8421",
                instructions="Use elevator bank B to level 3, suite 305. Code expires 2 hours after event start.",
                expires_at=booking.end_time + timedelta(hours=2),
                context={"note": "Demo access code"},
            )

            survey = SurveyResponse(
                booking=booking,
                rating=5,
                comments="Flawless setup and smooth check-in.",
                transcript="Loved the space and the seamless entry process.",
                action_items=["Follow up with catering preferences"],
            )

            session.add_all([booking, payment, door_access, survey])

        await session.commit()


if __name__ == "__main__":
    asyncio.run(seed())
