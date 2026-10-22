import json
from uuid import uuid4

from fastapi.testclient import TestClient

from app.services.evaluator import demo_bundle


def upload(client):
    return client.post("/models", data={"name": "ownership-check", "model_type": "linear_json"},
        files={"file": ("model.json", json.dumps(demo_bundle()).encode(), "application/json")}).json()["id"]


def test_other_user_cannot_read_or_scan_models(auth_client):
    model_id = upload(auth_client)
    scan_id = auth_client.post("/scans", json={"model_id": model_id}).json()["id"]
    other = TestClient(auth_client.app)
    tokens = other.post("/auth/register", json={"email": f"{uuid4()}@example.com", "password": "other-user-password"}).json()
    other.headers["Authorization"] = "Bearer " + tokens["access_token"]
    assert other.get("/models").json() == []
    assert other.post("/scans", json={"model_id": model_id}).status_code == 404
    assert other.get(f"/models/{model_id}/scans").status_code == 404
    for suffix in ["", "/score", "/findings", "/report"]:
        assert other.get(f"/scans/{scan_id}{suffix}").status_code == 404


def test_invalid_upload_does_not_persist(auth_client):
    before = len(auth_client.get("/models").json())
    for payload in [b"", b"not-json", b"{}", b"null"]:
        result = auth_client.post("/models", data={"name": "bad", "model_type": "linear_json"},
            files={"file": ("model.json", payload, "application/json")})
        assert result.status_code == 422
    assert len(auth_client.get("/models").json()) == before


def test_executable_model_formats_rejected(auth_client):
    assert auth_client.post("/models", data={"name": "pickle", "model_type": "sklearn"},
        files={"file": ("model.pkl", b"not-safe", "application/octet-stream")}).status_code == 400


def test_oversized_upload_cleans_file(auth_client, monkeypatch):
    from app.core.config import settings
    monkeypatch.setattr(settings, "MAX_MODEL_SIZE_MB", 0)
    assert auth_client.post("/models", data={"name": "large", "model_type": "linear_json"},
        files={"file": ("model.json", b"{}", "application/json")}).status_code == 413


def test_password_byte_limit(client):
    assert client.post("/auth/register", json={"email": "long@example.com", "password": "x" * 73}).status_code == 422
    assert client.post("/auth/register", json={"email": "unicode@example.com", "password": "\u20ac" * 25}).status_code == 422


def test_query_token_is_not_accepted_for_reports(auth_client):
    model_id = upload(auth_client)
    scan_id = auth_client.post("/scans", json={"model_id": model_id}).json()["id"]
    anon = TestClient(auth_client.app)
    assert anon.get(f"/scans/{scan_id}/report", params={"token": auth_client.headers["Authorization"].split()[1]}).status_code == 401
