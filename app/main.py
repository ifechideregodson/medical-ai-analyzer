from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import predict, training
from app.config import settings

app = FastAPI(
    title=settings.api_title,
    version=settings.api_version,
    debug=settings.debug,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(predict.router)
app.include_router(training.router)


@app.get("/health")
def health_check() -> dict:
    return {
        "status": "ok",
        "environment": settings.environment,
        "app": settings.app_name,
        "version": settings.api_version,
    }


@app.get("/")
def root() -> dict:
    return {"message": "Medical AI Analyzer API is running."}
