from __future__ import annotations

import asyncio
import json
import logging
from collections import defaultdict
from typing import Any, AsyncIterator, DefaultDict


logger = logging.getLogger(__name__)


class EventBus:
    """Simple in-memory event bus for streaming session updates."""

    def __init__(self) -> None:
        self._queues: DefaultDict[str, asyncio.Queue[dict[str, Any]]] = defaultdict(asyncio.Queue)

    async def publish(self, session_id: str, event: dict[str, Any]) -> None:
        await self._queues[session_id].put(event)
        logger.info(
            "session_event",
            extra={
                "session_id": session_id,
                "event": event,
                "event_json": json.dumps(event),
            },
        )

    async def stream(self, session_id: str) -> AsyncIterator[dict[str, Any]]:
        queue = self._queues[session_id]
        while True:
            event = await queue.get()
            yield event


event_bus = EventBus()
