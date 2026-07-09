import asyncio
import json
from collections import defaultdict
from typing import Any


class ProgressBroadcaster:
    """Manages WebSocket connections and broadcasts progress events per session."""

    def __init__(self):
        self._connections: dict[str, list[asyncio.Queue]] = defaultdict(list)

    def subscribe(self, session_id: str) -> asyncio.Queue:
        queue: asyncio.Queue = asyncio.Queue()
        self._connections[session_id].append(queue)
        return queue

    def unsubscribe(self, session_id: str, queue: asyncio.Queue):
        if session_id in self._connections:
            self._connections[session_id] = [
                q for q in self._connections[session_id] if q is not queue
            ]
            if not self._connections[session_id]:
                del self._connections[session_id]

    async def broadcast(self, session_id: str, event_type: str, data: dict[str, Any]):
        message = json.dumps({"type": event_type, **data})
        if session_id in self._connections:
            for queue in self._connections[session_id]:
                await queue.put(message)

    async def send_progress(self, session_id: str, stage: str, progress: float, detail: str = ""):
        await self.broadcast(session_id, "progress", {
            "stage": stage,
            "progress": round(progress, 1),
            "detail": detail,
        })

    async def send_error(self, session_id: str, error: str):
        await self.broadcast(session_id, "error", {"detail": error})

    async def send_complete(self, session_id: str, stage: str, data: dict[str, Any] | None = None):
        await self.broadcast(session_id, "complete", {
            "stage": stage,
            **(data or {}),
        })


# Singleton instance
progress_broadcaster = ProgressBroadcaster()
