from pydantic import BaseModel, Field


class TargetCredentialsRequest(BaseModel):
    """§Product-readiness — PATCH /api/targets/{id}/credentials body. Plain
    text over HTTPS (prod, §6 TLS termination); encrypted server-side before
    it ever touches the DB (§8) — never logged, never echoed back."""

    email: str = Field(..., min_length=1)
    password: str = Field(..., min_length=1)
