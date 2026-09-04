from pydantic import BaseModel, Field


class RuntimeConfigItem(BaseModel):
    key: str
    value: str


class RuntimeConfigUpdateRequest(BaseModel):
    value: str = Field(..., min_length=1)
