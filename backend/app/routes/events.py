from __future__ import annotations

import asyncio
import json
from typing import AsyncGenerator

from fastapi import APIRouter
from sse_starlette.sse import EventSourceResponse

from app.stores.event_bus import event_bus

router = APIRouter(prefix="/events", tags=["events"])


async def _event_stream(session_id: str) -> AsyncGenerator[str, None]:
    yield json.dumps({"type": "status", "status": "listening", "session_id": session_id})

    async def heartbeat() -> None:
        while True:
            await asyncio.sleep(15)
            await event_bus.publish(session_id, {"type": "heartbeat", "session_id": session_id})

    task = asyncio.create_task(heartbeat())
    try:
        async for event in event_bus.stream(session_id):
            yield json.dumps(event)
    finally:
        task.cancel()


@router.get("/{session_id}")
async def listen(session_id: str) -> EventSourceResponse:
    return EventSourceResponse(_event_stream(session_id))
