import asyncio
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from ..utils.progress import progress_broadcaster

router = APIRouter()


@router.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    await websocket.accept()
    queue = progress_broadcaster.subscribe(session_id)
    try:
        while True:
            try:
                message = await asyncio.wait_for(queue.get(), timeout=30.0)
                await websocket.send_text(message)
            except asyncio.TimeoutError:
                # Send keepalive ping
                await websocket.send_text('{"type":"ping"}')
    except WebSocketDisconnect:
        pass
    finally:
        progress_broadcaster.unsubscribe(session_id, queue)
