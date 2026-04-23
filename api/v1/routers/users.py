from fastapi import APIRouter

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/ping")
def users_ping() -> dict[str, str]:
    return {"module": "users", "status": "ok"}
