from __future__ import annotations

import secrets

from sqlalchemy import extract, func, select
from sqlalchemy.exc import IntegrityError

from core.database import api_SessionLocal
from core.models import ApiKey, ApiRequestLog, AdminRole, AdminRoleBinding, AdminUser
from core.security import hash_api_key, invalidate_api_key_profile_cache

ROLE_PERMISSIONS = {
    "viewer": {"dashboard:view", "logs:view", "data:view", "keys:view"},
    "operator": {"dashboard:view", "logs:view", "data:view", "keys:view", "keys:create", "keys:update", "keys:toggle"},
    "admin": {
        "dashboard:view",
        "logs:view",
        "data:view",
        "keys:view",
        "keys:create",
        "keys:update",
        "keys:toggle",
        "keys:delete",
        "rbac:manage",
    },
}


def serialize_permissions(permissions: set[str]) -> str:
    return ",".join(sorted(permissions))


def deserialize_permissions(raw: str) -> set[str]:
    if not raw:
        return set()
    return {item.strip() for item in raw.split(",") if item.strip()}


def ensure_default_roles() -> None:
    with api_SessionLocal() as db:
        for role_name, permissions in ROLE_PERMISSIONS.items():
            role = db.scalar(select(AdminRole).where(AdminRole.name == role_name))
            serialized = serialize_permissions(permissions)
            if role is None:
                db.add(AdminRole(name=role_name, permissions=serialized))
            else:
                role.permissions = serialized
        db.commit()


def assign_role_to_user(admin_user_id: int, role_name: str) -> None:
    with api_SessionLocal() as db:
        role = db.scalar(select(AdminRole).where(AdminRole.name == role_name))
        if role is None:
            return

        binding = db.scalar(
            select(AdminRoleBinding).where(AdminRoleBinding.admin_user_id == admin_user_id)
        )
        if binding is None:
            db.add(AdminRoleBinding(admin_user_id=admin_user_id, role_id=role.id))
        else:
            binding.role_id = role.id
        db.commit()


def get_user_permissions(admin_user_id: int) -> set[str]:
    with api_SessionLocal() as db:
        role = db.scalar(
            select(AdminRole)
            .join(AdminRoleBinding, AdminRoleBinding.role_id == AdminRole.id)
            .where(AdminRoleBinding.admin_user_id == admin_user_id)
        )
        if role is None:
            return set()
        return deserialize_permissions(role.permissions)


def get_dashboard_data() -> tuple[int, int, list[ApiRequestLog], list[str], list[int]]:
    with api_SessionLocal() as db:
        total_keys = db.scalar(select(func.count(ApiKey.id))) or 0
        total_requests = db.scalar(select(func.count(ApiRequestLog.id))) or 0

        latest_logs = db.scalars(select(ApiRequestLog).order_by(ApiRequestLog.id.desc()).limit(50)).all()

        hourly_rows = db.execute(
            select(
                extract("hour", ApiRequestLog.created_at).label("hour"),
                func.count(ApiRequestLog.id).label("count"),
            )
            .group_by("hour")
            .order_by("hour")
        ).all()

    hourly_counts = {hour: 0 for hour in range(24)}
    for hour_value, count_value in hourly_rows:
        hourly_counts[int(hour_value)] = int(count_value)

    chart_labels = [f"{hour:02d}:00" for hour in range(24)]
    chart_values = [hourly_counts[hour] for hour in range(24)]
    return total_keys, total_requests, latest_logs, chart_labels, chart_values


def list_keys() -> list[ApiKey]:
    with api_SessionLocal() as db:
        return db.scalars(select(ApiKey).order_by(ApiKey.id.desc())).all()


def create_api_key(name: str, note: str | None, rate_limit: int) -> tuple[bool, str | None]:
    raw_key_value = secrets.token_urlsafe(32)
    hashed_key_value = hash_api_key(raw_key_value)

    with api_SessionLocal() as db:
        db.add(
            ApiKey(
                name=name,
                key_value=hashed_key_value,
                note=note,
                rate_limit_per_minute=rate_limit,
                is_active=True,
            )
        )
        try:
            db.commit()
            invalidate_api_key_profile_cache(hashed_key_value)
            return True, raw_key_value
        except IntegrityError:
            db.rollback()
            return False, None


def update_api_key(key_id: int, note: str | None, rate_limit: int) -> bool:
    with api_SessionLocal() as db:
        item = db.get(ApiKey, key_id)
        if not item:
            return False

        item.note = note
        item.rate_limit_per_minute = rate_limit
        db.commit()
        invalidate_api_key_profile_cache(item.key_value)
        return True


def toggle_api_key(key_id: int) -> bool:
    with api_SessionLocal() as db:
        item = db.get(ApiKey, key_id)
        if not item:
            return False
        item.is_active = not item.is_active
        db.commit()
        invalidate_api_key_profile_cache(item.key_value)
        return True


def delete_api_key(key_id: int) -> bool:
    with api_SessionLocal() as db:
        item = db.get(ApiKey, key_id)
        if not item:
            return False
        hashed_key = item.key_value
        db.delete(item)
        db.commit()
        invalidate_api_key_profile_cache(hashed_key)
        return True


def list_logs(page: int, per_page: int = 50) -> list[ApiRequestLog]:
    with api_SessionLocal() as db:
        return db.scalars(
            select(ApiRequestLog)
            .order_by(ApiRequestLog.id.desc())
            .offset((page - 1) * per_page)
            .limit(per_page)
        ).all()


def query_data_manager(search: str, status: str) -> list[ApiKey]:
    stmt = select(ApiKey)

    if search:
        pattern = f"%{search}%"
        stmt = stmt.where(ApiKey.name.ilike(pattern) | ApiKey.note.ilike(pattern))

    if status == "active":
        stmt = stmt.where(ApiKey.is_active.is_(True))
    elif status == "inactive":
        stmt = stmt.where(ApiKey.is_active.is_(False))

    stmt = stmt.order_by(ApiKey.id.desc())

    with api_SessionLocal() as db:
        return db.scalars(stmt).all()


def get_admin_user_id(username: str) -> int | None:
    with api_SessionLocal() as db:
        user = db.scalar(select(AdminUser).where(AdminUser.username == username))
        return user.id if user else None
