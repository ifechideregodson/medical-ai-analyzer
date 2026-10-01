from __future__ import annotations

import json
import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

import torch


class ModelRegistry:
    def __init__(self, models_dir: str = "models"):
        self.models_dir = Path(models_dir)
        self.models_dir.mkdir(parents=True, exist_ok=True)
        self.metadata_dir = self.models_dir / "metadata"
        self.metadata_dir.mkdir(parents=True, exist_ok=True)
        self.active_models_file = self.metadata_dir / "active_models.json"

    def _load_active_models(self) -> dict[str, str]:
        if self.active_models_file.exists():
            with open(self.active_models_file, "r") as f:
                return json.load(f)
        return {}

    def _save_active_models(self, active: dict[str, str]) -> None:
        with open(self.active_models_file, "w") as f:
            json.dump(active, f, indent=2)

    def upload_model(
        self,
        model_file_path: str,
        model_name: str,
        image_type: str,
        labels: list[str],
        description: Optional[str] = None,
        accuracy: Optional[float] = None,
    ) -> dict[str, Any]:
        if not Path(model_file_path).exists():
            raise FileNotFoundError(f"Model file not found: {model_file_path}")

        if image_type not in {"xray", "skin"}:
            raise ValueError("image_type must be 'xray' or 'skin'")

        if not labels or len(labels) < 2:
            raise ValueError("At least 2 labels required")

        # Create model directory
        model_dir = self.models_dir / model_name
        model_dir.mkdir(parents=True, exist_ok=True)

        # Copy model file
        dest_file = model_dir / "model.pth"
        shutil.copy(model_file_path, dest_file)

        # Save metadata
        metadata = {
            "model_name": model_name,
            "image_type": image_type,
            "labels": labels,
            "description": description or "",
            "accuracy": accuracy,
            "file_path": str(dest_file),
            "file_size": dest_file.stat().st_size,
            "created_at": datetime.utcnow().isoformat(),
            "is_active": False,
        }

        metadata_file = model_dir / "metadata.json"
        with open(metadata_file, "w") as f:
            json.dump(metadata, f, indent=2)

        return metadata

    def list_models(self, image_type: Optional[str] = None) -> list[dict[str, Any]]:
        models = []
        active = self._load_active_models()

        for model_dir in self.models_dir.iterdir():
            if not model_dir.is_dir() or model_dir.name in {"checkpoints", "metadata"}:
                continue

            metadata_file = model_dir / "metadata.json"
            if metadata_file.exists():
                with open(metadata_file, "r") as f:
                    metadata = json.load(f)

                # Filter by image_type if provided
                if image_type and metadata["image_type"] != image_type:
                    continue

                # Check if model is active
                metadata["is_active"] = active.get(metadata["image_type"]) == metadata["model_name"]
                models.append(metadata)

        return sorted(models, key=lambda x: x["created_at"], reverse=True)

    def get_model(self, model_name: str) -> dict[str, Any]:
        metadata_file = self.models_dir / model_name / "metadata.json"
        if not metadata_file.exists():
            raise FileNotFoundError(f"Model {model_name} not found")

        with open(metadata_file, "r") as f:
            metadata = json.load(f)

        active = self._load_active_models()
        metadata["is_active"] = active.get(metadata["image_type"]) == metadata["model_name"]
        return metadata

    def activate_model(self, model_name: str) -> dict[str, Any]:
        metadata = self.get_model(model_name)
        active = self._load_active_models()
        image_type = metadata["image_type"]

        # Update active model
        active[image_type] = model_name
        self._save_active_models(active)

        # Update metadata file
        metadata["is_active"] = True
        metadata_file = self.models_dir / model_name / "metadata.json"
        with open(metadata_file, "w") as f:
            json.dump(metadata, f, indent=2)

        return metadata

    def get_active_model(self, image_type: str) -> Optional[dict[str, Any]]:
        active = self._load_active_models()
        model_name = active.get(image_type)
        if model_name:
            return self.get_model(model_name)
        return None

    def delete_model(self, model_name: str) -> None:
        model_dir = self.models_dir / model_name
        if model_dir.exists():
            shutil.rmtree(model_dir)
            # Remove from active if it was active
            active = self._load_active_models()
            for key, value in list(active.items()):
                if value == model_name:
                    del active[key]
            self._save_active_models(active)

    def load_model(self, model_name: str) -> torch.nn.Module:
        metadata_file = self.models_dir / model_name / "metadata.json"
        if not metadata_file.exists():
            raise FileNotFoundError(f"Model {model_name} not found")

        with open(metadata_file, "r") as f:
            metadata = json.load(f)

        model_path = metadata["file_path"]
        if not Path(model_path).exists():
            raise FileNotFoundError(f"Model file not found: {model_path}")

        device = "cuda" if torch.cuda.is_available() else "cpu"
        model = torch.load(model_path, map_location=device)
        if hasattr(model, "eval"):
            model.eval()
        return model


# Global model registry instance
model_registry = ModelRegistry()
