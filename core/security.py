from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

from fastapi import Request
from redis import Redis
from sqlalchemy import select

from core.config import settings
from core.database import api_SessionLocal
from core.models import ApiKey

redis_client = Redis.from_url(settings.REDIS_URL, decode_responses=True)


@dataclass(frozen=True)
class ApiKeyProfile:
    id: int
    hashed_key: str
    rate_limit_per_minute: int
    is_active: bool


def hash_api_key(api_key: str) -> str:
    return hashlib.sha256(api_key.encode("utf-8")).hexdigest()


def get_api_key_from_request(request: Request) -> str | None:
    return request.headers.get(settings.API_KEY_HEADER_NAME)


def get_key_fingerprint(hashed_key: str) -> str:
    if len(hashed_key) <= 12:
        return hashed_key
    return f"{hashed_key[:8]}...{hashed_key[-4:]}"


def _cache_key_for_hashed_api_key(hashed_key: str) -> str:
    return f"api_key_profile:{hashed_key}"


def _serialize_profile(profile: ApiKeyProfile) -> str:
    return json.dumps(
        {
            "id": profile.id,
            "hashed_key": profile.hashed_key,
            "rate_limit_per_minute": profile.rate_limit_per_minute,
            "is_active": profile.is_active,
        }
    )


def _deserialize_profile(value: str) -> ApiKeyProfile:
    data = json.loads(value)
    return ApiKeyProfile(
        id=int(data["id"]),
        hashed_key=str(data["hashed_key"]),
        rate_limit_per_minute=int(data["rate_limit_per_minute"]),
        is_active=bool(data["is_active"]),
    )


def get_api_key_profile(api_key: str | None) -> ApiKeyProfile | None:
    if not api_key:
        return None

    hashed_key = hash_api_key(api_key)
    cache_key = _cache_key_for_hashed_api_key(hashed_key)
    
    try:
        cached = redis_client.get(cache_key)
        if cached:
            return _deserialize_profile(cached)
    except Exception:
        # Redis not available, skip cache
        pass

    with api_SessionLocal() as session:
        row = session.execute(
            select(
                ApiKey.id,
                ApiKey.key_value,
                ApiKey.rate_limit_per_minute,
                ApiKey.is_active,
            ).where(ApiKey.key_value == hashed_key)
        ).first()

    if not row:
        return None

    profile = ApiKeyProfile(
        id=int(row.id),
        hashed_key=str(row.key_value),
        rate_limit_per_minute=int(row.rate_limit_per_minute),
        is_active=bool(row.is_active),
    )

    try:
        redis_client.setex(cache_key, settings.API_KEY_CACHE_TTL_SECONDS, _serialize_profile(profile))
    except Exception:
        # Redis not available, skip cache
        pass
    return profile


def is_api_key_valid(api_key: str | None) -> bool:
    profile = get_api_key_profile(api_key)
    return bool(profile and profile.is_active)


def invalidate_api_key_profile_cache(hashed_key: str) -> None:
    if not hashed_key:
        return
    try:
        redis_client.delete(_cache_key_for_hashed_api_key(hashed_key))
    except Exception:
        # Redis not available, ignore cache invalidation
        pass
