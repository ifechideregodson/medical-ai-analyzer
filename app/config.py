from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    environment: str = "development"
    debug: bool = False
    app_name: str = "Medical AI Analyzer"
    api_title: str = "Medical AI Analyzer API"
    api_version: str = "1.0.0"
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    database_url: str = "sqlite:///./medical_ai.db"
    redis_url: str = "redis://localhost:6379/0"
    xray_model_path: str = "models/xray_model.pth"
    skin_model_path: str = "models/skin_model.pth"
    xray_model_url: str = ""
    skin_model_url: str = ""
    xray_model_sha256: str = ""
    skin_model_sha256: str = ""
    model_download_timeout: int = 300
    confidence_threshold: float = 0.65
    review_threshold: float = 0.75
    secret_key: str = "change-me-in-production"
    allowed_origins: str = "http://localhost:3000,http://localhost:8501"
    log_level: str = "INFO"

    @property
    def allowed_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.allowed_origins.split(",") if origin.strip()]

    def model_path_for(self, image_type: str) -> str:
        if image_type == "xray":
            return self.xray_model_path
        if image_type == "skin":
            return self.skin_model_path
        raise ValueError(f"Unsupported image type: {image_type}")


settings = Settings()
