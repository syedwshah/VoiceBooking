from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING, Any, Dict

import httpx

from app.utils.config import get_settings

if TYPE_CHECKING:  # pragma: no cover
    from app.routes.calls import CallBrief


logger = logging.getLogger(__name__)


class VapiService:
    """Lightweight wrapper around Vapi APIs."""

    def __init__(self) -> None:
        self.settings = get_settings()
        self._client = httpx.Client(timeout=10.0)

    def is_configured(self) -> bool:
        return bool(self.settings.vapi_private_key)

    def launch_call(self, brief: "CallBrief") -> None:
        payload = {
            "sessionId": brief.session_id,
            "callType": brief.call_type,
            "metadata": {
                "targetContact": brief.target_contact,
                "objective": brief.objective,
                "notes": brief.notes,
                "venueId": brief.venue_id,
            },
        }

        headers = {
            "Authorization": f"Bearer {self.settings.vapi_private_key}",
            "x-public-key": self.settings.vapi_public_key,
            "Content-Type": "application/json",
        }

        try:
            response = self._client.post(
                "https://api.vapi.ai/calls",
                headers=headers,
                json=payload,
            )
            response.raise_for_status()
            logger.info("Vapi call launched", extra={"session_id": brief.session_id})
        except httpx.HTTPError as error:
            logger.exception(
                "Failed to launch Vapi call",
                extra={"session_id": brief.session_id, "error": str(error)},
            )

    def process_webhook(self, payload: Dict[str, Any]) -> None:
        logger.debug("Received Vapi webhook: %s", json.dumps(payload))
        # TODO: enrich session store, broadcast SSE updates


_vapi_service: VapiService | None = None


def get_vapi_service() -> VapiService:
    global _vapi_service
    if not _vapi_service:
        _vapi_service = VapiService()
    return _vapi_service
