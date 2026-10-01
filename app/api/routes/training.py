import asyncio
from typing import Literal
from io import BytesIO
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile, BackgroundTasks
from PIL import Image

from app.schemas.training import TrainingDataset, TrainingJobResponse, TrainingJobStatus
from app.services.training import training_service

router = APIRouter(prefix="/api/v1/training", tags=["training"])


@router.post("/jobs", response_model=TrainingJobResponse)
async def create_training_job(config: TrainingDataset) -> dict:
    """Create a new training job."""
    if config.image_type not in {"xray", "skin"}:
        raise HTTPException(status_code=400, detail="image_type must be 'xray' or 'skin'")

    if config.num_classes != len(config.labels):
        raise HTTPException(
            status_code=400,
            detail=f"num_classes ({config.num_classes}) must match labels length ({len(config.labels)})",
        )

    job = training_service.create_job(
        dataset_name=config.dataset_name,
        image_type=config.image_type,
        num_classes=config.num_classes,
        labels=config.labels,
    )

    return {
        "job_id": job.job_id,
        "status": job.status,
        "dataset_name": job.dataset_name,
        "image_type": job.image_type,
        "progress": job.progress,
        "epoch": job.epoch,
        "total_epochs": job.total_epochs,
        "message": f"Job {job.job_id} created",
    }


@router.get("/jobs/{job_id}", response_model=TrainingJobStatus)
async def get_job_status(job_id: str) -> dict:
    """Get the status of a training job."""
    job = training_service.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

    return job.to_dict()


@router.get("/jobs", response_model=list[TrainingJobStatus])
async def list_jobs() -> list[dict]:
    """List all training jobs."""
    jobs = training_service.list_jobs()
    return [job.to_dict() for job in jobs]


@router.post("/jobs/{job_id}/upload")
async def upload_training_data(
    job_id: str,
    files: list[UploadFile] = File(...),
    labels_json: str = "",
) -> dict:
    """Upload training images for a job."""
    job = training_service.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

    if job.status not in {"pending", "running"}:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot upload data for job in status: {job.status}",
        )

    upload_dir = Path(f"data/uploads/{job_id}")
    upload_dir.mkdir(parents=True, exist_ok=True)

    saved_files = []
    for file in files:
        if file.content_type not in {"image/jpeg", "image/png", "image/webp"}:
            raise HTTPException(status_code=400, detail=f"Unsupported file type: {file.content_type}")

        try:
            image_bytes = await file.read()
            image = Image.open(BytesIO(image_bytes)).convert("RGB")
            file_path = upload_dir / file.filename
            image.save(file_path)
            saved_files.append(str(file_path))
        except Exception as exc:
            raise HTTPException(status_code=400, detail=f"Failed to process {file.filename}: {exc}") from exc

    return {
        "job_id": job_id,
        "uploaded_files": len(saved_files),
        "file_paths": saved_files,
    }


@router.post("/jobs/{job_id}/start")
async def start_training(
    job_id: str,
    background_tasks: BackgroundTasks,
    labels: list[int] | None = None,
    num_epochs: int = 10,
    batch_size: int = 16,
    learning_rate: float = 1e-4,
) -> dict:
    """Start training for a job."""
    job = training_service.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

    if job.status == "running":
        raise HTTPException(status_code=400, detail="Job is already running")

    upload_dir = Path(f"data/uploads/{job_id}")
    if not upload_dir.exists():
        raise HTTPException(status_code=400, detail="No training data uploaded for this job")

    image_files = list(upload_dir.glob("*.*"))
    if not image_files:
        raise HTTPException(status_code=400, detail="No images found in upload directory")

    if labels is None:
        labels = [i % job.num_classes for i in range(len(image_files))]

    if len(labels) != len(image_files):
        raise HTTPException(
            status_code=400,
            detail=f"Labels count ({len(labels)}) must match images count ({len(image_files)})",
        )

    image_paths = [str(f) for f in image_files]

    # Run training in background
    background_tasks.add_task(
        training_service.train_async,
        job_id=job_id,
        image_paths=image_paths,
        labels=labels,
        num_epochs=num_epochs,
        batch_size=batch_size,
        learning_rate=learning_rate,
    )

    return {
        "job_id": job_id,
        "status": "training_started",
        "images_count": len(image_files),
        "epochs": num_epochs,
        "batch_size": batch_size,
    }
