from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import uuid4

import jwt
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.orm import Session

from core.config import settings
from core.database import api_SessionLocal
from core.models import RevokedToken
from core.project_models import User

pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    now = datetime.now(timezone.utc)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=30)

    to_encode.update(
        {
            "iss": settings.jwt_issuer,
            "aud": settings.jwt_audience,
            "iat": now,
            "nbf": now,
            "jti": uuid4().hex,
            "exp": expire,
        }
    )
    encoded_jwt = jwt.encode(
        to_encode,
        settings.JWT_SIGNING_SECRET,
        algorithm=settings.jwt_algorithm,
    )
    return encoded_jwt


def verify_token(token: str) -> Optional[dict]:
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SIGNING_SECRET,
            algorithms=[settings.jwt_algorithm],
            issuer=settings.jwt_issuer,
            audience=settings.jwt_audience,
        )
    except jwt.PyJWTError:
        return None

    jti = payload.get("jti")
    if jti and is_token_revoked(jti):
        return None

    return payload


def is_token_revoked(jti: str) -> bool:
    if not jti:
        return False
    with api_SessionLocal() as db:
        row = db.scalar(select(RevokedToken).where(RevokedToken.jti == jti))
        return row is not None


def revoke_token(token: str) -> bool:
    payload = verify_token(token)
    if not payload:
        return False

    jti = payload.get("jti")
    exp = payload.get("exp")
    if not jti or exp is None:
        return False

    with api_SessionLocal() as db:
        if db.scalar(select(RevokedToken).where(RevokedToken.jti == jti)):
            return True

        expires_at = datetime.utcfromtimestamp(float(exp))
        db.add(RevokedToken(jti=jti, expires_at=expires_at))
        db.commit()
    return True


def create_user(db: Session, username: str, email: str, password: str, full_name: Optional[str] = None) -> User:
    existing_user = db.scalar(select(User).where(User.username == username))
    if existing_user:
        raise ValueError("Username already exists")
    
    existing_email = db.scalar(select(User).where(User.email == email))
    if existing_email:
        raise ValueError("Email already exists")
    
    user = User(
        username=username,
        email=email,
        password_hash=hash_password(password),
        full_name=full_name,
        is_active=True
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def authenticate_user(db: Session, username: str, password: str) -> Optional[User]:
    user = db.scalar(select(User).where(User.username == username))
    if not user or not user.is_active:
        return None
    if not verify_password(password, user.password_hash):
        return None
    return user


def get_user_by_id(db: Session, user_id: int) -> Optional[User]:
    return db.get(User, user_id)


def get_user_by_username(db: Session, username: str) -> Optional[User]:
    return db.scalar(select(User).where(User.username == username))
