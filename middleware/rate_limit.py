from __future__ import annotations

import time

from redis import Redis
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from core.config import settings
from core.security import get_api_key_from_request, get_api_key_profile


class RedisRateLimiter:
    def __init__(self, redis_url: str) -> None:
        self.redis = Redis.from_url(redis_url, decode_responses=True)
        self.window_seconds = 60

    def allow(self, key_identifier: str, requests_per_minute: int) -> bool:
        window = int(time.time() // self.window_seconds)
        redis_key = f"rate_limit:{key_identifier}:{window}"

        with self.redis.pipeline() as pipeline:
            pipeline.incr(redis_key)
            pipeline.expire(redis_key, self.window_seconds)
            current_count, _ = pipeline.execute()

        return int(current_count) <= requests_per_minute


def rate_limit_error_response() -> JSONResponse:
    return JSONResponse(
        status_code=429,
        content={
            "status": "error",
            "error_code": "RATE_LIMIT_EXCEEDED",
            "message": "Rate limit exceeded",
        },
    )


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, requests_per_minute: int = 100) -> None:
        super().__init__(app)
        self.default_requests_per_minute = requests_per_minute
        self.limiter = RedisRateLimiter(redis_url=settings.REDIS_URL)

    async def dispatch(self, request: Request, call_next) -> Response:
        if not request.url.path.startswith("/api/v1"):
            return await call_next(request)

        # Skip rate limiting for health and auth endpoints
        if request.url.path in ["/api/v1/health", "/api/v1/auth/login", "/api/v1/auth/register"]:
            return await call_next(request)

        profile = getattr(request.state, "api_key_profile", None)
        if profile is None:
            api_key = getattr(request.state, "api_key", None) or get_api_key_from_request(request)
            profile = get_api_key_profile(api_key)

        client_host = request.client.host if request.client else "unknown"

        if profile and profile.is_active:
            per_key_limit = max(1, int(profile.rate_limit_per_minute or self.default_requests_per_minute))
            key_identifier = f"key:{profile.hashed_key}"
            if not self.limiter.allow(key_identifier, per_key_limit):
                return rate_limit_error_response()
            return await call_next(request)

        ip_identifier = f"ip:{client_host}"
        if not self.limiter.allow(ip_identifier, self.default_requests_per_minute):
            return rate_limit_error_response()

        return await call_next(request)
