from __future__ import annotations

from datetime import datetime, timezone, timedelta

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from core.database import ProjectBase


def get_time():
    """Lấy thời gian theo timezone Việt Nam (UTC+7)"""
    return datetime.now(timezone.utc).astimezone(timezone(timedelta(hours=7)))


# Add your project-specific models here
# These will be stored in DATABASE_PROJECT (project_quangdev)


class ProjectData(ProjectBase):
    """Example project data model - customize as needed"""
    __tablename__ = "project_data"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=get_time)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=get_time, onupdate=get_time)


class User(ProjectBase):
    """Application user model for login"""
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    username: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    full_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=get_time)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=get_time, onupdate=get_time)
