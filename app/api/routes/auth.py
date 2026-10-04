from fastapi import APIRouter, Header
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.schemas.auth import AddMemberRequest, AuthResponse, ChangeRoleRequest, LoginRequest, RegisterRequest
from app.services.auth import (
    add_member, authenticate_token, change_member_role, current_identity,
    list_members, login, register_owner,
)

router = APIRouter(prefix="/api/v1/auth", tags=["authentication"])
bearer = HTTPBearer(auto_error=False)


def get_auth(credentials: HTTPAuthorizationCredentials | None) -> dict:
    return authenticate_token(credentials.credentials if credentials else None)


@router.post("/register", response_model=AuthResponse)
def register(payload: RegisterRequest) -> dict:
    token, user = register_owner(payload.organization_name, payload.email, payload.full_name, payload.password)
    return {"access_token": token, "token_type": "bearer", "user": user}


@router.post("/login", response_model=AuthResponse)
def login_route(payload: LoginRequest) -> dict:
    token, user = login(payload.email, payload.password)
    return {"access_token": token, "token_type": "bearer", "user": user}


@router.get("/me")
def me(credentials: HTTPAuthorizationCredentials | None = __import__("fastapi").Depends(bearer)) -> dict:
    return current_identity(get_auth(credentials))


@router.get("/members")
def members(credentials: HTTPAuthorizationCredentials | None = __import__("fastapi").Depends(bearer)) -> list[dict]:
    return list_members(get_auth(credentials))


@router.post("/members")
def create_member(payload: AddMemberRequest, credentials: HTTPAuthorizationCredentials | None = __import__("fastapi").Depends(bearer)) -> dict:
    return add_member(get_auth(credentials), payload.email, payload.full_name, payload.password, payload.role)


@router.patch("/members/{membership_id}")
def update_member_role(membership_id: int, payload: ChangeRoleRequest, credentials: HTTPAuthorizationCredentials | None = __import__("fastapi").Depends(bearer)) -> dict:
    return change_member_role(get_auth(credentials), membership_id, payload.role)
