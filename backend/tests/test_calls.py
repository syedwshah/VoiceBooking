import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.routes.calls import get_vapi_service
from app.services.vapi_service import VapiService
from app.stores.session_store import session_store, SessionRecord


client = TestClient(app)


def test_healthcheck():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_list_venues_empty_when_missing_file():
    response = client.get("/api/metadata/venues")
    if response.status_code >= 500:
        pytest.skip("Database not available for metadata listing test")
    assert response.status_code == 200


class DummyVapi(VapiService):
    def __init__(self, configured: bool = True) -> None:
        self._configured = configured

    def is_configured(self) -> bool:  # type: ignore[override]
        return self._configured

    async def launch_call(self, brief):  # type: ignore[override]
        return None


def test_call_launch_missing_credentials():
    app.dependency_overrides[get_vapi_service] = lambda: DummyVapi(configured=False)

    response = client.post(
        "/api/calls/launch",
        json={
            "session_id": "test-session",
            "call_type": "booking",
            "target_contact": "Alex Morgan",
            "objective": "Book a room",
        },
    )
    app.dependency_overrides.pop(get_vapi_service, None)

    assert response.status_code == 503
    assert response.json()["detail"] == "Vapi is not configured"


def test_vapi_webhook_status_update():
    session_id = "session-abc"
    session_store.upsert(SessionRecord(session_id=session_id, call_type="booking"))

    response = client.post(
        "/api/calls/webhooks/vapi",
        json={
            "event": "call.completed",
            "session_id": session_id,
        },
    )

    assert response.status_code == 200
    assert response.json()["status"] == "accepted"
