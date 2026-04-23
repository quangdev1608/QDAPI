from __future__ import annotations

from sqlalchemy import select
from werkzeug.security import generate_password_hash

from core.config import settings
from core.database import api_SessionLocal, create_project_tables, create_tables
from admin.services import assign_role_to_user, ensure_default_roles, get_admin_user_id
from core.models import AdminUser


def bootstrap_admin_user() -> None:
    create_tables()
    create_project_tables()
    ensure_default_roles()

    with api_SessionLocal() as session:
        existing = session.scalar(select(AdminUser).where(AdminUser.username == settings.ADMIN_USERNAME))
        if not existing:
            user = AdminUser(
                username=settings.ADMIN_USERNAME,
                password_hash=generate_password_hash(settings.ADMIN_PASSWORD),
                is_active=True,
            )
            session.add(user)
            session.commit()

    admin_user_id = get_admin_user_id(settings.ADMIN_USERNAME)
    if admin_user_id is not None:
        assign_role_to_user(admin_user_id, "admin")
