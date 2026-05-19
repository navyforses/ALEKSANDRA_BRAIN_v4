"""
celery_tasks.py — Celery tasks for distributed chunk processing.

Each task processes one 10×10×10 voxel chunk from a 3D brain volume.
Designed to run in parallel across multiple Celery workers.

Usage:
    from agents.swarm.celery_tasks import process_chunk_task
    result = process_chunk_task.delay(chunk_info, file_path)
    output = result.get(timeout=120)
"""

from __future__ import annotations

import time
from typing import Any

from agents.swarm.celery_app import app
from agents.swarm.chunk_worker import ChunkWorkerAgent, ChunkWorkerResult


@app.task(bind=True, max_retries=3, default_retry_delay=5)
def process_chunk_task(
    self,
    chunk_info: dict[str, Any],
    file_path: str,
) -> dict[str, Any]:
    """
    Celery task: process a single chunk of the brain volume.
    Automatically retries on failure (up to 3 times).
    """
    worker_id = self.request.id or "unknown"
    agent_id = f"beta-worker-{worker_id[:8]}"

    worker = ChunkWorkerAgent(agent_id=agent_id, max_runtime_sec=90)
    result: ChunkWorkerResult = worker.process_chunk(chunk_info, file_path)

    if result.status == "failed":
        # Retry on failure
        try:
            raise self.retry(exc=Exception(result.error))
        except self.MaxRetriesExceededError:
            pass  # Return failed result after max retries

    return {
        "chunk_id": result.chunk_id,
        "agent_id": result.agent_id,
        "coords": result.coords,
        "shape": result.shape,
        "stats": result.stats,
        "anomalies": result.anomalies,
        "lesions": result.lesions,
        "processing_time_sec": result.processing_time_sec,
        "status": result.status,
        "error": result.error,
    }


@app.task
def health_check_task() -> dict[str, Any]:
    """Simple liveness check for Celery workers."""
    import os
    import socket

    return {
        "status": "ok",
        "hostname": socket.gethostname(),
        "pid": os.getpid(),
        "timestamp": time.time(),
    }
