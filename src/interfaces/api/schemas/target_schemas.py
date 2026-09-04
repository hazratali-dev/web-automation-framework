import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class TargetCredentialsRequest(BaseModel):
    """§Product-readiness — PATCH /api/targets/{id}/credentials body. Plain
    text over HTTPS (prod, §6 TLS termination); encrypted server-side before
    it ever touches the DB (§8) — never logged, never echoed back."""

    email: str = Field(..., min_length=1)
    password: str = Field(..., min_length=1)


class TargetCreateRequest(BaseModel):
    name: str = Field(..., min_length=1)
    base_url: str = Field(..., min_length=1)
    target_type: str = "own_site"  # own_site / competitor


class TargetConfigUpdateRequest(BaseModel):
    """PATCH /api/targets/{id} — §5.5: viewport/headers/timeout only. Merged
    into the existing config, never overwrites credentials_encrypted /
    login_selectors (those have their own dedicated endpoints, §Product-readiness)."""

    viewport: dict | None = None
    headers: dict | None = None
    timeout_seconds: int | None = None


class TargetResponse(BaseModel):
    id: uuid.UUID
    name: str
    base_url: str
    target_type: str
    is_active: bool
    has_credentials: bool
    created_at: datetime | None = None
