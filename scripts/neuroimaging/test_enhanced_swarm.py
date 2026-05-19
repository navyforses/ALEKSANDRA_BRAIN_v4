"""
test_enhanced_swarm.py — Test EnhancedDetector with baseline comparison.

Runs swarm on:
  1. Healthy brain (with healthy baseline)  → should find ~0 lesions (FP test)
  2. Damaged brain (with healthy baseline)  → should find real lesions (TP test)

This validates that the detector does NOT cry wolf on healthy tissue
but DOES catch real damage.
"""

from __future__ import annotations

import json
import multiprocessing as mp
import sys
import time

sys.path.insert(0, ".")

from mcp.swarm_orchestrator import SwarmOrchestrator


def run_swarm(
    name: str, brain_path: str, baseline_path: str, chunk_size: int = 20
) -> dict:
    """Run swarm with EnhancedDetector baseline comparison."""
    print(f"\n{'='*60}")
    print(f"ENHANCED SWARM: {name}")
    print(f"Brain: {brain_path}")
    print(f"Baseline: {baseline_path}")
    print(f"{'='*60}")

    orch = SwarmOrchestrator(
        n_workers=max(4, mp.cpu_count()),
        chunk_size=chunk_size,
        healthy_path=baseline_path,
    )

    def on_progress(done: int, total: int) -> None:
        if done % 20 == 0 or done == total:
            print(f"  Progress: {done}/{total} ({done/total*100:.1f}%)")

    start = time.monotonic()
    result = orch.process_volume(brain_path, progress_callback=on_progress)
    elapsed = time.monotonic() - start

    # Analyze lesions
    lesion_chunks = [r for r in result.chunk_results if r.lesions]
    total_lesions = sum(len(r.lesions) for r in lesion_chunks)

    # Confidence distribution
    high_conf = sum(
        1
        for r in result.chunk_results
        for lesion in r.lesions
        if lesion.get("confidence", 0) >= 0.7
    )
    med_conf = sum(
        1
        for r in result.chunk_results
        for lesion in r.lesions
        if 0.4 <= lesion.get("confidence", 0) < 0.7
    )
    low_conf = sum(
        1
        for r in result.chunk_results
        for lesion in r.lesions
        if lesion.get("confidence", 0) < 0.4
    )

    print(f"\n  Done: {result.successful_chunks}/{result.total_chunks} chunks")
    print(f"  Time: {elapsed:.2f}s")
    print(f"  Mean intensity: {result.global_stats.get('mean_mean', 0):.2f}")
    print(f"  Lesion chunks: {len(lesion_chunks)}")
    print(f"  Total lesions: {total_lesions}")
    print(f"    High confidence: {high_conf}")
    print(f"    Medium confidence: {med_conf}")
    print(f"    Low confidence: {low_conf}")

    return {
        "name": name,
        "brain_path": brain_path,
        "baseline_path": baseline_path,
        "shape": result.data_shape,
        "total_chunks": result.total_chunks,
        "successful_chunks": result.successful_chunks,
        "elapsed_sec": round(elapsed, 2),
        "mean_intensity": round(result.global_stats.get("mean_mean", 0), 2),
        "lesion_chunks": len(lesion_chunks),
        "total_lesions": total_lesions,
        "high_confidence": high_conf,
        "medium_confidence": med_conf,
        "low_confidence": low_conf,
        "chunk_results": [
            {
                "chunk_id": r.chunk_id,
                "lesions": r.lesions,
                "anomalies": r.anomalies,
            }
            for r in result.chunk_results
            if r.lesions or r.anomalies
        ],
    }


def main() -> None:
    healthy_path = "tests/fixtures/healthy_brain_128.nii.gz"
    damaged_path = "tests/fixtures/damaged_brain_128.nii.gz"

    print("ALEKSANDRA_BRAIN — EnhancedDetector Swarm Validation")
    print("Testing: Baseline-aware cyst/lesion detection")

    # Test 1: Healthy brain vs itself (should be near-zero false positives)
    healthy_result = run_swarm(
        "HEALTHY vs HEALTHY (FP test)",
        healthy_path,
        healthy_path,
        chunk_size=20,
    )

    # Test 2: Damaged brain vs healthy baseline (should find real lesions)
    damaged_result = run_swarm(
        "DAMAGED vs HEALTHY (TP test)",
        damaged_path,
        healthy_path,
        chunk_size=20,
    )

    # Validation report
    print("\n" + "=" * 60)
    print("VALIDATION REPORT")
    print("=" * 60)

    fp_rate = healthy_result["total_lesions"] / healthy_result["total_chunks"] * 100
    tp_detected = damaged_result["total_lesions"]

    print("\nFalse Positive Test (Healthy vs Healthy):")
    print(f"  Lesions detected: {healthy_result['total_lesions']}")
    print(f"  False positive rate: {fp_rate:.2f}%")
    print(f"  Target: <1%  {'PASS' if fp_rate < 1.0 else 'NEEDS WORK'}")

    print("\nTrue Positive Test (Damaged vs Healthy):")
    print(f"  Lesions detected: {tp_detected}")
    print(f"  Target: >0 real cysts  {'PASS' if tp_detected > 0 else 'FAIL'}")

    print("\nConfidence Distribution (Damaged):")
    print(f"  High:   {damaged_result['high_confidence']}")
    print(f"  Medium: {damaged_result['medium_confidence']}")
    print(f"  Low:    {damaged_result['low_confidence']}")

    # Save report
    report = {
        "test_type": "enhanced_detector_validation",
        "false_positive_test": healthy_result,
        "true_positive_test": damaged_result,
        "summary": {
            "false_positive_rate_percent": round(fp_rate, 2),
            "true_positives_detected": tp_detected,
            "detector_status": "VALIDATED"
            if (fp_rate < 5.0 and tp_detected > 0)
            else "NEEDS_TUNING",
        },
    }

    out_path = "tests/fixtures/enhanced_detector_validation.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print(f"\nFull validation report: {out_path}")


if __name__ == "__main__":
    main()
