from __future__ import annotations

import asyncio
import logging
from typing import Dict

from app.stores.session_store import session_store

logger = logging.getLogger(__name__)


class SummaryService:
    """Generates summaries for completed calls (stub implementation)."""

    def schedule_summary(self, session_id: str) -> None:
        asyncio.create_task(self._generate_summary(session_id))

    async def _generate_summary(self, session_id: str) -> None:
        await asyncio.sleep(0)  # placeholder async work
        summary: Dict[str, str] = {
            "headline": "Summary generation stub",
            "notes": "Hook up OpenAI responses here.",
        }
        session_store.update_summary(session_id, summary)
        logger.info("Summary generated", extra={"session_id": session_id})


_summary_service: SummaryService | None = None


def get_summary_service() -> SummaryService:
    global _summary_service
    if not _summary_service:
        _summary_service = SummaryService()
    return _summary_service
