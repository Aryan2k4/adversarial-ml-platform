"""Single-origin deployment: /api for FastAPI, everything else for the SPA."""
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.main import app as api, lifespan

ROOT = Path(__file__).resolve().parents[1] / "static"


@asynccontextmanager
async def startup(app):
    async with lifespan(api):
        yield


app = FastAPI(lifespan=startup, docs_url=None, redoc_url=None, openapi_url=None)
app.mount("/api", api)
if (ROOT / "assets").exists():
    app.mount("/assets", StaticFiles(directory=ROOT / "assets"), name="assets")


@app.get("/{path:path}")
def frontend(path: str):
    return FileResponse(ROOT / "index.html", headers={"Cache-Control": "no-cache"})
