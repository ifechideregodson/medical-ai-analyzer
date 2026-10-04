from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, Integer, String, create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from app.config import settings

Base = declarative_base()


class APIKey(Base):
    __tablename__ = "api_keys"

    id = Column(Integer, primary_key=True)
    name = Column(String(120), nullable=False)
    owner = Column(String(255), nullable=False)
    key_prefix = Column(String(32), nullable=False, unique=True)
    key_hash = Column(String(64), nullable=False, unique=True)
    created_at = Column(DateTime(timezone=True), nullable=False)
    last_used_at = Column(DateTime(timezone=True), nullable=True)
    revoked_at = Column(DateTime(timezone=True), nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)


def _database_url() -> str:
    return settings.database_url.replace("postgres://", "postgresql://", 1)


engine = create_engine(_database_url(), pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def init_api_key_store() -> None:
    Base.metadata.create_all(bind=engine)


def _hash(raw_key: str) -> str:
    return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()


def create_api_key(name: str, owner: str) -> tuple[str, dict]:
    init_api_key_store()
    raw = f"{settings.api_key_prefix}_{secrets.token_urlsafe(32)}"
    now = datetime.now(timezone.utc)
    record = APIKey(
        name=name.strip(),
        owner=owner.strip(),
        key_prefix=raw[:20],
        key_hash=_hash(raw),
        created_at=now,
        is_active=True,
    )
    with SessionLocal() as db:
        db.add(record)
        db.commit()
        db.refresh(record)
        return raw, serialize(record)


def serialize(record: APIKey) -> dict:
    return {
        "id": record.id,
        "name": record.name,
        "owner": record.owner,
        "key_prefix": record.key_prefix,
        "created_at": record.created_at.isoformat(),
        "last_used_at": record.last_used_at.isoformat() if record.last_used_at else None,
        "revoked_at": record.revoked_at.isoformat() if record.revoked_at else None,
        "is_active": bool(record.is_active),
    }


def list_api_keys() -> list[dict]:
    init_api_key_store()
    with SessionLocal() as db:
        return [serialize(item) for item in db.query(APIKey).order_by(APIKey.id.desc()).all()]


def revoke_api_key(key_id: int) -> bool:
    init_api_key_store()
    with SessionLocal() as db:
        item = db.get(APIKey, key_id)
        if not item or not item.is_active:
            return False
        item.is_active = False
        item.revoked_at = datetime.now(timezone.utc)
        db.commit()
        return True


def authenticate_api_key(raw_key: str | None) -> bool:
    if not raw_key:
        return False
    init_api_key_store()
    with SessionLocal() as db:
        item = db.query(APIKey).filter(
            APIKey.key_hash == _hash(raw_key),
            APIKey.is_active.is_(True),
            APIKey.revoked_at.is_(None),
        ).first()
        if not item:
            return False
        item.last_used_at = datetime.now(timezone.utc)
        db.commit()
        return True


def rate_limit_key(raw_key: str) -> str:
    return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()


def check_rate_limit(raw_key: str, limit: int = 60) -> None:
    """Best-effort per-key minute limiter. API remains available if Redis is temporarily unavailable."""
    try:
        import redis
        client = redis.Redis.from_url(settings.redis_url, decode_responses=True)
        bucket = f"medai:api-rate:{rate_limit_key(raw_key)}"
        count = client.incr(bucket)
        if count == 1:
            client.expire(bucket, 60)
        if count > limit:
            from fastapi import HTTPException
            from fastapi import status
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"API rate limit exceeded. Maximum {limit} requests per minute.",
                headers={"Retry-After": "60"},
            )
    except HTTPException:
        raise
    except Exception:
        return
