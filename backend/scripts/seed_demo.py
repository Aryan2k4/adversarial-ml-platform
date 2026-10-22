"""Seed a demo account + model + finished scan so the dashboard isn't empty in a demo.

    python -m scripts.seed_demo            # from /backend, with the venv active

Idempotent-ish: re-running adds another scan to the same demo user/model.
"""

import sys
import json
import hashlib
from app.core.config import settings
from app.services.evaluator import demo_bundle
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select  # noqa: E402

from app.core.security import hash_password  # noqa: E402
from app.db.base import MLModel, Scan, User  # noqa: E402
from app.db.session import SessionLocal  # noqa: E402
from app.services.pipeline import run_scan_pipeline  # noqa: E402

DEMO_EMAIL = "demo@example.com"
DEMO_PASSWORD = "demo-password-123"


def main() -> None:
    if settings.ENVIRONMENT == "prod":
        raise RuntimeError("Demo accounts with known passwords are disabled in production")
    db = SessionLocal()
    try:
        user = db.scalar(select(User).where(User.email == DEMO_EMAIL))
        if user is None:
            user = User(email=DEMO_EMAIL, password_hash=hash_password(DEMO_PASSWORD))
            db.add(user)
            db.commit()
            db.refresh(user)

        model = db.scalar(select(MLModel).where(MLModel.user_id == user.id, MLModel.model_type == "linear_json"))
        if model is None:
            artefact = settings.STORAGE_DIR / str(user.id) / "demo-model.json"
            artefact.parent.mkdir(parents=True, exist_ok=True)
            artefact.write_text(json.dumps(demo_bundle()), encoding="utf-8")
            model = MLModel(
                user_id=user.id,
                name="Synthetic linear classifier",
                file_path=str(artefact.resolve()),
                model_type="linear_json",
                version="1",
                checksum_sha256=hashlib.sha256(artefact.read_bytes()).hexdigest(),
                size_bytes=artefact.stat().st_size,
            )
            db.add(model)
            db.commit()
            db.refresh(model)

        scan = Scan(
            model_id=model.id,
            status="queued",
            threat_model="white_box",
            attack_config={
                "attacks": ["fgsm", "pgd", "random_search", "poisoning"],
                "params": {},
            },
        )
        db.add(scan)
        db.commit()
        db.refresh(scan)
        scan_id = scan.id
    finally:
        db.close()

    run_scan_pipeline(scan_id)
    print(f"seeded: login as {DEMO_EMAIL} / {DEMO_PASSWORD} — scan {scan_id}")  # noqa: T201


if __name__ == "__main__":
    main()
