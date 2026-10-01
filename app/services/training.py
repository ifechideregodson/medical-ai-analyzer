from __future__ import annotations

import asyncio
import json
import logging
import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

import torch
from torch import nn
from torch.utils.data import DataLoader, Dataset
from torchvision import models, transforms
from PIL import Image

logger = logging.getLogger("medical_ai")


class TrainingJob:
    def __init__(
        self,
        job_id: str,
        dataset_name: str,
        image_type: str,
        num_classes: int,
        labels: list[str],
        total_epochs: int = 10,
        auto_register: bool = True,
        activate_after_training: bool = True,
    ):
        self.job_id = job_id
        self.dataset_name = dataset_name
        self.image_type = image_type
        self.num_classes = num_classes
        self.labels = labels
        self.total_epochs = total_epochs
        self.auto_register = auto_register
        self.activate_after_training = activate_after_training
        self.status = "pending"
        self.epoch = 0
        self.loss = 0.0
        self.accuracy = 0.0
        self.progress = 0.0
        self.error_message = None
        self.model_name = None
        self.model_registered = False
        self.model_activated = False
        self.created_at = datetime.utcnow().isoformat()
        self.updated_at = datetime.utcnow().isoformat()

    def to_dict(self) -> dict[str, Any]:
        return {
            "job_id": self.job_id,
            "status": self.status,
            "dataset_name": self.dataset_name,
            "image_type": self.image_type,
            "epoch": self.epoch,
            "total_epochs": self.total_epochs,
            "progress": self.progress,
            "loss": self.loss,
            "accuracy": self.accuracy,
            "error_message": self.error_message,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "model_name": self.model_name,
            "model_registered": self.model_registered,
            "model_activated": self.model_activated,
        }


class SimpleImageDataset(Dataset):
    def __init__(self, image_paths: list[str], labels: list[int], transform=None):
        self.image_paths = image_paths
        self.labels = labels
        self.transform = transform

    def __len__(self):
        return len(self.image_paths)

    def __getitem__(self, idx):
        image = Image.open(self.image_paths[idx]).convert("RGB")
        if self.transform:
            image = self.transform(image)
        return image, self.labels[idx]


class TrainingService:
    def __init__(self):
        self.jobs: dict[str, TrainingJob] = {}
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        os.makedirs("data/uploads", exist_ok=True)
        os.makedirs("models/checkpoints", exist_ok=True)
        logger.info(f"Training service initialized on device: {self.device}")

    def create_job(
        self,
        dataset_name: str,
        image_type: str,
        num_classes: int,
        labels: list[str],
        auto_register: bool = True,
        activate_after_training: bool = True,
    ) -> TrainingJob:
        job_id = str(uuid.uuid4())
        job = TrainingJob(
            job_id=job_id,
            dataset_name=dataset_name,
            image_type=image_type,
            num_classes=num_classes,
            labels=labels,
            total_epochs=10,
            auto_register=auto_register,
            activate_after_training=activate_after_training,
        )
        self.jobs[job_id] = job
        return job

    def get_job(self, job_id: str) -> Optional[TrainingJob]:
        return self.jobs.get(job_id)

    def list_jobs(self) -> list[TrainingJob]:
        return list(self.jobs.values())

    async def train_async(
        self,
        job_id: str,
        image_paths: list[str],
        labels: list[int],
        num_epochs: int = 10,
        batch_size: int = 16,
        learning_rate: float = 1e-4,
    ) -> None:
        job = self.get_job(job_id)
        if not job:
            logger.error(f"Job {job_id} not found")
            return

        try:
            job.status = "running"
            job.updated_at = datetime.utcnow().isoformat()
            logger.info(f"Starting training job {job_id}")

            # Data preparation
            transform = transforms.Compose([
                transforms.Resize((224, 224)),
                transforms.RandomHorizontalFlip(),
                transforms.RandomRotation(15),
                transforms.ToTensor(),
                transforms.Normalize(
                    mean=[0.485, 0.456, 0.406],
                    std=[0.229, 0.224, 0.225],
                ),
            ])

            dataset = SimpleImageDataset(image_paths, labels, transform=transform)
            loader = DataLoader(dataset, batch_size=batch_size, shuffle=True)

            # Model creation
            model = models.efficientnet_b0(weights="DEFAULT")
            model.classifier[1] = nn.Linear(model.classifier[1].in_features, job.num_classes)
            model.to(self.device)
            model.train()

            criterion = nn.CrossEntropyLoss()
            optimizer = torch.optim.AdamW(model.parameters(), lr=learning_rate)
            scheduler = torch.optim.lr_scheduler.StepLR(optimizer, step_size=5, gamma=0.1)

            # Training loop
            for epoch in range(num_epochs):
                job.epoch = epoch + 1
                running_loss = 0.0
                correct = 0
                total = 0

                for batch_idx, (images, batch_labels) in enumerate(loader):
                    images, batch_labels = images.to(self.device), batch_labels.to(self.device)
                    optimizer.zero_grad()

                    outputs = model(images)
                    loss = criterion(outputs, batch_labels)
                    loss.backward()
                    optimizer.step()

                    running_loss += loss.item()
                    _, predicted = torch.max(outputs.data, 1)
                    total += batch_labels.size(0)
                    correct += (predicted == batch_labels).sum().item()

                    # Update progress
                    batch_progress = (batch_idx + 1) / len(loader)
                    epoch_progress = epoch / num_epochs
                    job.progress = ((epoch_progress + batch_progress / num_epochs) * 100)

                    # Allow other tasks to run
                    await asyncio.sleep(0.01)

                job.loss = running_loss / len(loader)
                job.accuracy = (correct / total) * 100 if total > 0 else 0.0
                job.progress = ((epoch + 1) / num_epochs) * 100
                job.updated_at = datetime.utcnow().isoformat()

                scheduler.step()
                logger.info(
                    f"Job {job_id} Epoch {epoch + 1}/{num_epochs} | "
                    f"Loss: {job.loss:.4f} | Accuracy: {job.accuracy:.2f}%"
                )

            # Save model checkpoint
            checkpoint_path = f"models/checkpoints/{job.dataset_name}_{job.image_type}_epoch{num_epochs}.pth"
            os.makedirs(os.path.dirname(checkpoint_path), exist_ok=True)
            torch.save(model.state_dict(), checkpoint_path)
            logger.info(f"Saved checkpoint to {checkpoint_path}")

            # Save final model
            job.model_name = f"{job.dataset_name}_{job.image_type}_{uuid.uuid4().hex[:8]}"
            model_dir = Path(f"models/{job.model_name}")
            model_dir.mkdir(parents=True, exist_ok=True)
            model_path = model_dir / "model.pth"
            torch.save(model, model_path)
            logger.info(f"Saved model to {model_path}")

            # Auto-register model
            if job.auto_register:
                metadata = {
                    "model_name": job.model_name,
                    "image_type": job.image_type,
                    "labels": job.labels,
                    "description": f"Auto-trained from {job.dataset_name}",
                    "accuracy": job.accuracy,
                    "file_path": str(model_path),
                    "file_size": model_path.stat().st_size,
                    "created_at": datetime.utcnow().isoformat(),
                    "is_active": job.activate_after_training,
                }
                metadata_file = model_dir / "metadata.json"
                with open(metadata_file, "w") as f:
                    json.dump(metadata, f, indent=2)
                job.model_registered = True
                logger.info(f"Model {job.model_name} registered")

                # Auto-activate model
                if job.activate_after_training:
                    active_models_file = Path("models/metadata/active_models.json")
                    active_models = {}
                    if active_models_file.exists():
                        with open(active_models_file, "r") as f:
                            active_models = json.load(f)
                    active_models[job.image_type] = job.model_name
                    with open(active_models_file, "w") as f:
                        json.dump(active_models, f, indent=2)
                    job.model_activated = True
                    logger.info(f"Model {job.model_name} activated for {job.image_type}")

            job.status = "completed"
            job.updated_at = datetime.utcnow().isoformat()
            logger.info(f"Job {job_id} completed successfully")

        except Exception as exc:
            job.status = "failed"
            job.error_message = str(exc)
            job.updated_at = datetime.utcnow().isoformat()
            logger.error(f"Job {job_id} failed: {exc}", exc_info=True)


# Global training service instance
training_service = TrainingService()
