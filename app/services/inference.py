from __future__ import annotations

from typing import Any

import numpy as np
import torch
from PIL import Image
from torchvision import transforms

from app.config import settings
from app.services.model_registry import ModelConfig, ensure_model_exists, get_model_config, model_registry

DEVICE = "cuda" if torch.cuda.is_available() else "cpu"


class InferenceService:
    def __init__(self) -> None:
        self.confidence_threshold = settings.confidence_threshold
        self.review_threshold = settings.review_threshold

    def _load_model(self, model_path: str, image_type: str) -> torch.nn.Module:
        ensure_model_exists(model_path, image_type)
        model = torch.load(model_path, map_location=DEVICE)
        if hasattr(model, "eval"):
            model.eval()
        return model

    def _preprocess(self, image: Image.Image, image_size: tuple[int, int] = (224, 224)) -> torch.Tensor:
        rgb_image = image.convert("RGB").resize(image_size)
        tensor = transforms.ToTensor()(rgb_image)
        tensor = transforms.Normalize(
            mean=[0.485, 0.456, 0.406],
            std=[0.229, 0.224, 0.225],
        )(tensor)
        return tensor.unsqueeze(0).to(DEVICE)

    def predict(
        self,
        image: Image.Image,
        image_type: str,
        model_name: str | None = None,
    ) -> dict[str, Any]:
        if model_name is None:
            config = get_model_config(image_type)
        else:
            # Pin gateway inference to the exact model that was authenticated and version-checked.
            metadata = model_registry.get_model(model_name)
            if metadata.get("image_type") != image_type:
                raise ValueError("Requested model image type does not match inference input")
            if not metadata.get("is_active"):
                raise ValueError("Requested model is no longer active")
            config = ModelConfig(
                model_name=metadata["model_name"],
                image_type=metadata["image_type"],
                model_path=metadata["file_path"],
                labels=metadata["labels"],
                source="registry",
            )

        model = self._load_model(config.model_path, image_type)
        tensor = self._preprocess(image)

        with torch.no_grad():
            logits = model(tensor)
            probabilities = torch.softmax(logits, dim=1).cpu().numpy()[0]
            pred_index = int(np.argmax(probabilities))
            confidence = float(probabilities[pred_index])

        if pred_index >= len(config.labels):
            raise RuntimeError(
                f"Model returned class index {pred_index}, but only {len(config.labels)} labels are configured"
            )

        scores = {
            config.labels[i]: round(float(probabilities[i]), 4)
            for i in range(min(len(config.labels), len(probabilities)))
        }
        needs_review = confidence < self.confidence_threshold or confidence < self.review_threshold

        return {
            "label": config.labels[pred_index],
            "confidence": round(confidence, 4),
            "all_scores": scores,
            "needs_review": needs_review,
            "model_name": config.model_name,
            "model_source": config.source,
            "research_status": "research_only_not_clinically_validated",
        }
