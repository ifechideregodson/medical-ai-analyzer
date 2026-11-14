import hashlib
from io import BytesIO

from fastapi.testclient import TestClient
from PIL import Image

from app.main import app
from app.api.routes import medai_gateway


def png_bytes() -> bytes:
    buffer = BytesIO()
    Image.new("RGB", (8, 8), "white").save(buffer, format="PNG")
    return buffer.getvalue()


def test_medai_gateway_requires_bearer_key(monkeypatch):
    monkeypatch.setenv("MEDAI_WEB_API_KEY", "test-secret")
    response = TestClient(app).post(
        "/api/v1/inference",
        files={"file": ("scan.png", png_bytes(), "image/png")},
        data={"model_name": "xray-v1", "model_version": "sha256:" + "0" * 64, "request_hash": hashlib.sha256(png_bytes()).hexdigest()},
    )
    assert response.status_code == 401


def test_medai_gateway_returns_needs_review_for_research_model(monkeypatch, tmp_path):
    monkeypatch.setenv("MEDAI_WEB_API_KEY", "test-secret")
    artifact = tmp_path / "model.pth"
    artifact.write_bytes(b"test-model-artifact")
    version = "sha256:" + hashlib.sha256(artifact.read_bytes()).hexdigest()
    image = png_bytes()
    monkeypatch.setattr(
        medai_gateway.model_registry,
        "get_model",
        lambda name: {
            "model_name": name,
            "image_type": "xray",
            "labels": ["normal", "pneumonia"],
            "file_path": str(artifact),
            "is_active": True,
        },
    )
    called = {}

    def fake_predict(image, image_type, model_name=None):
        called["model_name"] = model_name
        return {
            "label": "pneumonia",
            "confidence": 0.91,
            "model_name": model_name,
            "research_status": "research_only_not_clinically_validated",
        }

    monkeypatch.setattr(medai_gateway.inference_service, "predict", fake_predict)

    response = TestClient(app).post(
        "/api/v1/inference",
        headers={"Authorization": "Bearer test-secret"},
        files={"file": ("scan.png", image, "image/png")},
        data={
            "model_name": "xray-v1",
            "model_version": version,
            "request_hash": hashlib.sha256(image).hexdigest(),
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "NEEDS_REVIEW"
    assert payload["model"] == {"name": "xray-v1", "version": version}
    assert payload["findings"][0]["label"] == "pneumonia"
    assert any("not been clinically validated" in item for item in payload["limitations"])
    assert called["model_name"] == "xray-v1"


def test_medai_gateway_rejects_image_hash_mismatch(monkeypatch):
    monkeypatch.setenv("MEDAI_WEB_API_KEY", "test-secret")
    image = png_bytes()
    response = TestClient(app).post(
        "/api/v1/inference",
        headers={"Authorization": "Bearer test-secret"},
        files={"file": ("scan.png", image, "image/png")},
        data={"model_name": "xray-v1", "model_version": "sha256:" + "0" * 64, "request_hash": "0" * 64},
    )
    assert response.status_code == 400


def test_medai_gateway_rejects_model_path_traversal(monkeypatch):
    monkeypatch.setenv("MEDAI_WEB_API_KEY", "test-secret")
    monkeypatch.setattr(
        medai_gateway.model_registry,
        "get_model",
        lambda name: (_ for _ in ()).throw(AssertionError("registry must not be called")),
    )
    image = png_bytes()
    response = TestClient(app).post(
        "/api/v1/inference",
        headers={"Authorization": "Bearer test-secret"},
        files={"file": ("scan.png", image, "image/png")},
        data={
            "model_name": "../secret",
            "model_version": "sha256:" + "0" * 64,
            "request_hash": hashlib.sha256(image).hexdigest(),
        },
    )
    assert response.status_code == 400


def test_medai_gateway_rejects_oversized_image_dimensions(monkeypatch):
    monkeypatch.setenv("MEDAI_WEB_API_KEY", "test-secret")
    image_buffer = BytesIO()
    Image.new("RGB", (7000, 7000), "white").save(image_buffer, format="PNG")
    image = image_buffer.getvalue()
    response = TestClient(app).post(
        "/api/v1/inference",
        headers={"Authorization": "Bearer test-secret"},
        files={"file": ("large.png", image, "image/png")},
        data={
            "model_name": "xray-v1",
            "model_version": "sha256:" + "0" * 64,
            "request_hash": hashlib.sha256(image).hexdigest(),
        },
    )
    assert response.status_code == 413
