from __future__ import annotations

import hashlib
import hmac
import os
import re
from io import BytesIO

from fastapi import APIRouter, File, Form, Header, HTTPException, UploadFile, status
from PIL import Image, UnidentifiedImageError

from app.services.inference import InferenceService
from app.services.model_registry import model_registry

router = APIRouter(prefix="/api/v1/inference", tags=["MedAI model gateway"])
inference_service = InferenceService()
MAX_IMAGE_BYTES = 20 * 1024 * 1024
MAX_IMAGE_PIXELS = 40_000_000
SUPPORTED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp"}


def _authenticate(authorization: str | None) -> None:
    expected = os.getenv("MEDAI_WEB_API_KEY", "")
    if not expected:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Clinical model gateway authentication is not configured",
        )
    scheme, _, supplied = (authorization or "").partition(" ")
    if scheme.lower() != "bearer" or not supplied or not hmac.compare_digest(supplied, expected):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid model gateway credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


@router.post("")
async def run_medai_inference(
    file: UploadFile = File(...),
    model_name: str = Form(..., min_length=1, max_length=160),
    model_version: str = Form(..., min_length=1, max_length=80),
    request_hash: str = Form(..., min_length=64, max_length=64),
    authorization: str | None = Header(default=None),
) -> dict:
    """Compatibility contract consumed by MedAI's private model gateway."""
    _authenticate(authorization)

    if model_name in {".", ".."} or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,159}", model_name):
        raise HTTPException(status_code=400, detail="Invalid model name")

    content_type = (file.content_type or "").lower()
    if content_type not in SUPPORTED_IMAGE_TYPES:
        raise HTTPException(status_code=415, detail="Only JPEG, PNG, and WebP images are supported")

    raw = await file.read(MAX_IMAGE_BYTES + 1)
    if not raw or len(raw) > MAX_IMAGE_BYTES:
        raise HTTPException(status_code=413, detail="Image is empty or exceeds the 20 MiB limit")

    actual_request_hash = hashlib.sha256(raw).hexdigest()
    if not hmac.compare_digest(actual_request_hash, request_hash.lower()):
        raise HTTPException(status_code=400, detail="request_hash does not match uploaded image")

    try:
        with Image.open(BytesIO(raw)) as decoded:
            if decoded.width * decoded.height > MAX_IMAGE_PIXELS:
                raise HTTPException(status_code=413, detail="Image dimensions exceed the 40 megapixel limit")
            image = decoded.convert("RGB")
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        raise HTTPException(status_code=400, detail="Uploaded file is not a valid supported image") from exc

    try:
        metadata = model_registry.get_model(model_name)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Requested model is not registered") from exc

    if not metadata.get("is_active"):
        raise HTTPException(status_code=409, detail="Requested model is not active")
    if not metadata.get("file_path"):
        raise HTTPException(status_code=503, detail="Active model artifact is unavailable")

    # The version is an immutable artifact fingerprint, not a caller-supplied label.
    try:
        digest = hashlib.sha256()
        with open(metadata["file_path"], "rb") as artifact:
            for chunk in iter(lambda: artifact.read(1024 * 1024), b""):
                digest.update(chunk)
    except OSError as exc:
        raise HTTPException(status_code=503, detail="Active model artifact cannot be read") from exc

    actual_version = f"sha256:{digest.hexdigest()}"
    if not hmac.compare_digest(actual_version, model_version):
        raise HTTPException(status_code=409, detail="Requested model version does not match active artifact")

    image_type = metadata.get("image_type")
    if image_type not in {"xray", "skin"}:
        raise HTTPException(status_code=409, detail="Registered model has an unsupported image type")

    try:
        prediction = inference_service.predict(image, image_type, model_name=model_name)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail="Active model artifact is unavailable") from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail="Model inference failed") from exc

    if prediction.get("model_name") != model_name:
        raise HTTPException(status_code=502, detail="Inference model identity does not match requested model")

    # Detect an artifact replacement between fingerprint verification and model loading.
    try:
        final_digest = hashlib.sha256()
        with open(metadata["file_path"], "rb") as artifact:
            for chunk in iter(lambda: artifact.read(1024 * 1024), b""):
                final_digest.update(chunk)
    except OSError as exc:
        raise HTTPException(status_code=503, detail="Active model artifact cannot be read") from exc
    if not hmac.compare_digest(actual_version, f"sha256:{final_digest.hexdigest()}"):
        raise HTTPException(status_code=409, detail="Model artifact changed during inference")

    # Analyzer models are currently research-only. Never mark their output as clinically complete.
    return {
        "status": "NEEDS_REVIEW",
        "model": {"name": model_name, "version": actual_version},
        "findings": [{
            "label": str(prediction["label"]),
            "confidence": float(prediction["confidence"]),
        }],
        "limitations": [
            "Research-only output: this model has not been clinically validated.",
            "This output is not a diagnosis and must not guide treatment.",
            "A qualified clinician must independently review the source image and all findings.",
        ],
        "research_status": prediction.get("research_status", "research_only_not_clinically_validated"),
        "request_hash": actual_request_hash,
    }
