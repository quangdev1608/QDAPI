from __future__ import annotations

from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from core.security import get_api_key_from_request, get_api_key_profile, get_key_fingerprint


def auth_error_response(status_code: int, error_code: str, message: str) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={
            "status": "error",
            "error_code": error_code,
            "message": message,
        },
    )


PUBLIC_PATHS = {
    "/api/v1/health",
    "/api/v1/auth/login",
    "/api/v1/auth/register",
}


class AuthenticationMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        if not request.url.path.startswith("/api/v1"):
            return await call_next(request)

        if request.url.path in PUBLIC_PATHS:
            return await call_next(request)

        api_key = get_api_key_from_request(request)
        profile = get_api_key_profile(api_key)

        if not profile or not profile.is_active:
            return auth_error_response(
                status_code=401,
                error_code="API_KEY_INVALID",
                message="Invalid API key",
            )

        request.state.api_key = api_key
        request.state.api_key_profile = profile
        request.state.api_key_fingerprint = get_key_fingerprint(profile.hashed_key)
        return await call_next(request)
