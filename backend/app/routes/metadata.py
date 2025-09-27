from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.data.venue_loader import get_venue_by_id, load_venues
from app.stores.session_store import session_store


router = APIRouter(prefix="/metadata", tags=["metadata"])


@router.get("/venues")
def list_venues() -> list[dict]:
    return load_venues()


@router.get("/venues/{venue_id}")
def get_venue(venue_id: str) -> dict:
    venue = get_venue_by_id(venue_id)
    if not venue:
        raise HTTPException(status_code=404, detail="Venue not found")
    return venue


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
