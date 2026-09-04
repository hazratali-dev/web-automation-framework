import uuid

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database.models.metric import Metric as MetricModel
from src.infrastructure.database.session import get_db

router = APIRouter(prefix="/api/task-runs", tags=["metrics"])


class MetricResponse(BaseModel):
    metric_name: str
    metric_value: float
    unit: str | None


@router.get("/{task_run_id}/metrics", response_model=list[MetricResponse])
async def get_task_run_metrics(task_run_id: uuid.UUID, db: AsyncSession = Depends(get_db)) -> list[MetricResponse]:
    """§5.5 — metrics query, for the dashboard's charts."""
    result = await db.execute(select(MetricModel).where(MetricModel.task_run_id == task_run_id))
    return [
        MetricResponse(metric_name=row.metric_name, metric_value=row.metric_value, unit=row.unit)
        for row in result.scalars().all()
    ]
