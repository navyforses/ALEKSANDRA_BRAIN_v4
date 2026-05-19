"""
test_swarm.py — Quick smoke test for the swarm orchestrator.
Runs SwarmOrchestrator on a test NIfTI and writes results to JSON.
"""

from __future__ import annotations

import multiprocessing as mp
import sys

sys.path.insert(0, ".")

from mcp.swarm_orchestrator import SwarmOrchestrator


def main() -> None:
    nifti_path = "tests/fixtures/test_brain_128.nii.gz"
    n_workers = max(4, mp.cpu_count())
    chunk_size = 10

    print(f"Testing swarm on: {nifti_path}")
    print(f"Workers: {n_workers}, Chunk size: {chunk_size}x{chunk_size}x{chunk_size}")

    orch = SwarmOrchestrator(n_workers=n_workers, chunk_size=chunk_size)

    def on_progress(done: int, total: int) -> None:
        if done % 50 == 0 or done == total:
            pct = done / total * 100
            print(f"  Progress: {done}/{total} ({pct:.1f}%)")

    result = orch.process_volume(nifti_path, progress_callback=on_progress)

    # Export
    out_path = nifti_path.replace(".nii.gz", "_swarm_result.json").replace(
        ".nii", "_swarm_result.json"
    )
    orch.export_result_json(result, out_path)

    # Summary
    print("\n=== SWARM RESULT ===")
    print(f"Shape: {result.data_shape}")
    print(f"Total chunks: {result.total_chunks}")
    print(f"Successful: {result.successful_chunks}")
    print(f"Failed: {result.failed_chunks}")
    print(f"Time: {result.total_processing_time_sec:.2f}s")
    print("Global stats:")
    for k, v in result.global_stats.items():
        print(f"  {k}: {v:.4f}")

    # Lesion summary
    total_lesions = sum(
        len(r.lesions) for r in result.chunk_results if r.status == "success"
    )
    print(f"\nTotal suspected lesions detected: {total_lesions}")

    print(f"\nFull results saved to: {out_path}")


if __name__ == "__main__":
    main()
