from __future__ import annotations

from datetime import datetime, timedelta, timezone
import re
import secrets

from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, UniqueConstraint
from fastapi import HTTPException, status

from app.config import settings
from app.services.api_keys import Base, SessionLocal, engine

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
ALLOWED_ROLES = {"owner", "admin", "doctor", "radiologist", "dermatologist", "researcher", "nurse", "staff", "patient"}


class Organization(Base):
    __tablename__ = "organizations"
    id = Column(Integer, primary_key=True)
    name = Column(String(180), nullable=False)
    slug = Column(String(180), nullable=False, unique=True, index=True)
    created_at = Column(DateTime(timezone=True), nullable=False)
    is_active = Column(Boolean, nullable=False, default=True)


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    email = Column(String(255), nullable=False, unique=True, index=True)
    full_name = Column(String(255), nullable=False)
    password_hash = Column(String(255), nullable=False)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), nullable=False)


class Membership(Base):
    __tablename__ = "organization_memberships"
    id = Column(Integer, primary_key=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    role = Column(String(40), nullable=False, default="staff")
    created_at = Column(DateTime(timezone=True), nullable=False)
    __table_args__ = (UniqueConstraint("organization_id", "user_id", name="uq_org_user"),)


def now() -> datetime:
    return datetime.now(timezone.utc)


def init_auth_store() -> None:
    Base.metadata.create_all(bind=engine)


def slugify(value: str) -> str:
    value = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return value[:160] or "organization"


def unique_slug(db, name: str) -> str:
    base = slugify(name)
    slug = base
    counter = 2
    while db.query(Organization).filter(Organization.slug == slug).first():
        slug = f"{base}-{counter}"
        counter += 1
    return slug


def public_user(user: User, membership: Membership, organization: Organization) -> dict:
    return {
        "id": user.id,
        "email": user.email,
        "full_name": user.full_name,
        "role": membership.role,
        "organization": {"id": organization.id, "name": organization.name, "slug": organization.slug},
    }


def create_access_token(user_id: int, organization_id: int, role: str) -> str:
    expires = now() + timedelta(minutes=60)
    payload = {"sub": str(user_id), "org_id": organization_id, "role": role, "exp": expires}
    return jwt.encode(payload, settings.secret_key, algorithm="HS256")


def authenticate_token(token: str | None) -> dict:
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=["HS256"])
        user_id = int(payload["sub"])
        org_id = int(payload["org_id"])
        role = str(payload["role"])
    except (JWTError, KeyError, ValueError, TypeError) as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired access token") from exc
    if role not in ALLOWED_ROLES:
        raise HTTPException(status_code=401, detail="Invalid role")
    return {"user_id": user_id, "organization_id": org_id, "role": role}


def require_roles(auth: dict, *roles: str) -> dict:
    if auth["role"] not in roles:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    return auth


def register_owner(organization_name: str, email: str, full_name: str, password: str) -> tuple[str, dict]:
    init_auth_store()
    email = email.strip().lower()
    if len(password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters")
    if not organization_name.strip() or not full_name.strip():
        raise HTTPException(status_code=400, detail="Organization name and full name are required")
    with SessionLocal() as db:
        if db.query(User).filter(User.email == email).first():
            raise HTTPException(status_code=409, detail="An account with this email already exists")
        org = Organization(name=organization_name.strip(), slug=unique_slug(db, organization_name), created_at=now(), is_active=True)
        user = User(email=email, full_name=full_name.strip(), password_hash=pwd_context.hash(password), created_at=now(), is_active=True)
        db.add_all([org, user])
        db.flush()
        membership = Membership(organization_id=org.id, user_id=user.id, role="owner", created_at=now())
        db.add(membership)
        db.commit()
        db.refresh(org); db.refresh(user); db.refresh(membership)
        token = create_access_token(user.id, org.id, membership.role)
        return token, public_user(user, membership, org)


def login(email: str, password: str) -> tuple[str, dict]:
    init_auth_store()
    with SessionLocal() as db:
        user = db.query(User).filter(User.email == email.strip().lower(), User.is_active.is_(True)).first()
        if not user or not pwd_context.verify(password, user.password_hash):
            raise HTTPException(status_code=401, detail="Invalid email or password")
        membership = db.query(Membership).filter(Membership.user_id == user.id).order_by(Membership.id.asc()).first()
        if not membership:
            raise HTTPException(status_code=403, detail="Your account is not assigned to an organization")
        org = db.get(Organization, membership.organization_id)
        if not org or not org.is_active:
            raise HTTPException(status_code=403, detail="Your organization is inactive")
        token = create_access_token(user.id, org.id, membership.role)
        return token, public_user(user, membership, org)


def current_identity(auth: dict) -> dict:
    init_auth_store()
    with SessionLocal() as db:
        user = db.get(User, auth["user_id"])
        org = db.get(Organization, auth["organization_id"])
        membership = db.query(Membership).filter(
            Membership.user_id == auth["user_id"],
            Membership.organization_id == auth["organization_id"],
        ).first()
        if not user or not org or not membership or not user.is_active or not org.is_active:
            raise HTTPException(status_code=401, detail="Account or organization is no longer active")
        return public_user(user, membership, org)


def list_members(auth: dict) -> list[dict]:
    require_roles(auth, "owner", "admin")
    with SessionLocal() as db:
        rows = db.query(Membership, User).join(User, User.id == Membership.user_id).filter(
            Membership.organization_id == auth["organization_id"]
        ).order_by(Membership.id.asc()).all()
        return [{
            "membership_id": m.id, "user_id": u.id, "email": u.email,
            "full_name": u.full_name, "role": m.role, "is_active": u.is_active,
            "created_at": m.created_at.isoformat(),
        } for m, u in rows]


def add_member(auth: dict, email: str, full_name: str, password: str, role: str) -> dict:
    require_roles(auth, "owner", "admin")
    if role not in ALLOWED_ROLES or role == "owner":
        raise HTTPException(status_code=400, detail="Invalid member role")
    if len(password) < 8:
        raise HTTPException(status_code=400, detail="Temporary password must be at least 8 characters")
    email = email.strip().lower()
    with SessionLocal() as db:
        user = db.query(User).filter(User.email == email).first()
        if not user:
            user = User(email=email, full_name=full_name.strip(), password_hash=pwd_context.hash(password), created_at=now(), is_active=True)
            db.add(user); db.flush()
        elif db.query(Membership).filter(Membership.user_id == user.id, Membership.organization_id == auth["organization_id"]).first():
            raise HTTPException(status_code=409, detail="User is already a member of this organization")
        membership = Membership(organization_id=auth["organization_id"], user_id=user.id, role=role, created_at=now())
        db.add(membership); db.commit(); db.refresh(membership); db.refresh(user)
        return {"membership_id": membership.id, "user_id": user.id, "email": user.email, "full_name": user.full_name, "role": role, "temporary_password": password}


def change_member_role(auth: dict, membership_id: int, role: str) -> dict:
    require_roles(auth, "owner", "admin")
    if role not in ALLOWED_ROLES or role == "owner":
        raise HTTPException(status_code=400, detail="Invalid member role")
    with SessionLocal() as db:
        membership = db.get(Membership, membership_id)
        if not membership or membership.organization_id != auth["organization_id"]:
            raise HTTPException(status_code=404, detail="Membership not found")
        if membership.role == "owner":
            raise HTTPException(status_code=403, detail="Owner role cannot be changed here")
        membership.role = role
        db.commit()
        return {"membership_id": membership.id, "role": membership.role}


def generate_invite_code() -> str:
    return secrets.token_urlsafe(18)
