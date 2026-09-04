import uuid

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.use_cases.visitor_batch_use_cases import RunVisitorBatchUseCase
from src.domain.entities.task import Task
from src.infrastructure.database.repositories.audit_log_repository import SqlAlchemyAuditLogRepository
from src.infrastructure.database.repositories.target_repository import SqlAlchemyTargetRepository
from src.infrastructure.database.repositories.task_repository import SqlAlchemyTaskRepository
from src.infrastructure.database.repositories.task_run_repository import SqlAlchemyTaskRunRepository
from src.infrastructure.database.session import get_db
from src.interfaces.api.schemas.task_schemas import (
    TaskCreateRequest,
    TaskResponse,
    TaskRunResponse,
    TaskStatusUpdateRequest,
)

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/tasks", tags=["tasks"])


def _task_to_response(task: Task) -> TaskResponse:
    return TaskResponse(
        id=task.id,
        target_id=task.target_id,
        task_type=task.task_type,
        schedule_cron=task.schedule_cron,
        priority=task.priority,
        status=task.status,
        created_at=task.created_at,
    )


@router.post("", status_code=status.HTTP_201_CREATED, response_model=TaskResponse)
async def create_task(body: TaskCreateRequest, db: AsyncSession = Depends(get_db)) -> TaskResponse:
    target_repo = SqlAlchemyTargetRepository(db)
    if await target_repo.get(body.target_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Target not found")

    task_repo = SqlAlchemyTaskRepository(db)
    task = await task_repo.get_or_create(
        Task(target_id=body.target_id, task_type=body.task_type, schedule_cron=body.schedule_cron, priority=body.priority)
    )
    return _task_to_response(task)


@router.get("", response_model=list[TaskResponse])
async def list_tasks(target_id: uuid.UUID | None = None, db: AsyncSession = Depends(get_db)) -> list[TaskResponse]:
    task_repo = SqlAlchemyTaskRepository(db)
    return [_task_to_response(t) for t in await task_repo.list_all(target_id)]


@router.get("/{task_id}/runs", response_model=list[TaskRunResponse])
async def list_task_runs(
    task_id: uuid.UUID, limit: int = 20, offset: int = 0, db: AsyncSession = Depends(get_db)
) -> list[TaskRunResponse]:
    """§5.5 — task-run history, paginated."""
    repo = SqlAlchemyTaskRunRepository(db)
    runs = await repo.list_for_task(task_id, limit=limit, offset=offset)
    return [
        TaskRunResponse(
            id=r.id,
            task_id=r.task_id,
            status=r.status,
            started_at=r.started_at,
            finished_at=r.finished_at,
            duration_ms=r.duration_ms,
            retry_count=r.retry_count,
            error_message=r.error_message,
            result=r.result,
            screenshot_path=r.screenshot_path,
        )
        for r in runs
    ]


@router.patch("/{task_id}/status", response_model=TaskResponse)
async def update_task_status(
    task_id: uuid.UUID, body: TaskStatusUpdateRequest, db: AsyncSession = Depends(get_db)
) -> TaskResponse:
    """§5.3 pause/resume/archive — scheduler stops enqueueing new runs for a
    paused task; anything already in flight finishes normally."""
    task_repo = SqlAlchemyTaskRepository(db)
    task = await task_repo.get(task_id)
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")

    await task_repo.update_status(task_id, body.status)
    await SqlAlchemyAuditLogRepository(db).add(
        action="update_task_status", resource=f"task:{task_id}", extra={"status": body.status}
    )

    task = await task_repo.get(task_id)
    return _task_to_response(task)


@router.post("/{task_id}/run-now", status_code=status.HTTP_202_ACCEPTED)
async def run_task_now(task_id: uuid.UUID, request: Request, db: AsyncSession = Depends(get_db)) -> dict:
    """§5.3, §5.5 — bypasses the cron schedule, submits straight to the
    shared task_runner queue (still bound by Semaphore(N), §5.2). A
    paused/archived task can't be manually run either — pause means "not
    running", full stop, not just "not on a timer" (design decision from the
    dynamic-config pass)."""
    task_repo = SqlAlchemyTaskRepository(db)
    task = await task_repo.get(task_id)
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    if task.status != "active":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=f"Task is {task.status}, resume it before running"
        )

    await request.app.state.task_runner.submit(task_id)
    return {"submitted": True, "task_id": str(task_id)}


@router.post("/{task_id}/simulate-visitors", status_code=status.HTTP_202_ACCEPTED)
async def simulate_visitors(
    task_id: uuid.UUID, request: Request, count: int = 10, db: AsyncSession = Depends(get_db)
) -> dict:
    """§Appendix A.2 — dashboard-triggered visitor-batch simulation, batched
    at whatever runtime_config.max_concurrent_browsers currently says. Runs
    in the background (fire-and-forget, tracked on app.state so it isn't
    garbage-collected mid-flight) — the HTTP request returns immediately,
    progress is visible over the /ws/status WebSocket."""
    task_repo = SqlAlchemyTaskRepository(db)
    task = await task_repo.get(task_id)
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    if task.status != "active":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"Task is {task.status}")

    target = await SqlAlchemyTargetRepository(db).get(task.target_id)
    if target is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Target not found")

    state = request.app.state
    use_case = RunVisitorBatchUseCase(
        state.engine,
        state.session_factory,
        circuit_registry=state.circuit_registry,
        status_store=state.status_store,
    )

    async def _run() -> None:
        try:
            await use_case.execute(url=target.base_url, total_visitors=count, use_proxy=False)
        except Exception:
            logger.exception("simulate_visitors_background_task_failed", task_id=str(task_id))

    task_handle = state.background_tasks.create(_run())
    logger.info("simulate_visitors_started", task_id=str(task_id), count=count, background_task=str(task_handle))

    return {"started": True, "task_id": str(task_id), "count": count}
