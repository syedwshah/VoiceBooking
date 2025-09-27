from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field

from app.services.vapi_service import VapiService, get_vapi_service
from app.services.summary_service import SummaryService, get_summary_service
from app.stores.session_store import SessionRecord, session_store
from app.stores.session_store import TranscriptEntry
from app.stores.event_bus import event_bus


class CallBrief(BaseModel):
    session_id: str = Field(..., description="Unique ID for tracking the call workflow")
    call_type: str = Field(..., pattern="^(outreach|booking)$")
    target_contact: Optional[str] = None
    objective: Optional[str] = None
    notes: Optional[str] = None
    venue_id: Optional[str] = None
    phone_number: Optional[str] = Field(None, pattern=r"^\+?[0-9]{7,15}$")


class CallLaunchResponse(BaseModel):
    session_id: str
    status: str


router = APIRouter(prefix="/calls", tags=["calls"])


@router.post("/launch", response_model=CallLaunchResponse)
async def launch_call(
    brief: CallBrief,
    vapi_service: VapiService = Depends(get_vapi_service),
) -> CallLaunchResponse:
    """Kick off a Vapi call using the provided brief."""

    if not vapi_service.is_configured():
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Vapi is not configured")

    session_store.upsert(
        SessionRecord(
            session_id=brief.session_id,
            call_type=brief.call_type,
            brief=brief.model_dump(),
        )
    )

    await vapi_service.launch_call(brief)

    return CallLaunchResponse(session_id=brief.session_id, status="queued")


@router.post("/webhooks/vapi")
async def handle_vapi_webhook(
    request: Request,
    vapi_service: VapiService = Depends(get_vapi_service),
    summary_service: SummaryService = Depends(get_summary_service),
) -> dict[str, str]:
    payload = await request.json()
    session_id = payload.get("session_id") or payload.get("sessionId")
    event_type = payload.get("event")

    if not session_id:
        return {"status": "ignored"}

    if event_type == "transcript.append":
        data = payload.get("data", {})
        text = data.get("text")
        speaker = data.get("speaker", "agent")
        if text:
            session_store.append_transcript(
                session_id,
                TranscriptEntry(role=speaker, content=text, timestamp=data.get("timestamp", 0.0)),
            )
            await event_bus.publish(session_id, {"type": "transcript", "speaker": speaker, "text": text})
    elif event_type in {"call.started", "call.ringing", "call.completed", "call.failed"}:
        status_map = {
            "call.started": "in_progress",
            "call.ringing": "dialing",
            "call.completed": "completed",
            "call.failed": "failed",
        }
        await event_bus.publish(session_id, {"type": "status", "status": status_map[event_type]})
        record = session_store.get(session_id)
        if record:
            record.brief.setdefault("statuses", []).append(event_type)
            session_store.upsert(record)
        if event_type == "call.completed":
            summary_service.schedule_summary(session_id)

    return {"status": "accepted"}

    return {"status": "accepted"}
