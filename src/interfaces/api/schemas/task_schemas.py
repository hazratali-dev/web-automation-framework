import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

TaskStatus = Literal["active", "paused", "archived"]


class TaskCreateRequest(BaseModel):
    target_id: uuid.UUID
    task_type: str = Field(..., min_length=1)
    schedule_cron: str | None = None
    priority: int = 5


class TaskStatusUpdateRequest(BaseModel):
    status: TaskStatus


class TaskResponse(BaseModel):
    id: uuid.UUID
    target_id: uuid.UUID
    task_type: str
    schedule_cron: str | None
    priority: int
    status: TaskStatus
    created_at: datetime | None = None


class TaskRunResponse(BaseModel):
    id: uuid.UUID
    task_id: uuid.UUID
    status: str
    started_at: datetime | None
    finished_at: datetime | None
    duration_ms: int | None
    retry_count: int
    error_message: str | None
    result: dict | None
    screenshot_path: str | None
