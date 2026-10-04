from __future__ import annotations

import hashlib
import os
from pathlib import Path
from tempfile import NamedTemporaryFile

import requests

from app.config import settings


def ensure_model_downloaded(image_type: str, model_path: str) -> str:
    path = Path(model_path)
    if path.exists() and path.stat().st_size > 0:
        return str(path)

    urls = {"xray": settings.xray_model_url, "skin": settings.skin_model_url}
    checksums = {"xray": settings.xray_model_sha256, "skin": settings.skin_model_sha256}
    url = urls[image_type]
    if not url:
        raise FileNotFoundError(
            f"No local {image_type} model exists and no model URL is configured"
        )

    path.parent.mkdir(parents=True, exist_ok=True)
    with NamedTemporaryFile(delete=False, dir=path.parent, suffix=".download") as tmp:
        temp_path = Path(tmp.name)

    try:
        digest = hashlib.sha256()
        with requests.get(
            url,
            stream=True,
            timeout=settings.model_download_timeout,
            headers={"User-Agent": "medical-ai-analyzer/1.0"},
        ) as response:
            response.raise_for_status()
            with temp_path.open("wb") as handle:
                for chunk in response.iter_content(chunk_size=1024 * 1024):
                    if chunk:
                        handle.write(chunk)
                        digest.update(chunk)

        expected = checksums[image_type]
        actual = digest.hexdigest()
        if expected and actual.lower() != expected.lower():
            raise RuntimeError(
                f"SHA256 mismatch for {image_type} model: expected {expected}, got {actual}"
            )

        os.replace(temp_path, path)
        return str(path)
    finally:
        temp_path.unlink(missing_ok=True)
