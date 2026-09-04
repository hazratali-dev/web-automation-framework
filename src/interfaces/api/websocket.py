import asyncio
import base64
import uuid
from collections import Counter

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter()

STATUS_POLL_INTERVAL_SECONDS = 0.5
PREVIEW_POLL_INTERVAL_SECONDS = 1.0


@router.websocket("/ws/status")
async def status_websocket(websocket: WebSocket) -> None:
    """§5.5 — live status: 'X running, Y done' style aggregate counts, plus
    the individual running task_run_ids so the dashboard can offer a picker
    for /ws/preview (§Live-preview). Dev implementation just polls the
    shared in-memory dict (§Appendix A.3) every 500ms and pushes a snapshot
    — simple, correct at this scale, avoids building a full pub/sub
    broadcaster for a handful of visitors."""
    await websocket.accept()
    status_store = websocket.app.state.status_store

    try:
        while True:
            all_status = await status_store.get_all()
            counts = Counter(entry["status"] for entry in all_status.values())
            running_ids = [
                entry["task_run_id"] for entry in all_status.values() if entry["status"] in ("queued", "running")
            ]
            await websocket.send_json(
                {
                    "queued": counts.get("queued", 0),
                    "running": counts.get("running", 0),
                    "success": counts.get("success", 0),
                    "failed": counts.get("failed", 0),
                    "total": len(all_status),
                    "running_task_run_ids": running_ids,
                }
            )
            await asyncio.sleep(STATUS_POLL_INTERVAL_SECONDS)
    except WebSocketDisconnect:
        pass


@router.websocket("/ws/preview/{task_run_id}")
async def preview_websocket(websocket: WebSocket, task_run_id: uuid.UUID) -> None:
    """§Live-preview — streams the latest screenshot (base64 JPEG, refreshed
    by BrowserEngine every ~3s while the session runs) for one task_run.
    Sends {"active": false} once the run is no longer in the preview store
    (finished, or never started) so the dashboard can show a placeholder."""
    await websocket.accept()
    preview_store = websocket.app.state.preview_store

    try:
        while True:
            image_bytes = await preview_store.get(task_run_id)
            if image_bytes is None:
                await websocket.send_json({"active": False})
            else:
                encoded = base64.b64encode(image_bytes).decode("ascii")
                await websocket.send_json({"active": True, "image": f"data:image/jpeg;base64,{encoded}"})
            await asyncio.sleep(PREVIEW_POLL_INTERVAL_SECONDS)
    except WebSocketDisconnect:
        pass
