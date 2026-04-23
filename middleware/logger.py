from __future__ import annotations

import logging
import time

from sqlalchemy.exc import SQLAlchemyError
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from core.config import settings
from core.database import api_SessionLocal
from core.models import ApiRequestLog
from core.security import get_api_key_from_request, get_api_key_profile, get_key_fingerprint


def get_client_ip(request: Request) -> str:
    forwarded_for = request.headers.get("x-forwarded-for", "").strip()
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()

    real_ip = request.headers.get("x-real-ip", "").strip()
    if real_ip:
        return real_ip

    return request.client.host if request.client else "unknown"


def configure_logging() -> logging.Logger:
    logger = logging.getLogger("api_gateway")
    logger.setLevel(settings.LOG_LEVEL.upper())

    if logger.handlers:
        return logger

    formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    file_handler = logging.FileHandler(settings.LOG_FILE_PATH, encoding="utf-8")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    return logger


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    def __init__(self, app) -> None:
        super().__init__(app)
        self.logger = configure_logging()

    async def dispatch(self, request: Request, call_next) -> Response:
        started = time.perf_counter()
        status_code = 500

        try:
            response = await call_next(request)
            status_code = response.status_code
            return response
        finally:
            elapsed_ms = (time.perf_counter() - started) * 1000
            client_ip = get_client_ip(request)
            self.logger.info(
                "Method=%s Path=%s StatusCode=%s ProcessingTimeMs=%.2f ClientIP=%s",
                request.method,
                request.url.path,
                status_code,
                elapsed_ms,
                client_ip,
            )
            self._save_request_log(request=request, status_code=status_code, processing_time_ms=elapsed_ms)

    def _save_request_log(self, request: Request, status_code: int, processing_time_ms: float) -> None:
        try:
            fingerprint = getattr(request.state, "api_key_fingerprint", None)
            if fingerprint is None:
                raw_key = get_api_key_from_request(request)
                profile = get_api_key_profile(raw_key)
                if profile:
                    fingerprint = get_key_fingerprint(profile.hashed_key)

            with api_SessionLocal() as session:
                session.add(
                    ApiRequestLog(
                        method=request.method,
                        path=request.url.path,
                        status_code=status_code,
                        processing_time_ms=processing_time_ms,
                        api_key=fingerprint,
                        client_ip=get_client_ip(request),
                    )
                )
                session.commit()
        except SQLAlchemyError:
            self.logger.exception("Failed to persist API request log")
