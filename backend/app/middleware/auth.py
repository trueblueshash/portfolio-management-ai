from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from app.core.config import settings

# Loaded from env APP_API_KEY via pydantic-settings (default: lightspeed2026)
API_KEY = settings.APP_API_KEY


class APIKeyMiddleware(BaseHTTPMiddleware):
    EXCLUDED_PATHS = ["/", "/health", "/docs", "/openapi.json", "/redoc"]

    async def dispatch(self, request: Request, call_next):
        if request.url.path in self.EXCLUDED_PATHS:
            return await call_next(request)

        if request.method == "OPTIONS":
            return await call_next(request)

        api_key = request.headers.get("X-API-Key") or request.query_params.get("api_key")
        if api_key != API_KEY:
            return JSONResponse(status_code=401, content={"detail": "Invalid API key"})

        return await call_next(request)
