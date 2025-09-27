from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_healthcheck():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_list_venues_empty_when_missing_file():
    response = client.get("/api/metadata/venues")
    assert response.status_code == 200
    assert response.json() == []
