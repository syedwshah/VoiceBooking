from __future__ import annotations

import asyncio
import json
from typing import AsyncGenerator

from fastapi import APIRouter
from sse_starlette.sse import EventSourceResponse

router = APIRouter(prefix="/events", tags=["events"])


async def _event_stream(session_id: str) -> AsyncGenerator[str, None]:
    yield json.dumps({"type": "status", "status": "listening", "session_id": session_id})
    try:
        while True:
            await asyncio.sleep(15)
            yield json.dumps({"type": "heartbeat", "session_id": session_id})
    except asyncio.CancelledError:  # pragma: no cover
        return


@router.get("/{session_id}")
async def listen(session_id: str) -> EventSourceResponse:
    return EventSourceResponse(_event_stream(session_id))
