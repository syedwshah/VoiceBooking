from __future__ import annotations

import asyncio
import json
import logging
from typing import AsyncGenerator

from fastapi import WebSocket

from app.utils.config import get_settings

logger = logging.getLogger(__name__)


class RealtimeService:
    """Bridge between frontend WebSocket and OpenAI Realtime API (stub)."""

    def __init__(self) -> None:
        self.settings = get_settings()

    async def stream(self, session_id: str, client: WebSocket) -> AsyncGenerator[str, None]:
        logger.info("Realtime session started", extra={"session_id": session_id})
        await asyncio.sleep(0)  # yield control
        yield json.dumps({"type": "system", "message": "Realtime service stub active."})

    async def disconnect(self, session_id: str, client: WebSocket) -> None:
        logger.info("Realtime session closed", extra={"session_id": session_id})


_realtime_service: RealtimeService | None = None


def get_realtime_service() -> RealtimeService:
    global _realtime_service
    if not _realtime_service:
        _realtime_service = RealtimeService()
    return _realtime_service
