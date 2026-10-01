from typing import Optional
from pydantic import BaseModel, Field
from datetime import datetime


class ModelUploadRequest(BaseModel):
    model_name: str = Field(..., description="Name of the model (e.g., 'xray_model_v2')")
    image_type: str = Field(..., description="Type: 'xray' or 'skin'")
    labels: list[str] = Field(..., description="List of class labels")
    description: Optional[str] = Field(None, description="Model description")
    accuracy: Optional[float] = Field(None, ge=0, le=100, description="Model accuracy percentage")


class ModelInfo(BaseModel):
    model_name: str
    image_type: str
    labels: list[str]
    file_path: str
    file_size: int
    created_at: str
    description: Optional[str] = None
    accuracy: Optional[float] = None
    is_active: bool


class ModelListResponse(BaseModel):
    models: list[ModelInfo]
    total: int


class ModelActivateRequest(BaseModel):
    model_name: str = Field(..., description="Name of the model to activate")
