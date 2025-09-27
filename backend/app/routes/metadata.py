from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_session
from app.models import Venue
from app.stores.session_store import session_store


router = APIRouter(prefix="/metadata", tags=["metadata"])


@router.get("/venues")
async def list_venues(session: AsyncSession = Depends(get_session)) -> list[dict]:
    result = await session.execute(select(Venue).order_by(Venue.name))
    venues = result.scalars().unique().all()
    return [venue.to_dict() for venue in venues]


@router.get("/venues/{venue_id}")
async def get_venue(venue_id: str, session: AsyncSession = Depends(get_session)) -> dict:
    result = await session.execute(select(Venue).where(Venue.id == venue_id))
    venue = result.scalar_one_or_none()
    if not venue:
        raise HTTPException(status_code=404, detail="Venue not found")
    return venue.to_dict()


@router.get("/sessions/{session_id}")
def get_session(session_id: str) -> dict:
    record = session_store.get(session_id)
    if not record:
        raise HTTPException(status_code=404, detail="Session not found")
    return {
        "session_id": record.session_id,
        "call_type": record.call_type,
        "brief": record.brief,
        "summary": record.summary,
        "booking_status": record.booking_status.__dict__,
    }
