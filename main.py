from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.v1 import router as v1_router
from core.config import settings
from middleware import AuthenticationMiddleware, RateLimitMiddleware, RequestLoggingMiddleware

app = FastAPI(title="API Gateway", version="1.0.0")

@app.get("/")
def root():
    return {"status": "ok", "message": "API Gateway is running"}

@app.get("/health")
def health():
    return {"status": "ok"}

if settings.cors_allow_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_allow_origins,
        allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=settings.cors_allow_headers,
    )

app.add_middleware(AuthenticationMiddleware)
app.add_middleware(RateLimitMiddleware)
app.add_middleware(RequestLoggingMiddleware)
app.include_router(v1_router)
