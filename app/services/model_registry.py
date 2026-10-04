from __future__ import annotations

import json
import os
import shutil
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

import torch

from app.config import settings
from app.services.model_artifact import ensure_model_downloaded


@dataclass(frozen=True)
class ModelConfig:
    model_name: str
    image_type: str
    model_path: str
    labels: list[str]
    source: str = "configured"


DEFAULT_LABELS = {
    "xray": ["normal", "pneumonia"],
    "skin": [
        "actinic keratoses",
        "basal cell carcinoma",
        "benign keratosis-like lesions",
        "dermatofibroma",
        "melanoma",
        "melanocytic nevi",
        "vascular lesions",
    ],
}


class ModelRegistry:
    def __init__(self, models_dir: str = "models"):
        self.models_dir = Path(models_dir)
        self.models_dir.mkdir(parents=True, exist_ok=True)
        self.metadata_dir = self.models_dir / "metadata"
        self.metadata_dir.mkdir(parents=True, exist_ok=True)
        self.active_models_file = self.metadata_dir / "active_models.json"

    def _load_active_models(self) -> dict[str, str]:
        if self.active_models_file.exists():
            with self.active_models_file.open("r", encoding="utf-8") as f:
                return json.load(f)
        return {}

    def _save_active_models(self, active: dict[str, str]) -> None:
        with self.active_models_file.open("w", encoding="utf-8") as f:
            json.dump(active, f, indent=2)

    def upload_model(self, model_file_path: str, model_name: str, image_type: str,
                     labels: list[str], description: Optional[str] = None,
                     accuracy: Optional[float] = None) -> dict[str, Any]:
        if not Path(model_file_path).exists():
            raise FileNotFoundError(f"Model file not found: {model_file_path}")
        if image_type not in {"xray", "skin"}:
            raise ValueError("image_type must be 'xray' or 'skin'")
        if not labels or len(labels) < 2:
            raise ValueError("At least 2 labels required")

        model_dir = self.models_dir / model_name
        model_dir.mkdir(parents=True, exist_ok=True)
        dest_file = model_dir / "model.pth"
        shutil.copy(model_file_path, dest_file)

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
        with (model_dir / "metadata.json").open("w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2)
        return metadata

    def list_models(self, image_type: Optional[str] = None) -> list[dict[str, Any]]:
        models = []
        active = self._load_active_models()
        for model_dir in self.models_dir.iterdir():
            if not model_dir.is_dir() or model_dir.name in {"checkpoints", "metadata"}:
                continue
            metadata_file = model_dir / "metadata.json"
            if not metadata_file.exists():
                continue
            with metadata_file.open("r", encoding="utf-8") as f:
                metadata = json.load(f)
            if image_type and metadata["image_type"] != image_type:
                continue
            metadata["is_active"] = active.get(metadata["image_type"]) == metadata["model_name"]
            models.append(metadata)
        return sorted(models, key=lambda x: x["created_at"], reverse=True)

    def get_model(self, model_name: str) -> dict[str, Any]:
        metadata_file = self.models_dir / model_name / "metadata.json"
        if not metadata_file.exists():
            raise FileNotFoundError(f"Model {model_name} not found")
        with metadata_file.open("r", encoding="utf-8") as f:
            metadata = json.load(f)
        active = self._load_active_models()
        metadata["is_active"] = active.get(metadata["image_type"]) == metadata["model_name"]
        return metadata

    def activate_model(self, model_name: str) -> dict[str, Any]:
        metadata = self.get_model(model_name)
        active = self._load_active_models()
        active[metadata["image_type"]] = model_name
        self._save_active_models(active)
        metadata["is_active"] = True
        with (self.models_dir / model_name / "metadata.json").open("w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2)
        return metadata

    def delete_model(self, model_name: str) -> None:
        model_dir = self.models_dir / model_name
        if model_dir.exists():
            shutil.rmtree(model_dir)
            active = self._load_active_models()
            for key, value in list(active.items()):
                if value == model_name:
                    del active[key]
            self._save_active_models(active)

    def load_model(self, model_name: str) -> torch.nn.Module:
        metadata = self.get_model(model_name)
        model_path = metadata["file_path"]
        if not Path(model_path).exists():
            raise FileNotFoundError(f"Model file not found: {model_path}")
        device = "cuda" if torch.cuda.is_available() else "cpu"
        model = torch.load(model_path, map_location=device)
        if hasattr(model, "eval"):
            model.eval()
        return model


model_registry = ModelRegistry()


def get_model_config(image_type: str) -> ModelConfig:
    if image_type not in {"xray", "skin"}:
        raise ValueError(f"Unsupported image type: {image_type}")

    active = model_registry.get_active_model(image_type)
    if active:
        return ModelConfig(
            model_name=active["model_name"],
            image_type=image_type,
            model_path=active["file_path"],
            labels=active["labels"],
            source="registry",
        )

    model_path = settings.model_path_for(image_type)
    labels_env = os.getenv(f"{image_type.upper()}_MODEL_LABELS", "")
    labels = json.loads(labels_env) if labels_env else DEFAULT_LABELS[image_type]
    return ModelConfig(
        model_name=f"{image_type}-configured",
        image_type=image_type,
        model_path=model_path,
        labels=labels,
        source="configured",
    )


def ensure_model_exists(model_path: str, image_type: str | None = None) -> str:
    if Path(model_path).exists() and Path(model_path).stat().st_size > 0:
        return model_path
    if image_type is None:
        if model_path == settings.xray_model_path:
            image_type = "xray"
        elif model_path == settings.skin_model_path:
            image_type = "skin"
    if image_type is None:
        raise FileNotFoundError(f"Model file not found: {model_path}")
    return ensure_model_downloaded(image_type, model_path)
