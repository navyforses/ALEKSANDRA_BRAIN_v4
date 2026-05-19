"""
test_celery_swarm.py — End-to-end test for Celery-based distributed swarm.

Prerequisites:
  1. Redis running: docker run -d -p 6379:6379 --name aleksandra-redis redis:alpine
  2. Celery worker running:
       .venv/Scripts/celery -A agents.swarm.celery_app worker --loglevel=info --pool=solo

Usage:
    .venv/Scripts/python scripts/neuroimaging/test_celery_swarm.py
"""

from __future__ import annotations

import sys
import time

sys.path.insert(0, ".")

from mcp.swarm_orchestrator import CeleryOrchestrator


def main() -> None:
    nifti_path = "tests/fixtures/test_brain_128.nii.gz"
    chunk_size = 10

    print("=" * 60)
    print("CELERY SWARM TEST")
    print("=" * 60)
    print(f"File: {nifti_path}")
    print(f"Chunk size: {chunk_size}x{chunk_size}x{chunk_size}")
    print()
    print("NOTE: Make sure Celery workers are running:")
    print("  .venv/Scripts/celery -A agents.swarm.celery_app worker --pool=solo")
    print()

    orch = CeleryOrchestrator(chunk_size=chunk_size)

    def on_progress(done: int, total: int) -> None:
        if done % 50 == 0 or done == total:
            pct = done / total * 100
            print(f"  Progress: {done}/{total} ({pct:.1f}%)")

    print("Submitting chunks to Celery workers...")
    start = time.monotonic()
    result = orch.process_volume(nifti_path, progress_callback=on_progress)
    elapsed = time.monotonic() - start

    # Export
    out_path = nifti_path.replace(".nii.gz", "_celery_swarm_result.json").replace(
        ".nii", "_celery_swarm_result.json"
    )
    orch.export_result_json(result, out_path)

    print("\n=== CELERY SWARM RESULT ===")
    print(f"Shape: {result.data_shape}")
    print(f"Total chunks: {result.total_chunks}")
    print(f"Successful: {result.successful_chunks}")
    print(f"Failed: {result.failed_chunks}")
    print(f"Processing time: {result.total_processing_time_sec:.2f}s")
    print(f"Wall-clock time: {elapsed:.2f}s")
    print("Global stats:")
    for k, v in result.global_stats.items():
        print(f"  {k}: {v:.4f}")

    total_lesions = sum(
        len(r.lesions) for r in result.chunk_results if r.status == "success"
    )
    print(f"\nTotal suspected lesions: {total_lesions}")
    print(f"\nFull results: {out_path}")

    # Health check
    print("\n--- Health Check ---")
    from agents.swarm.celery_tasks import health_check_task

    health = health_check_task.delay().get(timeout=10)
    print(f"Worker health: {health}")


if __name__ == "__main__":
    main()
