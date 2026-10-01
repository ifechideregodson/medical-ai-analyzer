from typing import Optional
from pydantic import BaseModel, Field


class TrainingDataset(BaseModel):
    dataset_name: str = Field(..., description="Name of the dataset (e.g., 'xray_v1')")
    image_type: str = Field(..., description="Type: 'xray' or 'skin'")
    num_classes: int = Field(..., ge=2, le=50)
    train_size: int = Field(..., ge=10, description="Number of training images")
    val_size: int = Field(..., ge=5, description="Number of validation images")
    labels: list[str] = Field(..., description="List of class labels")
    auto_register: bool = Field(default=True, description="Auto-register model after training")
    activate_after_training: bool = Field(default=True, description="Activate model after training")


class TrainingJobResponse(BaseModel):
    job_id: str
    status: str
    dataset_name: str
    image_type: str
    progress: float
    epoch: int
    total_epochs: int
    loss: Optional[float] = None
    accuracy: Optional[float] = None
    message: str
    model_name: Optional[str] = None


class TrainingJobStatus(BaseModel):
    job_id: str
    status: str  # "pending", "running", "completed", "failed"
    progress: float
    epoch: int
    total_epochs: int
    loss: Optional[float] = None
    accuracy: Optional[float] = None
    error_message: Optional[str] = None
    created_at: str
    updated_at: str
    model_name: Optional[str] = None
    model_registered: bool = False
    model_activated: bool = False
