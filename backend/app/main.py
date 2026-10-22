"""FastAPI entrypoint. `uvicorn app.main:app --reload` from /backend."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes import auth, health, models, reports, scans
from app.core.config import settings
from app.core.logging import get_logger, setup_logging

setup_logging()
logger = get_logger(__name__)

DESCRIPTION = """
Reproducible adversarial evaluation for data-only linear-softmax classifier bundles.
FGSM, PGD, budgeted decision-only random search, and paired label-flip retraining.
Results include empirical scores, ATLAS mappings, evidence, and authenticated reports.
See docs/EVALUATION.md for supported formats, scoring and limitations.
"""

@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    if settings.ENVIRONMENT == "prod" and (settings.JWT_SECRET == "dev-only-secret-do-not-ship" or len(settings.JWT_SECRET) < 32):
        raise RuntimeError("Production requires a random JWT_SECRET of at least 32 characters")
    settings.STORAGE_DIR.mkdir(parents=True, exist_ok=True)
    # One API worker per deployment. Recover interrupted jobs explicitly on restart.
    from app.db.session import SessionLocal
    from app.db.base import Scan, utcnow
    from sqlalchemy import update
    with SessionLocal() as db:
        db.execute(update(Scan).where(Scan.status.in_(["queued", "running"])).values(
            status="failed", error="Service restarted before evaluation completed; submit a new scan", completed_at=utcnow()))
        db.commit()
    logger.info("api started", extra={"environment": settings.ENVIRONMENT})
    yield


app = FastAPI(
    lifespan=lifespan,
    title="Adversarial ML Red-Teaming Platform API",
    version="0.1.0",
    description=DESCRIPTION,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# Defaults to the Vite dev server; set CORS_ORIGINS in .env for a deployed frontend.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
from app.core.limits import RequestLimits
app.add_middleware(RequestLimits)

app.include_router(health.router)
app.include_router(auth.router)
app.include_router(models.router)
app.include_router(scans.router)
app.include_router(reports.router)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Log the stack trace, return a shaped error — never a raw traceback to the client."""
    logger.exception("unhandled error", extra={"path": request.url.path})
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "internal server error"},
    )
