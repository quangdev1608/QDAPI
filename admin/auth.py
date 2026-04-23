from __future__ import annotations

from functools import wraps

from flask import Flask, flash, redirect, url_for
from flask_login import LoginManager, UserMixin, current_user
from redis import Redis
from redis.exceptions import RedisError
from sqlalchemy import select
from werkzeug.security import check_password_hash

from admin.services import get_user_permissions
from core.config import settings
from core.database import api_SessionLocal
from core.models import AdminUser

redis_client = Redis.from_url(settings.REDIS_URL, decode_responses=True)
MAX_FAILED_ATTEMPTS = 5
LOCKOUT_SECONDS = 15 * 60
ATTEMPT_WINDOW_SECONDS = 15 * 60

login_manager = LoginManager()
login_manager.login_view = "admin.login_page"


def _attempt_key(username: str, client_ip: str) -> str:
    return f"admin_login_attempts:{username.lower()}:{client_ip}"


def _lockout_key(username: str, client_ip: str) -> str:
    return f"admin_login_lockout:{username.lower()}:{client_ip}"


def check_admin_login_lockout(username: str, client_ip: str) -> int:
    lock_key = _lockout_key(username, client_ip)
    try:
        ttl = redis_client.ttl(lock_key)
    except RedisError:
        return 0
    if ttl and ttl > 0:
        return int(ttl)
    return 0


def record_admin_login_attempt(username: str, client_ip: str, success: bool) -> int:
    attempt_key = _attempt_key(username, client_ip)
    lock_key = _lockout_key(username, client_ip)

    try:
        if success:
            redis_client.delete(attempt_key)
            redis_client.delete(lock_key)
            return 0

        attempts = redis_client.incr(attempt_key)
        if attempts == 1:
            redis_client.expire(attempt_key, ATTEMPT_WINDOW_SECONDS)

        if attempts >= MAX_FAILED_ATTEMPTS:
            redis_client.setex(lock_key, LOCKOUT_SECONDS, "1")
            redis_client.delete(attempt_key)
            return LOCKOUT_SECONDS

        ttl = redis_client.ttl(attempt_key)
        return int(ttl) if ttl and ttl > 0 else ATTEMPT_WINDOW_SECONDS
    except RedisError:
        return 0


def remaining_admin_attempts(username: str, client_ip: str) -> int:
    try:
        attempts = redis_client.get(_attempt_key(username, client_ip))
    except RedisError:
        return MAX_FAILED_ATTEMPTS
    used = int(attempts) if attempts else 0
    return max(0, MAX_FAILED_ATTEMPTS - used)


class AdminLoginUser(UserMixin):
    def __init__(self, admin_user: AdminUser) -> None:
        self.id = str(admin_user.id)
        self.username = admin_user.username
        self._is_active = bool(admin_user.is_active)

    @property
    def is_active(self) -> bool:
        return self._is_active


def init_login_manager(app: Flask) -> None:
    login_manager.init_app(app)


@login_manager.user_loader
def load_user(user_id: str) -> AdminLoginUser | None:
    with api_SessionLocal() as session:
        user = session.get(AdminUser, int(user_id))
        if not user or not user.is_active:
            return None
        return AdminLoginUser(user)


def authenticate_admin(username: str, password: str) -> AdminUser | None:
    with api_SessionLocal() as session:
        user = session.scalar(select(AdminUser).where(AdminUser.username == username))
        if not user or not user.is_active:
            return None
        if not check_password_hash(user.password_hash, password):
            return None
        return user


def require_permission(permission: str):
    def decorator(func):
        @wraps(func)
        def wrapped(*args, **kwargs):
            if not current_user.is_authenticated:
                return redirect(url_for("admin.login_page"))

            permissions = get_user_permissions(int(current_user.id))
            if permission not in permissions:
                flash("Bạn không có quyền truy cập chức năng này", "danger")
                return redirect(url_for("admin.index"))

            return func(*args, **kwargs)

        return wrapped

    return decorator


def require_any_permission(*permissions: str):
    def decorator(func):
        @wraps(func)
        def wrapped(*args, **kwargs):
            if not current_user.is_authenticated:
                return redirect(url_for("admin.login_page"))

            user_permissions = get_user_permissions(int(current_user.id))
            if not any(permission in user_permissions for permission in permissions):
                flash("Bạn không có quyền truy cập chức năng này", "danger")
                return redirect(url_for("admin.index"))

            return func(*args, **kwargs)

        return wrapped

    return decorator


def inject_admin_permission_helpers() -> dict[str, object]:
    def _can(permission: str) -> bool:
        if not current_user.is_authenticated:
            return False
        return permission in get_user_permissions(int(current_user.id))

    return {"is_admin_can": _can}
