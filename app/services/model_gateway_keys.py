from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, Integer, String

from app.services.api_keys import Base, SessionLocal, engine, init_api_key_store
from app.config import settings


class ModelGatewayKey(Base):
    __tablename__ = "model_gateway_keys"

    id = Column(Integer, primary_key=True)
    name = Column(String(120), nullable=False)
    owner = Column(String(255), nullable=False)
    key_prefix = Column(String(32), nullable=False, unique=True)
    key_hash = Column(String(64), nullable=False, unique=True)
    created_at = Column(DateTime(timezone=True), nullable=False)
    last_used_at = Column(DateTime(timezone=True), nullable=True)
    revoked_at = Column(DateTime(timezone=True), nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)


def _hash(raw_key: str) -> str:
    return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()


def _init() -> None:
    init_api_key_store()
    ModelGatewayKey.metadata.create_all(bind=engine)


def _serialize(record: ModelGatewayKey) -> dict:
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


def create_model_gateway_key(name: str, owner: str) -> tuple[str, dict]:
    _init()
    raw = f"{settings.model_gateway_key_prefix}_{secrets.token_urlsafe(32)}"
    record = ModelGatewayKey(
        name=name.strip(),
        owner=owner.strip(),
        key_prefix=raw[:24],
        key_hash=_hash(raw),
        created_at=datetime.now(timezone.utc),
        is_active=True,
    )
    with SessionLocal() as db:
        db.add(record)
        db.commit()
        db.refresh(record)
        return raw, _serialize(record)


def list_model_gateway_keys() -> list[dict]:
    _init()
    with SessionLocal() as db:
        return [_serialize(item) for item in db.query(ModelGatewayKey).order_by(ModelGatewayKey.id.desc()).all()]


def revoke_model_gateway_key(key_id: int) -> bool:
    _init()
    with SessionLocal() as db:
        item = db.get(ModelGatewayKey, key_id)
        if not item or not item.is_active:
            return False
        item.is_active = False
        item.revoked_at = datetime.now(timezone.utc)
        db.commit()
        return True


def authenticate_model_gateway_key(raw_key: str | None) -> bool:
    if not raw_key:
        return False
    _init()
    with SessionLocal() as db:
        item = db.query(ModelGatewayKey).filter(
            ModelGatewayKey.key_hash == _hash(raw_key),
            ModelGatewayKey.is_active.is_(True),
            ModelGatewayKey.revoked_at.is_(None),
        ).first()
        if not item:
            return False
        item.last_used_at = datetime.now(timezone.utc)
        db.commit()
        return True
