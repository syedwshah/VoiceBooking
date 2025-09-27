from __future__ import annotations

import asyncio
import json
from pathlib import Path

from app.db.database import async_session_factory
from app.models import Room, Venue
from app.utils.config import get_settings


async def seed() -> None:
    settings = get_settings()
    venue_path = Path(settings.venue_data_path)
    if not venue_path.exists():
        raise FileNotFoundError(f"Seed data file not found: {venue_path}")

    payload = json.loads(venue_path.read_text(encoding="utf-8"))

    async with async_session_factory() as session:
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


if __name__ == "__main__":
    asyncio.run(seed())
