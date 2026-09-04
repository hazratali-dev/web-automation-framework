import uuid
from datetime import datetime
from typing import Literal

from apscheduler.triggers.cron import CronTrigger
from pydantic import BaseModel, Field, field_validator

TaskStatus = Literal["active", "paused", "archived"]


class TaskCreateRequest(BaseModel):
    target_id: uuid.UUID
    task_type: str = Field(..., min_length=1)
    schedule_cron: str | None = None
    priority: int = 5

    @field_validator("schedule_cron")
    @classmethod
    def _validate_cron(cls, value: str | None) -> str | None:
        """§5.3 — reject a malformed cron expression here, at the API
        boundary, rather than letting it into the DB where it would only
        surface later as a scheduler crash (see AsyncioScheduler.sync(),
        which also guards against this defensively, but the real fix is to
        never store it in the first place)."""
        if value is None:
            return value
        try:
            CronTrigger.from_crontab(value)
        except ValueError as exc:
            raise ValueError(f"invalid cron expression: {exc}") from exc
        return value


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
