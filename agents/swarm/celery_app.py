"""
celery_app.py — Celery configuration for the ALEKSANDRA_BRAIN neuroimaging swarm.

Uses Redis as broker and result backend. Designed for local-only deployment
so PHI never leaves the family machine.

Usage:
    from agents.swarm.celery_app import app
    from agents.swarm.celery_tasks import process_chunk_task

    # Start worker:
    #   celery -A agents.swarm.celery_app worker --loglevel=info --pool=solo
"""

from __future__ import annotations

import os

from celery import Celery

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

app = Celery(
    "aleksandra_brain_swarm",
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=["agents.swarm.celery_tasks"],
)

# Task serialization
app.conf.task_serializer = "json"
app.conf.accept_content = ["json"]
app.conf.result_serializer = "json"
app.conf.result_expires = 3600  # 1 hour
app.conf.task_track_started = True

# Worker settings (local machine, modest defaults)
app.conf.worker_prefetch_multiplier = 1
app.conf.task_acks_late = (
    True  # Acknowledge after task completes (safer for long tasks)
)

# Time limits per task (seconds)
app.conf.task_time_limit = 120
app.conf.task_soft_time_limit = 90

# Result backend settings
app.conf.result_backend = REDIS_URL
app.conf.result_extended = True

print(f"[celery] Broker: {REDIS_URL}")
