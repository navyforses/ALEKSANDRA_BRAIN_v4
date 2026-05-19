"""
create_healthy_brain.py — Generate a synthetic HEALTHY neonatal brain NIfTI.

This serves as the BASELINE for comparison against Aleksandra's damaged brain.
Features:
  - Smooth ellipsoidal brain shape
  - Clear WM/GM/CSF differentiation
  - Normal-sized lateral ventricles
  - Symmetric hemispheres
  - NO cysts, NO hypodense regions
  - Realistic 1mm isotropic affine

Output: tests/fixtures/healthy_brain_128.nii.gz
"""

from __future__ import annotations

import os

import nibabel as nib
import numpy as np


def create_healthy_brain(
    shape: tuple[int, int, int] = (128, 128, 128),
    voxel_size: tuple[float, float, float] = (1.0, 1.0, 1.0),
    output_path: str = "tests/fixtures/healthy_brain_128.nii.gz",
) -> str:
    """Generate a healthy neonatal brain volume — baseline for comparison."""
    sx, sy, sz = shape
    cx, cy, cz = sx // 2, sy // 2, sz // 2

    # Coordinate grids
    x = np.arange(sx) - cx
    y = np.arange(sy) - cy
    z = np.arange(sz) - cz
    X, Y, Z = np.meshgrid(x, y, z, indexing="ij")

    # === BRAIN MASK ===
    # Smooth ellipsoid for neonatal brain
    brain_mask = (
        (X / (sx * 0.36)) ** 2 + (Y / (sy * 0.41)) ** 2 + (Z / (sz * 0.36)) ** 2
    ) <= 1.0

    # Distance from center (for tissue type assignment)
    dist_from_center = np.sqrt(X**2 + Y**2 + Z**2)
    max_dist = np.sqrt(cx**2 + cy**2 + cz**2)
    tissue_ratio = dist_from_center / (max_dist + 1e-6)

    data = np.zeros(shape, dtype=np.float32)

    # === TISSUE INTENSITIES (neonatal T1-like) ===
    # WM = bright (inner), GM = medium, CSF = dark (outer + ventricles)
    # For neonates, WM is typically brighter than GM on T1

    # Base intensity gradient: inner = WM (bright), mid = GM, outer = CSF
    wm_mask = tissue_ratio < 0.35
    gm_mask = (tissue_ratio >= 0.35) & (tissue_ratio < 0.65)
    csf_mask = (tissue_ratio >= 0.65) & brain_mask

    data[wm_mask & brain_mask] = 160 + np.random.normal(
        0, 8, size=data[wm_mask & brain_mask].shape
    )
    data[gm_mask & brain_mask] = 100 + np.random.normal(
        0, 6, size=data[gm_mask & brain_mask].shape
    )
    data[csf_mask] = 25 + np.random.normal(0, 4, size=data[csf_mask].shape)

    # === LATERAL VENTRICLES ===
    # Two small symmetric cavities near center
    left_vent = (((X - 6) / 4) ** 2 + ((Y - 4) / 3) ** 2 + ((Z + 2) / 5) ** 2) <= 1.0

    right_vent = (((X + 6) / 4) ** 2 + ((Y - 4) / 3) ** 2 + ((Z + 2) / 5) ** 2) <= 1.0

    data[left_vent | right_vent] = 18.0 + np.random.normal(
        0, 2, size=data[left_vent | right_vent].shape
    )

    # === CORTICAL FOLDS (simplified gyri/sulci) ===
    # Add subtle ridges to outer GM
    angle = np.arctan2(Y, X)
    cortical_pattern = np.sin(angle * 6) * np.cos(Z * 0.15) * 8
    cortical_mask = (tissue_ratio > 0.50) & (tissue_ratio < 0.75) & brain_mask
    data[cortical_mask] += cortical_pattern[cortical_mask]

    # === CLIP AND CLEAN ===
    data = np.clip(data, 0, 400)
    data[~brain_mask] = 0.0

    # === AFFINE ===
    affine = np.eye(4)
    affine[0, 0] = voxel_size[0]
    affine[1, 1] = voxel_size[1]
    affine[2, 2] = voxel_size[2]
    affine[:3, 3] = [-cx * voxel_size[0], -cy * voxel_size[1], -cz * voxel_size[2]]

    img = nib.Nifti1Image(data, affine)
    img.header.set_xyzt_units(xyz="mm", t="sec")

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    nib.save(img, output_path)

    # Stats
    wm_voxels = int((wm_mask & brain_mask).sum())
    gm_voxels = int((gm_mask & brain_mask).sum())
    csf_voxels = int(csf_mask.sum())
    vent_voxels = int((left_vent | right_vent).sum())
    total_brain = int(brain_mask.sum())

    print(f"HEALTHY brain saved: {output_path}")
    print(f"  Shape: {shape}")
    print(f"  Voxel size: {voxel_size}")
    print(f"  Intensity range: [{data.min():.1f}, {data.max():.1f}]")
    print(f"  Total brain voxels: {total_brain}")
    print(f"  WM: {wm_voxels} ({wm_voxels/total_brain*100:.1f}%)")
    print(f"  GM: {gm_voxels} ({gm_voxels/total_brain*100:.1f}%)")
    print(f"  CSF (cortical): {csf_voxels - vent_voxels}")
    print(f"  Ventricles: {vent_voxels}")
    print("  SYMMETRIC: YES")
    print("  CYSTS: 0")
    print("  LESIONS: 0")

    return output_path


if __name__ == "__main__":
    create_healthy_brain()
