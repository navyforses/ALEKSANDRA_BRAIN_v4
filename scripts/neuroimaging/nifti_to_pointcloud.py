"""
nifti_to_pointcloud.py — Convert NIfTI brain to JSON point cloud for 3D visualization.

Each non-zero voxel becomes one point in the cloud with color based on intensity.
Outputs a lightweight JSON for Three.js Points rendering.

Usage:
    .venv/Scripts/python scripts/neuroimaging/nifti_to_pointcloud.py \
        tests/fixtures/healthy_brain_128.nii.gz \
        tests/fixtures/healthy_brain_points.json
"""

from __future__ import annotations

import json
import sys

import nibabel as nib
import numpy as np


def nifti_to_pointcloud(
    nifti_path: str,
    output_path: str,
    downsample: int = 2,
    max_points: int = 200_000,
) -> dict:
    """Convert NIfTI to JSON point cloud with colors."""
    print(f"Loading: {nifti_path}")
    img = nib.load(nifti_path)
    data = img.get_fdata()
    shape = data.shape

    print(f"Shape: {shape}")
    print(f"Total voxels: {np.prod(shape):,}")

    # Find non-zero voxels
    mask = data > 0
    coords = np.argwhere(mask)  # (N, 3) array of [z, y, x] — nibabel order
    intensities = data[mask]

    print(f"Non-zero voxels: {len(coords):,}")

    # Downsample if too many
    if len(coords) > max_points * downsample:
        step = max(1, len(coords) // max_points)
        coords = coords[::step]
        intensities = intensities[::step]
        print(f"After downsample (step={step}): {len(coords):,}")

    # Color mapping based on intensity
    # Low = CSF (blue), Mid = GM (green), High = WM (red/white)
    def intensity_to_color(val: float) -> tuple[int, int, int]:
        if val < 30:
            # CSF — blue
            return (100, 150, 255)
        elif val < 80:
            # GM — green/cyan
            t = (val - 30) / 50
            return (int(50 + t * 50), int(150 + t * 100), int(150 + t * 50))
        elif val < 130:
            # WM — yellow/white
            t = (val - 80) / 50
            return (int(200 + t * 55), int(200 + t * 55), int(100 + t * 155))
        else:
            # Bright WM — white
            return (255, 255, 220)

    points = []
    for (z, y, x), intensity in zip(coords, intensities):
        r, g, b = intensity_to_color(float(intensity))
        points.append(
            {
                "x": int(x),
                "y": int(y),
                "z": int(z),
                "i": round(float(intensity), 2),
                "c": [r, g, b],
            }
        )

    result = {
        "metadata": {
            "source": nifti_path,
            "shape": list(shape),
            "total_points": len(points),
            "downsample": downsample,
        },
        "points": points,
    }

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False)

    print(f"Saved: {output_path}")
    print(f"Points: {len(points):,}")
    print(f"File size: ~{len(json.dumps(result)) / 1024 / 1024:.1f} MB")

    return result


if __name__ == "__main__":
    if len(sys.argv) < 3:
        # Default: convert both brains
        for name in ["healthy", "damaged"]:
            nifti_to_pointcloud(
                f"tests/fixtures/{name}_brain_128.nii.gz",
                f"tests/fixtures/{name}_brain_points.json",
            )
            print()
    else:
        nifti_to_pointcloud(sys.argv[1], sys.argv[2])
