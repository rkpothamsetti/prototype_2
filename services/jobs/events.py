"""Job event bus for WebSocket progress streaming."""
from __future__ import annotations

import asyncio
from collections import defaultdict
from typing import Any


class JobEventBus:
    def __init__(self) -> None:
        self._events: dict[str, list[dict[str, Any]]] = defaultdict(list)
        self._queues: dict[str, list[asyncio.Queue]] = defaultdict(list)

    def emit(self, job_id: str, event: str, data: dict[str, Any] | None = None) -> None:
        payload = {"event": event, "job_id": job_id, "data": data or {}}
        self._events[job_id].append(payload)
        for queue in self._queues.get(job_id, []):
            try:
                queue.put_nowait(payload)
            except asyncio.QueueFull:
                pass

    def history(self, job_id: str) -> list[dict[str, Any]]:
        return list(self._events.get(job_id, []))

    def subscribe(self, job_id: str) -> asyncio.Queue:
        queue: asyncio.Queue = asyncio.Queue(maxsize=50)
        self._queues[job_id].append(queue)
        for item in self._events.get(job_id, []):
            queue.put_nowait(item)
        return queue

    def unsubscribe(self, job_id: str, queue: asyncio.Queue) -> None:
        if job_id in self._queues and queue in self._queues[job_id]:
            self._queues[job_id].remove(queue)


job_events = JobEventBus()
