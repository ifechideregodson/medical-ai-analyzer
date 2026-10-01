import os
from io import BytesIO
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile

from app.schemas.models import ModelUploadRequest, ModelInfo, ModelActivateRequest, ModelListResponse
from app.services.model_registry import model_registry

router = APIRouter(prefix="/api/v1/models", tags=["models"])


@router.post("/upload")
async def upload_model(
    file: UploadFile = File(...),
    model_name: str = None,
    image_type: str = None,
    labels: str = None,
    description: str = None,
    accuracy: float = None,
) -> dict:
    """Upload a trained model file to the model registry."""
    if not model_name or not image_type or not labels:
        raise HTTPException(
            status_code=400,
            detail="model_name, image_type, and labels are required"
        )

    if image_type not in {"xray", "skin"}:
        raise HTTPException(status_code=400, detail="image_type must be 'xray' or 'skin'")

    if file.content_type not in {"application/octet-stream", "application/x-pytorch"}:
        if not file.filename.endswith(".pth"):
            raise HTTPException(status_code=400, detail="File must be a .pth PyTorch model file")

    try:
        # Parse labels
        import json
        labels_list = json.loads(labels) if isinstance(labels, str) else labels
        if not isinstance(labels_list, list):
            raise ValueError("labels must be a JSON list")

        # Save uploaded file temporarily
        temp_dir = Path("data/uploads/temp_models")
        temp_dir.mkdir(parents=True, exist_ok=True)
        temp_file = temp_dir / file.filename

        file_content = await file.read()
        with open(temp_file, "wb") as f:
            f.write(file_content)

        # Register model
        metadata = model_registry.upload_model(
            model_file_path=str(temp_file),
            model_name=model_name,
            image_type=image_type,
            labels=labels_list,
            description=description,
            accuracy=accuracy,
        )

        # Clean up temp file
        temp_file.unlink()

        return {
            "status": "ok",
            "model_name": metadata["model_name"],
            "image_type": metadata["image_type"],
            "file_size": metadata["file_size"],
            "created_at": metadata["created_at"],
            "message": f"Model {model_name} uploaded successfully",
        }
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/list", response_model=ModelListResponse)
async def list_models(image_type: str = None) -> dict:
    """List all registered models."""
    models = model_registry.list_models(image_type=image_type)
    return {
        "models": models,
        "total": len(models),
    }


@router.get("/{model_name}", response_model=ModelInfo)
async def get_model(model_name: str) -> dict:
    """Get information about a specific model."""
    try:
        return model_registry.get_model(model_name)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/activate")
async def activate_model(request: ModelActivateRequest) -> dict:
    """Activate a model for inference."""
    try:
        metadata = model_registry.activate_model(request.model_name)
        return {
            "status": "ok",
            "message": f"Model {request.model_name} activated",
            "model": metadata,
        }
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.delete("/{model_name}")
async def delete_model(model_name: str) -> dict:
    """Delete a model from the registry."""
    try:
        model_registry.delete_model(model_name)
        return {
            "status": "ok",
            "message": f"Model {model_name} deleted",
        }
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/active/{image_type}")
async def get_active_model(image_type: str) -> dict:
    """Get the active model for a specific image type."""
    if image_type not in {"xray", "skin"}:
        raise HTTPException(status_code=400, detail="image_type must be 'xray' or 'skin'")

    model = model_registry.get_active_model(image_type)
    if not model:
        raise HTTPException(status_code=404, detail=f"No active model for {image_type}")

    return model
