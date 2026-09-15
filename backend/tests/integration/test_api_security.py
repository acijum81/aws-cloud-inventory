from fastapi.testclient import TestClient

from main import app


def test_read_endpoints_fail_closed_without_keys(monkeypatch) -> None:
    monkeypatch.delenv("INVENTORY_READ_API_KEY", raising=False)
    monkeypatch.delenv("INVENTORY_WRITE_API_KEY", raising=False)
    response = TestClient(app).get("/api/v1/resources/summary")
    assert response.status_code == 503


def test_read_endpoints_reject_invalid_key(monkeypatch) -> None:
    monkeypatch.setenv("INVENTORY_READ_API_KEY", "read-key")
    monkeypatch.setenv("INVENTORY_WRITE_API_KEY", "write-key")
    response = TestClient(app).get("/api/v1/resources/summary", headers={"X-API-Key": "wrong"})
    assert response.status_code == 401


def test_inventory_request_validates_account_id_before_execution(monkeypatch) -> None:
    monkeypatch.setenv("INVENTORY_READ_API_KEY", "read-key")
    monkeypatch.setenv("INVENTORY_WRITE_API_KEY", "write-key")
    monkeypatch.setenv("INVENTORY_ALLOWED_ACCOUNT_IDS", "123456789012")
    response = TestClient(app).post(
        "/api/v1/inventory-runs",
        headers={"X-API-Key": "write-key"},
        json={"account_ids": ["not-an-account"]},
    )
    assert response.status_code == 422
