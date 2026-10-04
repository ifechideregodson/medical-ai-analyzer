from fastapi import APIRouter, Header, HTTPException

from app.config import settings
from app.schemas.api_keys import APIKeyCreateRequest, APIKeyCreateResponse, APIKeyInfo
from app.services.api_keys import authenticate_api_key, create_api_key, list_api_keys, revoke_api_key

router = APIRouter(prefix="/api/v1/api-keys", tags=["api-keys"])


def require_admin(x_admin_key: str | None) -> None:
    if not settings.api_key_admin_secret:
        raise HTTPException(status_code=503, detail="API key administration is not configured")
    if not x_admin_key or x_admin_key != settings.api_key_admin_secret:
        raise HTTPException(status_code=401, detail="Invalid administrator key")


@router.post("", response_model=APIKeyCreateResponse)
async def issue_api_key(request: APIKeyCreateRequest, x_admin_key: str | None = Header(default=None)) -> dict:
    require_admin(x_admin_key)
    raw, metadata = create_api_key(request.name, request.owner)
    return {
        "api_key": raw,
        "key_prefix": metadata["key_prefix"],
        "name": metadata["name"],
        "owner": metadata["owner"],
        "warning": "Save this API key now. It will not be shown again.",
    }


@router.get("", response_model=list[APIKeyInfo])
async def get_api_keys(x_admin_key: str | None = Header(default=None)) -> list[dict]:
    require_admin(x_admin_key)
    return list_api_keys()


@router.delete("/{key_id}")
async def revoke(key_id: int, x_admin_key: str | None = Header(default=None)) -> dict:
    require_admin(x_admin_key)
    if not revoke_api_key(key_id):
        raise HTTPException(status_code=404, detail="Active API key not found")
    return {"status": "ok", "message": "API key revoked"}


@router.get("/verify")
async def verify_api_key(x_api_key: str | None = Header(default=None)) -> dict:
    if not authenticate_api_key(x_api_key):
        raise HTTPException(status_code=401, detail="Invalid or revoked API key")
    return {"status": "ok", "authenticated": True}
