"""Durable job queue with Redis fallback to in-process execution."""
from __future__ import annotations

import logging
from typing import Callable, Optional

from config import settings

logger = logging.getLogger(__name__)


def enqueue_job(task: Callable, *args, **kwargs) -> str:
    """
    Enqueue a background job. Uses Redis/RQ when TV_REDIS_URL is set,
    otherwise returns 'inline' and caller should run via BackgroundTasks.
    """
    if not settings.redis_url:
        return "inline"

    try:
        from redis import Redis
        from rq import Queue

        redis_conn = Redis.from_url(settings.redis_url)
        queue = Queue(settings.redis_queue_name, connection=redis_conn)
        job = queue.enqueue(task, *args, **kwargs, job_timeout=600)
        return job.id
    except Exception as exc:
        logger.warning("Redis queue unavailable, falling back to inline: %s", exc)
        return "inline"


def queue_status() -> dict:
    if not settings.redis_url:
        return {"backend": "inline", "redis_connected": False}
    try:
        from redis import Redis

        conn = Redis.from_url(settings.redis_url)
        conn.ping()
        return {"backend": "redis", "redis_connected": True, "url": settings.redis_url.split("@")[-1]}
    except Exception as exc:
        return {"backend": "inline", "redis_connected": False, "error": str(exc)}
