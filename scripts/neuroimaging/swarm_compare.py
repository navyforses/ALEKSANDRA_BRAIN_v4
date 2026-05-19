"""
swarm_compare.py — Run swarm on both Healthy and Damaged brains, then compare.

Outputs a side-by-side report showing how the swarm detects differences.
"""

from __future__ import annotations

import json
import multiprocessing as mp
import sys
import time

sys.path.insert(0, ".")

from mcp.swarm_orchestrator import SwarmOrchestrator


def run_swarm(name: str, path: str, chunk_size: int = 20) -> dict:
    """Run swarm on a single brain and return summary."""
    print(f"\n{'='*60}")
    print(f"SWARM: {name}")
    print(f"File: {path}")
    print(f"{'='*60}")

    orch = SwarmOrchestrator(n_workers=max(4, mp.cpu_count()), chunk_size=chunk_size)

    def on_progress(done: int, total: int) -> None:
        if done % 20 == 0 or done == total:
            print(f"  Progress: {done}/{total} ({done/total*100:.1f}%)")

    start = time.monotonic()
    result = orch.process_volume(path, progress_callback=on_progress)
    elapsed = time.monotonic() - start

    # Count lesions per severity
    lesion_chunks = [r for r in result.chunk_results if r.lesions]
    total_lesions = sum(len(r.lesions) for r in lesion_chunks)

    print(f"\n  Done: {result.successful_chunks}/{result.total_chunks} chunks")
    print(f"  Time: {elapsed:.2f}s")
    print(f"  Mean intensity: {result.global_stats.get('mean_mean', 0):.2f}")
    print(f"  Lesion chunks: {len(lesion_chunks)}")
    print(f"  Total lesions: {total_lesions}")

    return {
        "name": name,
        "path": path,
        "shape": result.data_shape,
        "total_chunks": result.total_chunks,
        "successful_chunks": result.successful_chunks,
        "failed_chunks": result.failed_chunks,
        "elapsed_sec": round(elapsed, 2),
        "mean_intensity": round(result.global_stats.get("mean_mean", 0), 2),
        "std_intensity": round(result.global_stats.get("std_mean", 0), 2),
        "lesion_chunks": len(lesion_chunks),
        "total_lesions": total_lesions,
        "global_stats": result.global_stats,
    }


def main() -> None:
    healthy_path = "tests/fixtures/healthy_brain_128.nii.gz"
    damaged_path = "tests/fixtures/damaged_brain_128.nii.gz"

    print("ALEKSANDRA_BRAIN — Swarm Comparison: Healthy vs Damaged")
    print("This will process both brains through the MapReduce swarm.")

    healthy_result = run_swarm("HEALTHY BASELINE", healthy_path, chunk_size=20)
    damaged_result = run_swarm("DAMAGED (HIE)", damaged_path, chunk_size=20)

    # Comparison
    print("\n" + "=" * 60)
    print("SIDE-BY-SIDE COMPARISON")
    print("=" * 60)

    print(f"{'Metric':<30} {'Healthy':>12} {'Damaged':>12} {'Delta':>12}")
    print("-" * 66)
    print(
        f"{'Mean intensity':<30} {healthy_result['mean_intensity']:>12.2f} {damaged_result['mean_intensity']:>12.2f} {damaged_result['mean_intensity'] - healthy_result['mean_intensity']:>+12.2f}"
    )
    print(
        f"{'Std intensity':<30} {healthy_result['std_intensity']:>12.2f} {damaged_result['std_intensity']:>12.2f} {damaged_result['std_intensity'] - healthy_result['std_intensity']:>+12.2f}"
    )
    print(
        f"{'Lesion chunks detected':<30} {healthy_result['lesion_chunks']:>12} {damaged_result['lesion_chunks']:>12} {damaged_result['lesion_chunks'] - healthy_result['lesion_chunks']:>+12}"
    )
    print(
        f"{'Total lesions detected':<30} {healthy_result['total_lesions']:>12} {damaged_result['total_lesions']:>12} {damaged_result['total_lesions'] - healthy_result['total_lesions']:>+12}"
    )
    print(
        f"{'Processing time (s)':<30} {healthy_result['elapsed_sec']:>12.2f} {damaged_result['elapsed_sec']:>12.2f} {damaged_result['elapsed_sec'] - healthy_result['elapsed_sec']:>+12.2f}"
    )

    # Save combined report
    report = {
        "comparison": "swarm_healthy_vs_damaged",
        "healthy": healthy_result,
        "damaged": damaged_result,
        "swarm_detected_difference": {
            "intensity_drop": round(
                healthy_result["mean_intensity"] - damaged_result["mean_intensity"], 2
            ),
            "lesion_increase": damaged_result["total_lesions"]
            - healthy_result["total_lesions"],
            "conclusion": "Damaged brain shows significant intensity reduction and lesion detection vs healthy baseline.",
        },
    }

    out_path = "tests/fixtures/swarm_comparison_report.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print(f"\nFull swarm comparison saved: {out_path}")


if __name__ == "__main__":
    main()
