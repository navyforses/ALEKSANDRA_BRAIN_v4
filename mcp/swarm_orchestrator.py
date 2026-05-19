"""
swarm_orchestrator — MapReduce orchestration for ALEKSANDRA_BRAIN neuroimaging swarm.

Coordinates hundreds of chunk-worker agents to process a 3D brain volume in parallel.
Uses Python multiprocessing for local parallelism; designed to scale to Celery later.

Usage:
    from mcp.swarm_orchestrator import SwarmOrchestrator
    orch = SwarmOrchestrator(n_workers=100)
    result = orch.process_volume("/path/to/brain.nii.gz")
"""

from __future__ import annotations

import json
import multiprocessing as mp
import os
import time
from dataclasses import dataclass, field
from typing import Any, Callable

import numpy as np


@dataclass
class ChunkResult:
    """Result from a single chunk worker."""

    chunk_id: int
    agent_id: str
    coords: dict[str, int]
    shape: list[int]
    stats: dict[str, float]
    anomalies: list[dict[str, Any]] = field(default_factory=list)
    lesions: list[dict[str, Any]] = field(default_factory=list)
    processing_time_sec: float = 0.0
    status: str = "pending"  # pending | success | failed
    error: str | None = None


@dataclass
class SwarmResult:
    """Aggregated result from the entire swarm."""

    file_path: str
    data_shape: list[int]
    total_voxels: int
    chunk_size: int
    total_chunks: int
    active_workers: int
    successful_chunks: int
    failed_chunks: int
    total_processing_time_sec: float
    global_stats: dict[str, float]
    chunk_results: list[ChunkResult]
    lesion_mask_path: str | None = None
    report_path: str | None = None


def _process_single_chunk(
    chunk_info: dict[str, Any],
    file_path: str,
    worker_id: int,
    healthy_path: str | None = None,
) -> ChunkResult:
    """
    Worker function: processes one chunk of the 3D volume.
    If healthy_path is provided, uses EnhancedDetector for baseline comparison.
    Designed to run in a separate process.
    """
    start = time.monotonic()
    chunk_id = chunk_info["chunk_id"]
    coords = chunk_info["coords"]

    try:
        import nibabel as nib

        img = nib.load(file_path)
        data = img.get_fdata()

        x0, x1 = coords["x_start"], coords["x_end"]
        y0, y1 = coords["y_start"], coords["y_end"]
        z0, z1 = coords["z_start"], coords["z_end"]

        chunk_data = data[x0:x1, y0:y1, z0:z1]

        # === LOCAL STATISTICS ===
        stats = {
            "mean": float(np.mean(chunk_data)),
            "std": float(np.std(chunk_data)),
            "min": float(np.min(chunk_data)),
            "max": float(np.max(chunk_data)),
            "median": float(np.median(chunk_data)),
            "nonzero": int(np.count_nonzero(chunk_data)),
        }

        # === GRADIENT MAGNITUDE (edge detection) ===
        if chunk_data.size > 1:
            grad = np.gradient(chunk_data)
            grad_mag = np.sqrt(sum(g**2 for g in grad))
            stats["gradient_mean"] = float(np.mean(grad_mag))
            stats["gradient_max"] = float(np.max(grad_mag))

        # === ENHANCED DETECTION (baseline-aware) ===
        anomalies: list[dict[str, Any]] = []
        lesions: list[dict[str, Any]] = []

        if healthy_path and chunk_data.size > 0:
            from agents.swarm.enhanced_detector import EnhancedDetector

            detector = EnhancedDetector(healthy_path)
            det_result = detector.analyze_chunk(chunk_data, coords)

            if det_result["status"] == "success":
                lesions = det_result.get("lesions", [])
                anomalies = [
                    {
                        "type": "detector_" + r,
                        "severity": det_result["confidence"],
                        "score": det_result["score"],
                    }
                    for r in det_result.get("reasons", [])
                ]
        else:
            # Fallback heuristic when no baseline
            if stats["mean"] < 10.0 and stats["nonzero"] < (chunk_data.size * 0.3):
                lesions.append(
                    {
                        "type": "suspected_cyst",
                        "confidence": 0.6,
                        "center_voxel": [
                            x0 + (x1 - x0) // 2,
                            y0 + (y1 - y0) // 2,
                            z0 + (z1 - z0) // 2,
                        ],
                    }
                )

        return ChunkResult(
            chunk_id=chunk_id,
            agent_id=f"beta-worker-{worker_id:04d}",
            coords=coords,
            shape=list(chunk_data.shape),
            stats=stats,
            anomalies=anomalies,
            lesions=lesions,
            processing_time_sec=round(time.monotonic() - start, 3),
            status="success",
        )

    except Exception as exc:
        return ChunkResult(
            chunk_id=chunk_id,
            agent_id=f"beta-worker-{worker_id:04d}",
            coords=coords,
            shape=[0, 0, 0],
            stats={},
            processing_time_sec=round(time.monotonic() - start, 3),
            status="failed",
            error=str(exc),
        )


class SwarmOrchestrator:
    """
    MapReduce orchestrator for brain volume processing.
    Splits a NIfTI volume into chunks and distributes them across worker processes.
    """

    def __init__(
        self,
        n_workers: int | None = None,
        chunk_size: int = 10,
        healthy_path: str | None = None,
    ):
        self.n_workers = n_workers or max(4, mp.cpu_count())
        self.chunk_size = chunk_size
        self.healthy_path = healthy_path

    def _generate_chunks(self, shape: tuple[int, ...]) -> list[dict[str, Any]]:
        """Generate chunk metadata for a 3D volume."""
        sx, sy, sz = shape[:3]
        c = self.chunk_size
        chunks = []
        chunk_id = 0
        for z in range(0, sz, c):
            for y in range(0, sy, c):
                for x in range(0, sx, c):
                    xe = min(x + c, sx)
                    ye = min(y + c, sy)
                    ze = min(z + c, sz)
                    chunks.append(
                        {
                            "chunk_id": chunk_id,
                            "coords": {
                                "x_start": x,
                                "x_end": xe,
                                "y_start": y,
                                "y_end": ye,
                                "z_start": z,
                                "z_end": ze,
                            },
                            "shape": [xe - x, ye - y, ze - z],
                            "voxels": (xe - x) * (ye - y) * (ze - z),
                        }
                    )
                    chunk_id += 1
        return chunks

    def process_volume(
        self,
        file_path: str,
        progress_callback: Callable[[int, int], None] | None = None,
    ) -> SwarmResult:
        """
        Main entry point: load a NIfTI file and process all chunks in parallel.
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"NIfTI file not found: {file_path}")

        import nibabel as nib

        img = nib.load(file_path)
        data = img.get_fdata()
        shape = data.shape

        if len(shape) != 3:
            raise ValueError(f"Expected 3D data, got {len(shape)}D: {shape}")

        chunks = self._generate_chunks(shape)
        total_chunks = len(chunks)

        # Distribute chunks round-robin across workers
        # Each worker process will handle multiple chunks sequentially
        worker_chunks: list[list[dict[str, Any]]] = [[] for _ in range(self.n_workers)]
        for idx, chunk in enumerate(chunks):
            worker_chunks[idx % self.n_workers].append(chunk)

        start_time = time.monotonic()

        # === MAP PHASE: parallel processing ===
        all_results: list[ChunkResult] = []

        with mp.Pool(processes=self.n_workers) as pool:
            # Build async result handles
            async_results = []
            for worker_id, w_chunks in enumerate(worker_chunks):
                if not w_chunks:
                    continue
                # Each worker processes its assigned chunks
                for chunk in w_chunks:
                    ar = pool.apply_async(
                        _process_single_chunk,
                        (chunk, file_path, worker_id, self.healthy_path),
                    )
                    async_results.append(ar)

            # Collect results with progress
            completed = 0
            for ar in async_results:
                result = ar.get(timeout=120)  # 2 min per chunk max
                all_results.append(result)
                completed += 1
                if progress_callback:
                    progress_callback(completed, total_chunks)

        elapsed = time.monotonic() - start_time

        # === REDUCE PHASE: aggregate statistics ===
        successful = [r for r in all_results if r.status == "success"]
        failed = [r for r in all_results if r.status == "failed"]

        global_stats: dict[str, float] = {}
        if successful:
            for key in successful[0].stats:
                values = [r.stats[key] for r in successful if key in r.stats]
                if values:
                    global_stats[f"{key}_mean"] = float(np.mean(values))
                    global_stats[f"{key}_std"] = float(np.std(values))

        # Count lesions
        total_lesions = sum(len(r.lesions) for r in successful)
        global_stats["total_suspected_lesions"] = float(total_lesions)
        global_stats["total_chunks_processed"] = float(len(successful))
        global_stats["total_chunks_failed"] = float(len(failed))

        return SwarmResult(
            file_path=file_path,
            data_shape=list(shape),
            total_voxels=int(np.prod(shape)),
            chunk_size=self.chunk_size,
            total_chunks=total_chunks,
            active_workers=self.n_workers,
            successful_chunks=len(successful),
            failed_chunks=len(failed),
            total_processing_time_sec=round(elapsed, 2),
            global_stats=global_stats,
            chunk_results=all_results,
        )

    def export_result_json(self, result: SwarmResult, out_path: str) -> None:
        """Export a SwarmResult to JSON for downstream agents."""
        payload = {
            "file_path": result.file_path,
            "data_shape": result.data_shape,
            "total_voxels": result.total_voxels,
            "chunk_size": result.chunk_size,
            "total_chunks": result.total_chunks,
            "active_workers": result.active_workers,
            "successful_chunks": result.successful_chunks,
            "failed_chunks": result.failed_chunks,
            "total_processing_time_sec": result.total_processing_time_sec,
            "global_stats": result.global_stats,
            "chunk_summary": [
                {
                    "chunk_id": cr.chunk_id,
                    "agent_id": cr.agent_id,
                    "status": cr.status,
                    "coords": cr.coords,
                    "stats": cr.stats,
                    "lesions": cr.lesions,
                    "processing_time_sec": cr.processing_time_sec,
                }
                for cr in result.chunk_results
            ],
        }
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)


class CeleryOrchestrator:
    """
    Distributed MapReduce orchestrator using Celery + Redis.
    Submits chunks as Celery tasks and aggregates results asynchronously.
    """

    def __init__(self, chunk_size: int = 10):
        self.chunk_size = chunk_size
        # Import here to avoid import overhead when not using Celery
        from agents.swarm.celery_tasks import process_chunk_task

        self._process_chunk_task = process_chunk_task

    def _generate_chunks(self, shape: tuple[int, ...]) -> list[dict[str, Any]]:
        """Generate chunk metadata for a 3D volume."""
        sx, sy, sz = shape[:3]
        c = self.chunk_size
        chunks = []
        chunk_id = 0
        for z in range(0, sz, c):
            for y in range(0, sy, c):
                for x in range(0, sx, c):
                    xe = min(x + c, sx)
                    ye = min(y + c, sy)
                    ze = min(z + c, sz)
                    chunks.append(
                        {
                            "chunk_id": chunk_id,
                            "coords": {
                                "x_start": x,
                                "x_end": xe,
                                "y_start": y,
                                "y_end": ye,
                                "z_start": z,
                                "z_end": ze,
                            },
                            "shape": [xe - x, ye - y, ze - z],
                            "voxels": (xe - x) * (ye - y) * (ze - z),
                        }
                    )
                    chunk_id += 1
        return chunks

    def process_volume(
        self,
        file_path: str,
        progress_callback: Callable[[int, int], None] | None = None,
    ) -> SwarmResult:
        """
        Main entry point: submit all chunks as Celery tasks and collect results.
        Requires running Celery workers: celery -A agents.swarm.celery_app worker --pool=solo
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"NIfTI file not found: {file_path}")

        import nibabel as nib
        import numpy as np

        img = nib.load(file_path)
        data = img.get_fdata()
        shape = data.shape

        if len(shape) != 3:
            raise ValueError(f"Expected 3D data, got {len(shape)}D: {shape}")

        chunks = self._generate_chunks(shape)
        total_chunks = len(chunks)

        start_time = time.monotonic()

        # --- MAP PHASE: submit all chunks as Celery tasks ---
        async_results = []
        for chunk in chunks:
            ar = self._process_chunk_task.delay(chunk, file_path)
            async_results.append((chunk["chunk_id"], ar))

        # --- COLLECT PHASE: gather results ---
        all_results: list[ChunkResult] = []
        completed = 0

        for chunk_id, ar in async_results:
            try:
                raw = ar.get(timeout=120)
                cr = ChunkResult(
                    chunk_id=raw["chunk_id"],
                    agent_id=raw["agent_id"],
                    coords=raw["coords"],
                    shape=raw["shape"],
                    stats=raw["stats"],
                    anomalies=raw.get("anomalies", []),
                    lesions=raw.get("lesions", []),
                    processing_time_sec=raw["processing_time_sec"],
                    status=raw["status"],
                    error=raw.get("error"),
                )
            except Exception as exc:
                cr = ChunkResult(
                    chunk_id=chunk_id,
                    agent_id="celery-worker-failed",
                    coords={},
                    shape=[0, 0, 0],
                    stats={},
                    status="failed",
                    error=str(exc),
                )

            all_results.append(cr)
            completed += 1
            if progress_callback:
                progress_callback(completed, total_chunks)

        elapsed = time.monotonic() - start_time

        # --- REDUCE PHASE: aggregate statistics ---
        successful = [r for r in all_results if r.status == "success"]
        failed = [r for r in all_results if r.status == "failed"]

        global_stats: dict[str, float] = {}
        if successful:
            for key in successful[0].stats:
                values = [r.stats[key] for r in successful if key in r.stats]
                if values:
                    global_stats[f"{key}_mean"] = float(np.mean(values))
                    global_stats[f"{key}_std"] = float(np.std(values))

        total_lesions = sum(len(r.lesions) for r in successful)
        global_stats["total_suspected_lesions"] = float(total_lesions)
        global_stats["total_chunks_processed"] = float(len(successful))
        global_stats["total_chunks_failed"] = float(len(failed))

        return SwarmResult(
            file_path=file_path,
            data_shape=list(shape),
            total_voxels=int(np.prod(shape)),
            chunk_size=self.chunk_size,
            total_chunks=total_chunks,
            active_workers=len(async_results),  # One task per chunk
            successful_chunks=len(successful),
            failed_chunks=len(failed),
            total_processing_time_sec=round(elapsed, 2),
            global_stats=global_stats,
            chunk_results=all_results,
        )

    def export_result_json(self, result: SwarmResult, out_path: str) -> None:
        """Export a SwarmResult to JSON for downstream agents."""
        payload = {
            "file_path": result.file_path,
            "data_shape": result.data_shape,
            "total_voxels": result.total_voxels,
            "chunk_size": result.chunk_size,
            "total_chunks": result.total_chunks,
            "active_workers": result.active_workers,
            "successful_chunks": result.successful_chunks,
            "failed_chunks": result.failed_chunks,
            "total_processing_time_sec": result.total_processing_time_sec,
            "global_stats": result.global_stats,
            "chunk_summary": [
                {
                    "chunk_id": cr.chunk_id,
                    "agent_id": cr.agent_id,
                    "status": cr.status,
                    "coords": cr.coords,
                    "stats": cr.stats,
                    "lesions": cr.lesions,
                    "processing_time_sec": cr.processing_time_sec,
                }
                for cr in result.chunk_results
            ],
        }
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    # Quick smoke test
    import sys

    if len(sys.argv) < 2:
        print("Usage: python -m mcp.swarm_orchestrator <nifti_file>")
        sys.exit(1)

    nifti_path = sys.argv[1]
    orch = SwarmOrchestrator(n_workers=max(4, mp.cpu_count()), chunk_size=10)

    def on_progress(done: int, total: int) -> None:
        pct = done / total * 100
        print(f"\rProgress: {done}/{total} chunks ({pct:.1f}%)", end="", flush=True)

    print(f"Starting swarm on: {nifti_path}")
    result = orch.process_volume(nifti_path, progress_callback=on_progress)
    print("\n")

    print(f"Shape: {result.data_shape}")
    print(f"Total chunks: {result.total_chunks}")
    print(f"Successful: {result.successful_chunks}")
    print(f"Failed: {result.failed_chunks}")
    print(f"Time: {result.total_processing_time_sec:.2f}s")
    print(f"Global stats: {json.dumps(result.global_stats, indent=2)}")
