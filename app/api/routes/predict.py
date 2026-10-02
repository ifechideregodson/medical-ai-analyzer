from io import BytesIO

from fastapi import APIRouter, File, HTTPException, UploadFile
from PIL import Image

from app.services.inference import InferenceService

router = APIRouter(prefix="/api/v1/predict", tags=["prediction"])
inference_service = InferenceService()


@router.post("")
async def predict(image_type: str, file: UploadFile = File(...)) -> dict:
    if image_type not in {"xray", "skin"}:
        raise HTTPException(status_code=400, detail="image_type must be 'xray' or 'skin'")
    if not file.filename:
        raise HTTPException(status_code=400, detail="A filename is required")
    if not (file.content_type or "").startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image")

    try:
        image = Image.open(BytesIO(await file.read())).convert("RGB")
        result = inference_service.predict(image, image_type)
        return {
            "status": "ok",
            "image_type": image_type,
            "result": result,
        }
    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail="No trained model is available for this image type") from exc
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Unable to analyze image: {exc}") from exc
