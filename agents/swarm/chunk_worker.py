"""
chunk_worker.py — Chunk Worker Agent template for Team Beta.

Each instance of ChunkWorkerAgent processes one or more 10×10×10 voxel chunks
from a 3D brain volume. This is the core computational unit of the MapReduce swarm.

Usage:
    from agents.swarm.chunk_worker import ChunkWorkerAgent
    worker = ChunkWorkerAgent(agent_id="beta-worker-0427")
    result = worker.process_chunk(chunk_info, file_path)
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

import numpy as np


@dataclass
class ChunkWorkerResult:
    """Output from a single chunk worker run."""

    chunk_id: int
    agent_id: str
    coords: dict[str, int]
    shape: list[int]
    stats: dict[str, float]
    anomalies: list[dict[str, Any]] = field(default_factory=list)
    lesions: list[dict[str, Any]] = field(default_factory=list)
    processing_time_sec: float = 0.0
    status: str = "pending"
    error: str | None = None


class ChunkWorkerAgent:
    """
    A single chunk-processing agent in the MapReduce swarm.
    Processes assigned chunks independently; has no access to full volume.
    """

    def __init__(
        self,
        agent_id: str,
        max_runtime_sec: int = 30,
        max_tokens: int = 8000,
    ):
        self.agent_id = agent_id
        self.max_runtime_sec = max_runtime_sec
        self.max_tokens = max_tokens
        self.chunks_processed = 0
        self.total_voxels_processed = 0

    def process_chunk(
        self,
        chunk_info: dict[str, Any],
        file_path: str,
        healthy_path: str | None = None,
    ) -> ChunkWorkerResult:
        """
        Process a single chunk of the brain volume.
        If healthy_path is provided, uses EnhancedDetector for baseline comparison.
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
            self.chunks_processed += 1
            self.total_voxels_processed += chunk_data.size

            # ── STATISTICS ──
            stats = {
                "mean": float(np.mean(chunk_data)),
                "std": float(np.std(chunk_data)),
                "min": float(np.min(chunk_data)),
                "max": float(np.max(chunk_data)),
                "median": float(np.median(chunk_data)),
                "nonzero": int(np.count_nonzero(chunk_data)),
            }

            # ── GRADIENT ──
            grad = np.gradient(chunk_data)
            grad_mag = np.sqrt(sum(g**2 for g in grad))
            stats["gradient_mean"] = float(np.mean(grad_mag))
            stats["gradient_max"] = float(np.max(grad_mag))

            # ── ENHANCED DETECTION (baseline-aware) ──
            anomalies: list[dict[str, Any]] = []
            lesions: list[dict[str, Any]] = []

            if healthy_path and chunk_data.size > 0:
                from agents.swarm.enhanced_detector import EnhancedDetector

                # Reuse detector instance if cached
                if not hasattr(self, "_detector") or self._detector is None:
                    self._detector = EnhancedDetector(healthy_path)

                det_result = self._detector.analyze_chunk(chunk_data, coords)

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
                # Fallback: simple heuristic when no baseline
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
                            "chunk_mean": stats["mean"],
                        }
                    )

            elapsed = time.monotonic() - start
            if elapsed > self.max_runtime_sec:
                raise TimeoutError(
                    f"Chunk {chunk_id} exceeded {self.max_runtime_sec}s limit"
                )

            return ChunkWorkerResult(
                chunk_id=chunk_id,
                agent_id=self.agent_id,
                coords=coords,
                shape=list(chunk_data.shape),
                stats=stats,
                anomalies=anomalies,
                lesions=lesions,
                processing_time_sec=round(elapsed, 3),
                status="success",
            )

        except Exception as exc:
            return ChunkWorkerResult(
                chunk_id=chunk_id,
                agent_id=self.agent_id,
                coords=coords,
                shape=[0, 0, 0],
                stats={},
                processing_time_sec=round(time.monotonic() - start, 3),
                status="failed",
                error=str(exc),
            )

    def process_batch(
        self,
        chunks: list[dict[str, Any]],
        file_path: str,
    ) -> list[ChunkWorkerResult]:
        """Process multiple chunks sequentially (one worker, many chunks)."""
        return [self.process_chunk(c, file_path) for c in chunks]

    def get_status(self) -> dict[str, Any]:
        """Report agent status for health monitoring."""
        return {
            "agent_id": self.agent_id,
            "team": "beta-chunk-workers",
            "chunks_processed": self.chunks_processed,
            "total_voxels_processed": self.total_voxels_processed,
            "max_runtime_sec": self.max_runtime_sec,
            "alive": True,
        }


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python -m agents.swarm.chunk_worker <nifti_file> [chunk_id]")
        sys.exit(1)

    nifti_path = sys.argv[1]
    chunk_id = int(sys.argv[2]) if len(sys.argv) > 2 else 0

    # Demo chunk info
    demo_chunk = {
        "chunk_id": chunk_id,
        "coords": {
            "x_start": 0,
            "x_end": 10,
            "y_start": 0,
            "y_end": 10,
            "z_start": 0,
            "z_end": 10,
        },
        "shape": [10, 10, 10],
        "voxels": 1000,
    }

    worker = ChunkWorkerAgent(agent_id="beta-worker-demo")
    result = worker.process_chunk(demo_chunk, nifti_path)

    print(f"Status: {result.status}")
    print(f"Stats: {result.stats}")
    print(f"Lesions: {result.lesions}")
    print(f"Time: {result.processing_time_sec}s")
