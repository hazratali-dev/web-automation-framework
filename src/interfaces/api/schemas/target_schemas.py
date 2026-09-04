import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, model_validator

LoginType = Literal["email_password", "single_password"]


class TargetCredentialsRequest(BaseModel):
    """§Product-readiness — PATCH /api/targets/{id}/credentials body. Plain
    text over HTTPS (prod, §6 TLS termination); encrypted server-side before
    it ever touches the DB (§8) — never logged, never echoed back.

    `login_type` covers sites with no email field at all (Shopify storefront
    password page, cPanel, ...) — `email` is only required when it's
    "email_password" (the default, backward-compatible with credentials set
    before this existed)."""

    login_type: LoginType = "email_password"
    email: str | None = None
    password: str = Field(..., min_length=1)

    @model_validator(mode="after")
    def _email_required_for_email_password_login(self) -> "TargetCredentialsRequest":
        if self.login_type == "email_password" and not self.email:
            raise ValueError("email is required when login_type is 'email_password'")
        return self


class TargetCreateRequest(BaseModel):
    name: str = Field(..., min_length=1)
    base_url: str = Field(..., min_length=1)
    target_type: str = "own_site"  # own_site / competitor


class TargetConfigUpdateRequest(BaseModel):
    """PATCH /api/targets/{id} — §5.5 config (viewport/headers/timeout) plus
    §UI-refactor basic-info edit (name/base_url/target_type). Config changes
    merge into the existing config JSON, never overwriting
    credentials_encrypted/login_selectors (those have their own dedicated
    endpoints, §Product-readiness). All fields optional — only what's sent
    gets changed."""

    name: str | None = Field(None, min_length=1)
    base_url: str | None = Field(None, min_length=1)
    target_type: str | None = None
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
