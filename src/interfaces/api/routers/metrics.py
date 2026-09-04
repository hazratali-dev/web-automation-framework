import uuid
from datetime import datetime

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database.models.metric import Metric as MetricModel
from src.infrastructure.database.models.target import Target as TargetModel
from src.infrastructure.database.models.task import Task as TaskModel
from src.infrastructure.database.models.task_run import TaskRun as TaskRunModel
from src.infrastructure.database.session import get_db

router = APIRouter(prefix="/api/task-runs", tags=["metrics"])


class MetricResponse(BaseModel):
    metric_name: str
    metric_value: float
    unit: str | None


class RecentRunResponse(BaseModel):
    id: uuid.UUID
    task_id: uuid.UUID
    task_type: str
    target_name: str
    status: str
    started_at: datetime | None
    duration_ms: int | None


@router.get("/{task_run_id}/metrics", response_model=list[MetricResponse])
async def get_task_run_metrics(task_run_id: uuid.UUID, db: AsyncSession = Depends(get_db)) -> list[MetricResponse]:
    """§5.5 — metrics query, for the dashboard's charts."""
    result = await db.execute(select(MetricModel).where(MetricModel.task_run_id == task_run_id))
    return [
        MetricResponse(metric_name=row.metric_name, metric_value=row.metric_value, unit=row.unit)
        for row in result.scalars().all()
    ]


@router.get("/recent", response_model=list[RecentRunResponse])
async def list_recent_runs(limit: int = 20, db: AsyncSession = Depends(get_db)) -> list[RecentRunResponse]:
    """§UI-refactor — the dashboard home's "Recent Runs" feed, across every
    task/target, newest first."""
    query = (
        select(TaskRunModel, TaskModel.task_type, TargetModel.name)
        .join(TaskModel, TaskRunModel.task_id == TaskModel.id)
        .join(TargetModel, TaskModel.target_id == TargetModel.id)
        .order_by(TaskRunModel.created_at.desc())
        .limit(limit)
    )
    result = await db.execute(query)
    return [
        RecentRunResponse(
            id=run.id,
            task_id=run.task_id,
            task_type=task_type,
            target_name=target_name,
            status=run.status,
            started_at=run.started_at,
            duration_ms=run.duration_ms,
        )
        for run, task_type, target_name in result.all()
    ]
