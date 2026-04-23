from fastapi import APIRouter

from .routers import auth_router, health_router, users_router, users_auth_router

router = APIRouter(prefix="/api/v1")
router.include_router(health_router)
router.include_router(auth_router)
router.include_router(users_router)
router.include_router(users_auth_router)

__all__ = ["router"]
