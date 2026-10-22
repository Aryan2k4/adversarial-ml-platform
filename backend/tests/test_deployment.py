from pathlib import Path
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.config import settings
from app.core.limits import RequestLimits


def test_production_refuses_default_secret(monkeypatch):
    from app.main import app
    monkeypatch.setattr(settings, "ENVIRONMENT", "prod")
    monkeypatch.setattr(settings, "JWT_SECRET", "dev-only-secret-do-not-ship")
    with pytest.raises(RuntimeError, match="JWT_SECRET"):
        with TestClient(app):
            pass


def test_rate_limit(monkeypatch):
    monkeypatch.setattr(settings, "ENVIRONMENT", "prod")
    mini = FastAPI()
    mini.add_middleware(RequestLimits)
    @mini.post("/auth/login")
    def login():
        return {"ok": True}
    with TestClient(mini) as client:
        for _ in range(20):
            assert client.post("/auth/login").status_code == 200
        result = client.post("/auth/login")
        assert result.status_code == 429
        assert result.headers["Retry-After"] == "60"


def test_single_origin_frontend_and_api(monkeypatch, tmp_path):
    from app import deployment
    (tmp_path / "index.html").write_text("<!doctype html><div id='root'>test frontend</div>")
    monkeypatch.setattr(deployment, "ROOT", tmp_path)
    with TestClient(deployment.app) as client:
        assert "test frontend" in client.get("/").text
        assert "test frontend" in client.get("/scans/any-deep-link").text
        assert client.get("/api/health").json()["database"] == "up"
        assert client.get("/api/missing-endpoint").status_code == 404


def test_restart_marks_unfinished_scan_failed(auth_client):
    from app.db.session import SessionLocal
    from app.db.base import MLModel, Scan, User
    from app.main import app
    from sqlalchemy import select
    with SessionLocal() as db:
        user = db.scalar(select(User))
        model = MLModel(user_id=user.id, name="restart fixture", model_type="linear_json", file_path="unused")
        db.add(model); db.flush()
        scan = Scan(model_id=model.id, status="running", threat_model="white_box", attack_config={})
        db.add(scan); db.commit(); scan_id = scan.id
    with TestClient(app):
        pass
    with SessionLocal() as db:
        scan = db.get(Scan, scan_id)
        assert scan.status == "failed"
        assert "restarted" in scan.error
        assert scan.completed_at is not None
