from fastapi import APIRouter, Header, HTTPException

from app.config import settings
from app.schemas.model_gateway_keys import (
    ModelGatewayKeyCreateRequest,
    ModelGatewayKeyCreateResponse,
    ModelGatewayKeyInfo,
)
from app.services.model_gateway_keys import (
    authenticate_model_gateway_key,
    create_model_gateway_key,
    list_model_gateway_keys,
    revoke_model_gateway_key,
)

router = APIRouter(prefix="/api/v1/model-gateway/keys", tags=["model-gateway"])


def require_admin(x_admin_key: str | None) -> None:
    if not settings.api_key_admin_secret:
        raise HTTPException(status_code=503, detail="Key administration is not configured")
    if not x_admin_key or x_admin_key != settings.api_key_admin_secret:
        raise HTTPException(status_code=401, detail="Invalid administrator key")


@router.post("", response_model=ModelGatewayKeyCreateResponse)
async def issue_key(
    request: ModelGatewayKeyCreateRequest,
    x_admin_key: str | None = Header(default=None),
) -> dict:
    require_admin(x_admin_key)
    raw, metadata = create_model_gateway_key(request.name, request.owner)
    return {
        "model_gateway_api_key": raw,
        "key_prefix": metadata["key_prefix"],
        "name": metadata["name"],
        "owner": metadata["owner"],
        "warning": "Save this MODEL_GATEWAY_API_KEY now. It will not be shown again.",
    }


@router.get("", response_model=list[ModelGatewayKeyInfo])
async def get_keys(x_admin_key: str | None = Header(default=None)) -> list[dict]:
    require_admin(x_admin_key)
    return list_model_gateway_keys()


@router.delete("/{key_id}")
async def revoke(key_id: int, x_admin_key: str | None = Header(default=None)) -> dict:
    require_admin(x_admin_key)
    if not revoke_model_gateway_key(key_id):
        raise HTTPException(status_code=404, detail="Active model gateway key not found")
    return {"status": "ok", "message": "MODEL_GATEWAY_API_KEY revoked"}


@router.get("/verify")
async def verify_key(x_model_gateway_api_key: str | None = Header(default=None)) -> dict:
    if not authenticate_model_gateway_key(x_model_gateway_api_key):
        raise HTTPException(status_code=401, detail="Invalid or revoked MODEL_GATEWAY_API_KEY")
    return {"status": "ok", "authenticated": True}
