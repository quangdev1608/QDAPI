from __future__ import annotations

from contextlib import contextmanager
from typing import Generator, Protocol

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from core.config import settings


class Base(DeclarativeBase):
    pass


class ProjectBase(DeclarativeBase):
    pass


class SessionProvider(Protocol):
    @property
    def engine(self) -> Engine: ...

    @property
    def session_local(self) -> sessionmaker[Session]: ...

    def get_db(self) -> Generator[Session, None, None]: ...

    def session_scope(self) -> Generator[Session, None, None]: ...


class SQLAlchemySessionProvider:
    def __init__(self, database_url: str) -> None:
        self._engine = create_engine(
            database_url,
            pool_pre_ping=True,
            pool_recycle=1800,
            pool_size=10,
            max_overflow=20,
            pool_timeout=30,
        )
        self._session_local = sessionmaker(
            bind=self._engine,
            autocommit=False,
            autoflush=False,
            expire_on_commit=False,
            class_=Session,
        )

    @property
    def engine(self) -> Engine:
        return self._engine

    @property
    def session_local(self) -> sessionmaker[Session]:
        return self._session_local

    def get_db(self) -> Generator[Session, None, None]:
        db = self._session_local()
        try:
            yield db
        finally:
            db.close()

    @contextmanager
    def session_scope(self) -> Generator[Session, None, None]:
        with self._session_local() as session:
            yield session


# API Database - for admin, api keys, logs
api_db_provider: SessionProvider = SQLAlchemySessionProvider(settings.database_api_url)
api_engine = api_db_provider.engine
api_SessionLocal = api_db_provider.session_local


# Project Database - for project data
project_db_provider: SessionProvider = SQLAlchemySessionProvider(settings.database_project_url)
project_engine = project_db_provider.engine
project_SessionLocal = project_db_provider.session_local


# Legacy compatibility (points to API DB)
session_provider = api_db_provider
engine = api_engine
SessionLocal = api_SessionLocal


def get_db() -> Generator[Session, None, None]:
    yield from api_db_provider.get_db()


def get_api_db() -> Generator[Session, None, None]:
    yield from api_db_provider.get_db()


def get_project_db() -> Generator[Session, None, None]:
    yield from project_db_provider.get_db()


def _ensure_api_logs_client_ip_column() -> None:
    inspector = inspect(api_engine)
    if "api_logs" not in inspector.get_table_names():
        return

    existing_columns = {column["name"] for column in inspector.get_columns("api_logs")}
    if "client_ip" in existing_columns:
        return

    with api_engine.begin() as connection:
        connection.execute(text("ALTER TABLE api_logs ADD COLUMN client_ip VARCHAR(45) NULL"))
        connection.execute(text("CREATE INDEX ix_api_logs_client_ip ON api_logs (client_ip)"))


def create_tables() -> None:
    from core import models  # noqa: F401

    Base.metadata.create_all(bind=api_engine)
    _ensure_api_logs_client_ip_column()


def create_project_tables() -> None:
    from core import project_models  # noqa: F401

    ProjectBase.metadata.create_all(bind=project_engine)
