"""Single-worker admission limits for a small public capstone deployment."""
import time
from collections import OrderedDict, deque

from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware


class RequestLimits(BaseHTTPMiddleware):
    def __init__(self, app):
        super().__init__(app)
        self.windows = OrderedDict()

    async def dispatch(self, request, call_next):
        from app.core.config import settings
        # Reject before multipart parsing when Content-Length is available.
        length = request.headers.get("content-length")
        if length and (not length.isdigit() or int(length) > settings.max_model_size_bytes + 65536):
            return JSONResponse({"detail": "Request body exceeds upload limit"}, status_code=413)
        if settings.ENVIRONMENT == "prod" and request.method == "POST":
            now = time.monotonic()
            key = (request.client.host if request.client else "unknown", request.url.path)
            window = self.windows.setdefault(key, deque())
            self.windows.move_to_end(key)
            while window and window[0] < now - 60:
                window.popleft()
            if len(window) >= 20:
                return JSONResponse({"detail": "Too many requests; retry in one minute"}, status_code=429, headers={"Retry-After": "60"})
            window.append(now)
            while len(self.windows) > 10000:
                self.windows.popitem(last=False)
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Cache-Control"] = "no-store"
        return response
