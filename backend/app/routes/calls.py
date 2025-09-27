from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field

from app.services.vapi_service import VapiService, get_vapi_service
from app.services.summary_service import SummaryService, get_summary_service
from app.stores.session_store import SessionRecord, session_store


class CallBrief(BaseModel):
    session_id: str = Field(..., description="Unique ID for tracking the call workflow")
    call_type: str = Field(..., pattern="^(outreach|booking)$")
    target_contact: Optional[str] = None
    objective: Optional[str] = None
    notes: Optional[str] = None
    venue_id: Optional[str] = None


class CallLaunchResponse(BaseModel):
    session_id: str
    status: str


router = APIRouter(prefix="/calls", tags=["calls"])


@router.post("/launch", response_model=CallLaunchResponse)
async def launch_call(
    brief: CallBrief,
    background_tasks: BackgroundTasks,
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

    background_tasks.add_task(vapi_service.launch_call, brief)

    return CallLaunchResponse(session_id=brief.session_id, status="queued")


@router.post("/webhooks/vapi")
async def handle_vapi_webhook(
    request: Request,
    vapi_service: VapiService = Depends(get_vapi_service),
    summary_service: SummaryService = Depends(get_summary_service),
) -> dict[str, str]:
    payload = await request.json()
    vapi_service.process_webhook(payload)

    if payload.get("event") == "call.completed":
        session_id = payload.get("session_id")
        if session_id:
            summary_service.schedule_summary(session_id)

    return {"status": "accepted"}
