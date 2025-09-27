from __future__ import annotations

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.services.realtime_service import RealtimeService, get_realtime_service


router = APIRouter(prefix="/ws", tags=["realtime"])


@router.websocket("/booking/{session_id}")
async def booking_chat_websocket(websocket: WebSocket, session_id: str) -> None:
    await websocket.accept()
    service = get_realtime_service()

    try:
        async for message in service.stream(session_id=session_id, client=websocket):
            await websocket.send_text(message)
    except WebSocketDisconnect:
        await service.disconnect(session_id, websocket)
