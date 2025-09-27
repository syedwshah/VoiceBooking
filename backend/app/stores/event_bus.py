from __future__ import annotations

import asyncio
from collections import defaultdict
from typing import Any, AsyncIterator, DefaultDict


class EventBus:
    """Simple in-memory event bus for streaming session updates."""

    def __init__(self) -> None:
        self._queues: DefaultDict[str, asyncio.Queue[dict[str, Any]]] = defaultdict(asyncio.Queue)

    async def publish(self, session_id: str, event: dict[str, Any]) -> None:
        await self._queues[session_id].put(event)

    async def stream(self, session_id: str) -> AsyncIterator[dict[str, Any]]:
        queue = self._queues[session_id]
        while True:
            event = await queue.get()
            yield event


event_bus = EventBus()
