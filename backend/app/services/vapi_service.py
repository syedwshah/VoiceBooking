from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING, Any, Dict, List

import httpx

from app.utils.config import get_settings

if TYPE_CHECKING:  # pragma: no cover
    from app.routes.calls import CallBrief


logger = logging.getLogger(__name__)


class VapiService:
    """Wrapper around Vapi API for launching calls and responding to tool executions."""

    BASE_URL = "https://api.vapi.ai/api/v1"

    def __init__(self) -> None:
        self.settings = get_settings()
        self._client = httpx.AsyncClient(timeout=20.0)

    def is_configured(self) -> bool:
        return bool(self.settings.vapi_private_key)

    async def launch_call(self, brief: "CallBrief") -> None:
        payload = self._build_call_payload(brief)
        headers = self._headers()

        try:
            response = await self._client.post(
                f"{self.BASE_URL}/calls",
                headers=headers,
                json=payload,
            )
            logger.info(
                "Vapi launch response",
                extra={
                    "session_id": brief.session_id,
                    "payload": payload,
                    "status": response.status_code,
                    "body": response.text,
                },
            )
            response.raise_for_status()
        except httpx.HTTPError as error:
            logger.exception(
                "Failed to launch Vapi call",
                extra={
                    "session_id": brief.session_id,
                    "error": str(error),
                    "payload": payload,
                },
            )

    async def send_tool_result(self, call_id: str, tool_call_id: str, result: Dict[str, Any]) -> None:
        """Optionally forward tool execution results back to Vapi."""

        headers = self._headers()
        payload = {"toolCallId": tool_call_id, "result": result}
        try:
            response = await self._client.post(
                f"{self.BASE_URL}/calls/{call_id}/tool-results",
                headers=headers,
                json=payload,
            )
            response.raise_for_status()
        except httpx.HTTPError as error:
            logger.warning(
                "Failed to send tool result to Vapi",
                extra={"call_id": call_id, "tool_call_id": tool_call_id, "error": str(error)},
            )

    def _headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.settings.vapi_private_key}",
            "x-public-key": self.settings.vapi_public_key,
            "Content-Type": "application/json",
        }

    def _build_call_payload(self, brief: "CallBrief") -> Dict[str, Any]:
        persona = "booking" if brief.call_type == "booking" else "outreach"
        instructions = self._build_instructions(brief)
        tools = self._tool_definitions()

        payload: Dict[str, Any] = {
            "sessionId": brief.session_id,
            "assistant": {
                "name": f"VoiceBooking {persona.title()} Agent",
                "model": "gpt-4o-mini",
                "voice": {"provider": "twilio", "voiceId": "alloy"},
                "instructions": instructions,
                "tools": tools,
            },
            "metadata": {
                "persona": persona,
                "objective": brief.objective,
                "notes": brief.notes,
                "venueId": brief.venue_id,
            },
        }

        call_config: Dict[str, Any] = {}
        if getattr(brief, "phone_number", None):
            call_config["customer"] = {
                "phoneNumber": brief.phone_number,
                "name": brief.target_contact or "Caller",
            }
        if self.settings.twilio_phone_number:
            call_config.setdefault("business", {})["phoneNumber"] = self.settings.twilio_phone_number

        if call_config:
            payload["call"] = call_config

        return payload

    def _build_instructions(self, brief: "CallBrief") -> str:
        intro = "You are a concierge for VoiceBooking helping clients plan outreach and workspace bookings."
        if brief.call_type == "booking":
            objective = "Capture caller details, confirm their booking needs, verify availability, and use the provided tools to finalize a reservation, collect payment, issue a door code, and summarize the outcome."
        else:
            objective = "Gather context for outreach, capture key notes, and schedule any requested follow-up actions."

        venue_context = ""
        if brief.venue_id:
            venue_context = f"Focus on venue id {brief.venue_id} when recommending rooms."

        return "\n".join([
            intro,
            objective,
            "Always confirm information back to the caller before finalizing.",
            venue_context,
            "Call the REST tools when you need to persist data or retrieve availability.",
        ]).strip()

    def _tool_definitions(self) -> List[Dict[str, Any]]:
        base_url = self.settings.public_backend_url.rstrip("/")
        return [
            {
                "name": "store_customer_profile",
                "description": "Persist caller contact details and session context.",
                "type": "rest",
                "spec": {
                    "url": f"{base_url}/api/vapi/tools/customer",
                    "method": "POST",
                },
            },
            {
                "name": "check_room_availability",
                "description": "Check availability for a venue and time window.",
                "type": "rest",
                "spec": {
                    "url": f"{base_url}/api/vapi/tools/availability",
                    "method": "POST",
                },
            },
            {
                "name": "confirm_booking",
                "description": "Create a booking, charge the caller (sandbox), generate a door code, and send a summary.",
                "type": "rest",
                "spec": {
                    "url": f"{base_url}/api/vapi/tools/booking",
                    "method": "POST",
                },
            },
            {
                "name": "log_follow_up_survey",
                "description": "Store survey responses after a follow-up call.",
                "type": "rest",
                "spec": {
                    "url": f"{base_url}/api/vapi/tools/survey",
                    "method": "POST",
                },
            },
        ]


_vapi_service: VapiService | None = None


def get_vapi_service() -> VapiService:
    global _vapi_service
    if not _vapi_service:
        _vapi_service = VapiService()
    return _vapi_service
