from __future__ import annotations

import logging
import secrets

logger = logging.getLogger(__name__)


class KeyService:
    """Placeholder smart-lock integration."""

    def issue_key(self, booking_id: str, session_id: str) -> str:
        token = secrets.token_urlsafe(12)
        logger.info("Issued key token", extra={"session_id": session_id, "booking_id": booking_id})
        return token

    def revoke_key(self, booking_id: str) -> None:
        logger.info("Revoked key token", extra={"booking_id": booking_id})


_key_service: KeyService | None = None


def get_key_service() -> KeyService:
    global _key_service
    if not _key_service:
        _key_service = KeyService()
    return _key_service
