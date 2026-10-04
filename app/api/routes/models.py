from pathlib import Path

from fastapi import APIRouter, File, Header, HTTPException, UploadFile

from app.config import settings
from app.schemas.models import ModelActivateRequest, ModelInfo, ModelListResponse
from app.services.model_registry import ensure_model_exists, model_registry\n\n\ndef require_model_admin(x_admin_key: str | None) -> None:\n    if not settings.api_key_admin_secret or x_admin_key != settings.api_key_admin_secret:\n        raise HTTPException(status_code=401, detail="Administrator secret is required")

router = APIRouter(prefix="/api/v1/models", tags=["models"])


@router.post("/upload")
async def upload_model(file: UploadFile = File(...), model_name: str = None, image_type: str = None, labels: str = None, description: str = None, accuracy: float = None, x_admin_key: str | None = Header(default=None)) -> dict:\n    require_model_admin(x_admin_key)
    if not model_name or not image_type or not labels:
        raise HTTPException(status_code=400, detail="model_name, image_type, and labels are required")
    if image_type not in {"xray", "skin"}:
        raise HTTPException(status_code=400, detail="image_type must be 'xray' or 'skin'")
    if file.content_type not in {"application/octet-stream", "application/x-pytorch"} and not (file.filename or "").endswith(".pth"):
        raise HTTPException(status_code=400, detail="File must be a .pth PyTorch model file")
    try:
        import json
        labels_list = json.loads(labels)
        if not isinstance(labels_list, list):
            raise ValueError("labels must be a JSON list")
        temp_dir = Path("data/uploads/temp_models")
        temp_dir.mkdir(parents=True, exist_ok=True)
        temp_file = temp_dir / (file.filename or f"{model_name}.pth")
        temp_file.write_bytes(await file.read())
        metadata = model_registry.upload_model(str(temp_file), model_name, image_type, labels_list, description, accuracy)
        temp_file.unlink(missing_ok=True)
        return {"status": "ok", "model_name": metadata["model_name"], "image_type": metadata["image_type"], "file_size": metadata["file_size"], "created_at": metadata["created_at"]}
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/list", response_model=ModelListResponse)
async def list_models(image_type: str = None) -> dict:
    models = model_registry.list_models(image_type=image_type)
    return {"models": models, "total": len(models)}


@router.get("/readiness/{image_type}")
async def model_readiness(image_type: str) -> dict:
    if image_type not in {"xray", "skin"}:
        raise HTTPException(status_code=400, detail="image_type must be 'xray' or 'skin'")
    active = model_registry.get_active_model(image_type)
    model_path = active["file_path"] if active else settings.model_path_for(image_type)
    try:
        resolved = ensure_model_exists(model_path, image_type)
        return {
            "status": "ready",
            "image_type": image_type,
            "model_name": active["model_name"] if active else f"{image_type}-configured",
            "file_size": Path(resolved).stat().st_size,
            "research_status": "research_only_not_clinically_validated",
        }
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"No usable trained {image_type} model is available: {exc}") from exc


@router.get("/{model_name}", response_model=ModelInfo)
async def get_model(model_name: str) -> dict:
    try:
        return model_registry.get_model(model_name)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/activate")
async def activate_model(request: ModelActivateRequest, x_admin_key: str | None = Header(default=None)) -> dict:\n    require_model_admin(x_admin_key)
    try:
        metadata = model_registry.activate_model(request.model_name)
        return {"status": "ok", "message": f"Model {request.model_name} activated", "model": metadata}
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.delete("/{model_name}")
async def delete_model(model_name: str, x_admin_key: str | None = Header(default=None)) -> dict:\n    require_model_admin(x_admin_key)
    try:
        model_registry.delete_model(model_name)
        return {"status": "ok", "message": f"Model {model_name} deleted"}
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/active/{image_type}")
async def get_active_model(image_type: str) -> dict:
    if image_type not in {"xray", "skin"}:
        raise HTTPException(status_code=400, detail="image_type must be 'xray' or 'skin'")
    model = model_registry.get_active_model(image_type)
    if not model:
        raise HTTPException(status_code=404, detail=f"No active model for {image_type}")
    return model
