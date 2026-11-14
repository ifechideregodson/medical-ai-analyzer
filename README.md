# medical-ai-analyzer
Production-ready medical AI analyzer for X-ray and skin disease diagnostics with FastAPI, PyTorch, and Dockerized deployment


## MedAI clinical platform gateway

The private compatibility endpoint consumed by the MedAI clinical platform is:

`POST /api/v1/inference`

It accepts multipart fields `file`, `model_name`, `model_version`, and `request_hash`, authenticated with `Authorization: Bearer <MEDAI_WEB_API_KEY>`. Set the same high-entropy `MEDAI_WEB_API_KEY` secret in the analyzer and MedAI server environments. Never expose it to a browser or commit it to source control.

The requested model must be registered and active. `model_version` must be the immutable artifact fingerprint `sha256:<64 lowercase hex characters>`; calculate it from the exact deployed `.pth` artifact and store that value in the corresponding MedAI model registry version. The service verifies the uploaded image SHA-256 against `request_hash`, limits images to 20 MiB, and currently accepts JPEG, PNG, and WebP only.

**Clinical safety:** this adapter always returns `NEEDS_REVIEW`. Analyzer output remains research-only and is never represented as a diagnosis or clinically validated result. DICOM support, clinical validation, and production model governance require separate implementation and validation.
