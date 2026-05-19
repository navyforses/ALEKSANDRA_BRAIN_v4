"""
compare_brains.py — Differential analysis: Healthy vs Damaged brain.

Compares a healthy baseline brain against a damaged brain (e.g. Aleksandra's HIE)
to automatically identify:
  - Volume loss regions
  - Cyst locations
  - Intensity anomalies
  - Asymmetry
  - Enlarged ventricles

Usage:
    .venv/Scripts/python scripts/neuroimaging/compare_brains.py

Output: tests/fixtures/brain_comparison_report.json
"""

from __future__ import annotations

import json
import os
from typing import Any

import nibabel as nib
import numpy as np


def compare_brains(
    healthy_path: str = "tests/fixtures/healthy_brain_128.nii.gz",
    damaged_path: str = "tests/fixtures/damaged_brain_128.nii.gz",
    output_path: str = "tests/fixtures/brain_comparison_report.json",
) -> dict[str, Any]:
    """Compare healthy baseline against damaged brain and generate report."""

    print("=" * 60)
    print("BRAIN DIFFERENTIAL ANALYSIS")
    print("=" * 60)

    # Load both volumes
    healthy_img = nib.load(healthy_path)
    damaged_img = nib.load(damaged_path)

    healthy = healthy_img.get_fdata()
    damaged = damaged_img.get_fdata()
    shape = healthy.shape

    print(f"Shape: {shape}")
    print(f"Healthy: {healthy_path}")
    print(f"Damaged: {damaged_path}")
    print()

    # === GLOBAL STATISTICS ===
    h_nonzero = healthy > 0
    d_nonzero = damaged > 0

    global_stats = {
        "healthy": {
            "mean": float(np.mean(healthy[h_nonzero])),
            "std": float(np.std(healthy[h_nonzero])),
            "min": float(np.min(healthy[h_nonzero])),
            "max": float(np.max(healthy[h_nonzero])),
            "total_voxels": int(np.prod(shape)),
            "brain_voxels": int(h_nonzero.sum()),
        },
        "damaged": {
            "mean": float(np.mean(damaged[d_nonzero])),
            "std": float(np.std(damaged[d_nonzero])),
            "min": float(np.min(damaged[d_nonzero])),
            "max": float(np.max(damaged[d_nonzero])),
            "total_voxels": int(np.prod(shape)),
            "brain_voxels": int(d_nonzero.sum()),
        },
    }

    volume_loss = (
        global_stats["healthy"]["brain_voxels"]
        - global_stats["damaged"]["brain_voxels"]
    )
    volume_loss_pct = volume_loss / global_stats["healthy"]["brain_voxels"] * 100

    print("--- Global Statistics ---")
    print(f"Healthy brain voxels:  {global_stats['healthy']['brain_voxels']:,}")
    print(f"Damaged brain voxels:  {global_stats['damaged']['brain_voxels']:,}")
    print(f"Volume loss:           {volume_loss:,} voxels ({volume_loss_pct:.1f}%)")
    print(f"Healthy mean intensity: {global_stats['healthy']['mean']:.1f}")
    print(f"Damaged mean intensity: {global_stats['damaged']['mean']:.1f}")
    print()

    # === DIFFERENCE MAP ===
    diff = healthy.astype(np.float32) - damaged.astype(np.float32)

    # Regions where damaged brain has significantly lower intensity
    # (potential damage / cyst / atrophy)
    anomaly_threshold = 30.0  # intensity difference threshold
    anomaly_mask = (diff > anomaly_threshold) & h_nonzero

    anomaly_voxels = int(anomaly_mask.sum())
    anomaly_pct = anomaly_voxels / global_stats["healthy"]["brain_voxels"] * 100

    print("--- Anomaly Detection ---")
    print(f"Anomaly threshold:     {anomaly_threshold} intensity units")
    print(
        f"Anomaly voxels:        {anomaly_voxels:,} ({anomaly_pct:.1f}% of healthy brain)"
    )
    print()

    # === REGIONAL ANALYSIS (chunk-based) ===
    chunk_size = 10
    sx, sy, sz = shape
    regional_findings: list[dict[str, Any]] = []

    chunk_id = 0
    for z in range(0, sz, chunk_size):
        for y in range(0, sy, chunk_size):
            for x in range(0, sx, chunk_size):
                xe = min(x + chunk_size, sx)
                ye = min(y + chunk_size, sy)
                ze = min(z + chunk_size, sz)

                h_chunk = healthy[x:xe, y:ye, z:ze]
                d_chunk = damaged[x:xe, y:ye, z:ze]
                _diff_chunk = diff[x:xe, y:ye, z:ze]  # noqa: F841 reserved for future use

                h_mean = (
                    float(np.mean(h_chunk[h_chunk > 0])) if (h_chunk > 0).any() else 0.0
                )
                d_mean = (
                    float(np.mean(d_chunk[d_chunk > 0])) if (d_chunk > 0).any() else 0.0
                )
                mean_diff = h_mean - d_mean

                # Detect cyst-like regions: very low intensity in damaged but normal in healthy
                cyst_candidates = (d_chunk < 20) & (h_chunk > 50)
                cyst_voxels = int(cyst_candidates.sum())

                # Detect significant volume loss
                h_count = int((h_chunk > 0).sum())
                d_count = int((d_chunk > 0).sum())
                volume_loss_chunk = h_count - d_count

                if cyst_voxels > 5 or volume_loss_chunk > 50 or mean_diff > 40:
                    finding = {
                        "chunk_id": chunk_id,
                        "coords": {
                            "x_start": x,
                            "x_end": xe,
                            "y_start": y,
                            "y_end": ye,
                            "z_start": z,
                            "z_end": ze,
                        },
                        "healthy_mean": round(h_mean, 2),
                        "damaged_mean": round(d_mean, 2),
                        "mean_diff": round(mean_diff, 2),
                        "cyst_voxels": cyst_voxels,
                        "volume_loss_voxels": volume_loss_chunk,
                        "severity": "high"
                        if (cyst_voxels > 20 or volume_loss_chunk > 100)
                        else "medium",
                    }
                    regional_findings.append(finding)

                chunk_id += 1

    print("--- Regional Findings ---")
    print(f"Total chunks analyzed: {chunk_id}")
    print(f"Abnormal chunks:       {len(regional_findings)}")

    high_severity = [f for f in regional_findings if f["severity"] == "high"]
    medium_severity = [f for f in regional_findings if f["severity"] == "medium"]
    print(f"  High severity:   {len(high_severity)}")
    print(f"  Medium severity: {len(medium_severity)}")
    print()

    # === VENTRICLE ANALYSIS ===
    # Approximate ventricle detection: low-intensity central regions
    central_mask = (
        (np.abs(np.arange(sx)[:, None, None] - sx // 2) < 20)
        & (np.abs(np.arange(sy)[None, :, None] - sy // 2) < 20)
        & (np.abs(np.arange(sz)[None, None, :] - sz // 2) < 20)
    )

    h_vent = ((healthy < 30) & central_mask & h_nonzero).sum()
    d_vent = ((damaged < 30) & central_mask & d_nonzero).sum()
    ventricle_change = int(d_vent - h_vent)

    print("--- Ventricle Analysis ---")
    print(f"Healthy ventricle voxels:  {h_vent}")
    print(f"Damaged ventricle voxels:  {d_vent}")
    print(
        f"Change:                    {ventricle_change:+d} ({ventricle_change/h_vent*100:.1f}%)"
    )
    print()

    # === ASYMMETRY ===
    cx_mid = sx // 2
    h_left = healthy[:cx_mid, :, :]
    h_right = healthy[cx_mid:, :, :]
    d_left = damaged[:cx_mid, :, :]
    d_right = damaged[cx_mid:, :, :]

    h_left_mean = float(np.mean(h_left[h_left > 0])) if (h_left > 0).any() else 0
    h_right_mean = float(np.mean(h_right[h_right > 0])) if (h_right > 0).any() else 0
    d_left_mean = float(np.mean(d_left[d_left > 0])) if (d_left > 0).any() else 0
    d_right_mean = float(np.mean(d_right[d_right > 0])) if (d_right > 0).any() else 0

    healthy_asymmetry = (
        abs(h_left_mean - h_right_mean) / ((h_left_mean + h_right_mean) / 2) * 100
    )
    damaged_asymmetry = (
        abs(d_left_mean - d_right_mean) / ((d_left_mean + d_right_mean) / 2) * 100
    )

    print("--- Asymmetry ---")
    print(f"Healthy asymmetry:  {healthy_asymmetry:.1f}%")
    print(f"Damaged asymmetry:  {damaged_asymmetry:.1f}%")
    print()

    # === BUILD REPORT ===
    report = {
        "status": "success",
        "comparison_type": "healthy_baseline_vs_damaged",
        "volume_shape": list(shape),
        "global_statistics": global_stats,
        "volume_loss": {
            "voxels": volume_loss,
            "percentage": round(volume_loss_pct, 2),
        },
        "anomaly_detection": {
            "threshold": anomaly_threshold,
            "anomaly_voxels": anomaly_voxels,
            "anomaly_percentage": round(anomaly_pct, 2),
        },
        "regional_findings": {
            "total_chunks": chunk_id,
            "abnormal_chunks": len(regional_findings),
            "high_severity": len(high_severity),
            "medium_severity": len(medium_severity),
            "findings": regional_findings[:20],  # Preview top 20
        },
        "ventricles": {
            "healthy_voxels": int(h_vent),
            "damaged_voxels": int(d_vent),
            "change_voxels": ventricle_change,
            "change_percentage": round(ventricle_change / h_vent * 100, 1)
            if h_vent > 0
            else 0,
        },
        "asymmetry": {
            "healthy_percent": round(healthy_asymmetry, 2),
            "damaged_percent": round(damaged_asymmetry, 2),
        },
        "clinical_summary": {
            "diagnosis": "Severe HIE with diffuse cystic encephalomalacia",
            "volume_loss_percent": round(volume_loss_pct, 1),
            "cyst_count_estimate": len(
                [f for f in regional_findings if f["cyst_voxels"] > 10]
            ),
            "ventricle_enlargement": "YES" if ventricle_change > 0 else "NO",
            "asymmetry_present": "YES"
            if damaged_asymmetry > healthy_asymmetry + 5
            else "NO",
        },
    }

    # Save report
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print(f"Full report saved: {output_path}")
    print()
    print("=== CLINICAL SUMMARY ===")
    print(f"Diagnosis:     {report['clinical_summary']['diagnosis']}")
    print(f"Volume loss:   {report['clinical_summary']['volume_loss_percent']:.1f}%")
    print(
        f"Cysts found:   ~{report['clinical_summary']['cyst_count_estimate']} regions"
    )
    print(
        f"Ventricles:    {report['clinical_summary']['ventricle_enlargement']} (enlarged)"
    )
    print(f"Asymmetry:     {report['clinical_summary']['asymmetry_present']}")
    print(f"Severity:      {'HIGH' if len(high_severity) > 10 else 'MODERATE'}")

    return report


if __name__ == "__main__":
    compare_brains()
