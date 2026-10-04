from pydantic import BaseModel, Field


class APIKeyCreateRequest(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    owner: str = Field(min_length=2, max_length=255)


class APIKeyCreateResponse(BaseModel):
    api_key: str
    key_prefix: str
    name: str
    owner: str
    warning: str


class APIKeyInfo(BaseModel):
    id: int
    name: str
    owner: str
    key_prefix: str
    created_at: str
    last_used_at: str | None
    revoked_at: str | None
    is_active: bool
