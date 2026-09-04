import asyncio
from collections import Counter

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter()

POLL_INTERVAL_SECONDS = 0.5


@router.websocket("/ws/status")
async def status_websocket(websocket: WebSocket) -> None:
    """§5.5 — live status: '৫ জন চলমান, ১০ জন শেষ' style aggregate counts.
    Dev implementation just polls the shared in-memory dict (§Appendix A.3)
    every 500ms and pushes a snapshot — simple, correct at this scale, and
    avoids building a full pub/sub broadcaster for a handful of visitors."""
    await websocket.accept()
    status_store = websocket.app.state.status_store

    try:
        while True:
            all_status = await status_store.get_all()
            counts = Counter(entry["status"] for entry in all_status.values())
            await websocket.send_json(
                {
                    "queued": counts.get("queued", 0),
                    "running": counts.get("running", 0),
                    "success": counts.get("success", 0),
                    "failed": counts.get("failed", 0),
                    "total": len(all_status),
                }
            )
            await asyncio.sleep(POLL_INTERVAL_SECONDS)
    except WebSocketDisconnect:
        pass
