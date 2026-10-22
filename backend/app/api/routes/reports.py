"""Authenticated report export using Authorization headers, never URL tokens."""

from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status
from fastapi.responses import HTMLResponse, Response

from app.api.deps import DbSession, CurrentUser
from app.core.logging import get_logger
from app.core.security import TokenError, decode_token
from app.db.base import Scan, User
from app.schemas.common import ErrorResponse
from app.services.report import render_html, render_pdf

router = APIRouter(tags=["reports"])
logger = get_logger(__name__)


@router.get(
    "/scans/{scan_id}/report",
    responses={
        200: {"content": {"application/pdf": {}, "text/html": {}}, "description": "the report"},
        401: {"model": ErrorResponse, "description": "missing or invalid token"},
        404: {"model": ErrorResponse, "description": "scan not found"},
        409: {"model": ErrorResponse, "description": "scan is not finished"},
    },
    summary="Download the compliance report for a finished scan",
)
def get_report(
    scan_id: UUID,
    db: DbSession,
    current_user: CurrentUser,
    format: str = Query("pdf", pattern="^(pdf|html)$"),
) -> Response:
    user = current_user
    scan = db.get(Scan, scan_id)
    if user is None or scan is None or scan.model.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="scan not found")
    if scan.status != "done":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"report unavailable; scan status is {scan.status}",
        )

    logger.info("report exported", extra={"scan_id": str(scan_id), "format": format})
    if format == "html":
        return HTMLResponse(render_html(scan))

    filename = f"robustness-report-{scan_id}.pdf"
    return Response(
        content=render_pdf(scan),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
