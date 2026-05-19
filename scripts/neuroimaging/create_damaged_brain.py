"""
create_damaged_brain.py — Generate a synthetic HIE-damaged brain (Aleksandra's profile).

Simulates:
  - Severe HIE (hypoxic-ischemic encephalopathy)
  - Diffuse cystic encephalomalacia (many cysts throughout brain)
  - White matter volume loss
  - Enlarged ventricles (hydrocephalus ex vacuo)
  - Asymmetry between hemispheres
  - Cortical thinning

This is based on Aleksandra's actual diagnosis: severe HIE, diffuse cystic
encephalomalacia, preserved brainstem.

Output: tests/fixtures/damaged_brain_128.nii.gz
"""

from __future__ import annotations

import os

import nibabel as nib
import numpy as np


def create_damaged_brain(
    shape: tuple[int, int, int] = (128, 128, 128),
    voxel_size: tuple[float, float, float] = (1.0, 1.0, 1.0),
    output_path: str = "tests/fixtures/damaged_brain_128.nii.gz",
) -> str:
    """Generate a brain with HIE + diffuse cystic encephalomalacia."""
    sx, sy, sz = shape
    cx, cy, cz = sx // 2, sy // 2, sz // 2

    # Coordinate grids
    x = np.arange(sx) - cx
    y = np.arange(sy) - cy
    z = np.arange(sz) - cz
    X, Y, Z = np.meshgrid(x, y, z, indexing="ij")

    # === BRAIN MASK (slightly smaller than healthy due to atrophy) ===
    brain_mask = (
        (X / (sx * 0.34)) ** 2 + (Y / (sy * 0.39)) ** 2 + (Z / (sz * 0.34)) ** 2
    ) <= 1.0

    dist_from_center = np.sqrt(X**2 + Y**2 + Z**2)
    max_dist = np.sqrt(cx**2 + cy**2 + cz**2)
    tissue_ratio = dist_from_center / (max_dist + 1e-6)

    data = np.zeros(shape, dtype=np.float32)

    # === TISSUES (damaged — reduced WM, thinner GM) ===
    wm_mask = tissue_ratio < 0.28  # WM reduced
    gm_mask = (tissue_ratio >= 0.28) & (tissue_ratio < 0.60)  # GM thinner
    csf_mask = (tissue_ratio >= 0.60) & brain_mask

    # Damaged WM: lower intensity, more variable
    data[wm_mask & brain_mask] = 110 + np.random.normal(
        0, 15, size=data[wm_mask & brain_mask].shape
    )
    # Damaged GM: lower intensity
    data[gm_mask & brain_mask] = 70 + np.random.normal(
        0, 10, size=data[gm_mask & brain_mask].shape
    )
    # Expanded CSF
    data[csf_mask] = 20 + np.random.normal(0, 4, size=data[csf_mask].shape)

    # === ENLARGED VENTRICLES (hydrocephalus ex vacuo) ===
    # Much larger than healthy — brain tissue loss creates space
    left_vent = (((X - 8) / 7) ** 2 + ((Y - 4) / 5) ** 2 + ((Z + 3) / 8) ** 2) <= 1.0

    right_vent = (((X + 8) / 7) ** 2 + ((Y - 4) / 5) ** 2 + ((Z + 3) / 8) ** 2) <= 1.0

    data[left_vent | right_vent] = 12.0 + np.random.normal(
        0, 2, size=data[left_vent | right_vent].shape
    )

    # === DIFFUSE CYSTIC ENCEPHALOMALACIA ===
    # Many cysts of varying sizes scattered throughout WM and deep GM
    np.random.seed(42)
    n_cysts = 45  # Many cysts = diffuse pattern

    for i in range(n_cysts):
        # Random position within brain
        cx_c = np.random.randint(cx - 30, cx + 30)
        cy_c = np.random.randint(cy - 35, cy + 35)
        cz_c = np.random.randint(cz - 30, cz + 30)
        radius = np.random.uniform(1.5, 7.0)

        cyst_mask = ((X - cx_c) ** 2 + (Y - cy_c) ** 2 + (Z - cz_c) ** 2) <= radius**2

        # Cyst intensity: near-CSF
        cyst_intensity = np.random.uniform(5.0, 18.0)
        data[cyst_mask & brain_mask] = cyst_intensity

    # === ASYMMETRY ===
    # Left hemisphere more damaged than right (common in HIE)
    left_damage_mask = (X < 0) & brain_mask & (tissue_ratio < 0.5)
    data[left_damage_mask] *= 0.75  # 25% intensity reduction on left

    # === CORTICAL THINNING ===
    # Reduced cortical thickness = less GM at periphery
    thin_mask = (tissue_ratio > 0.50) & (tissue_ratio < 0.65) & brain_mask
    data[thin_mask] *= 0.60

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

    # Count cysts for stats
    cyst_voxels = 0
    for i in range(n_cysts):
        cx_c = np.random.randint(cx - 30, cx + 30)
        cy_c = np.random.randint(cy - 35, cy + 35)
        cz_c = np.random.randint(cz - 30, cz + 30)
        radius = np.random.uniform(1.5, 7.0)
        cyst_mask = ((X - cx_c) ** 2 + (Y - cy_c) ** 2 + (Z - cz_c) ** 2) <= radius**2
        cyst_voxels += int((cyst_mask & brain_mask).sum())

    total_brain = int(brain_mask.sum())
    wm_voxels = int((wm_mask & brain_mask).sum())
    gm_voxels = int((gm_mask & brain_mask).sum())
    vent_voxels = int((left_vent | right_vent).sum())

    print(f"DAMAGED brain saved: {output_path}")
    print(f"  Shape: {shape}")
    print(f"  Voxel size: {voxel_size}")
    print(f"  Intensity range: [{data.min():.1f}, {data.max():.1f}]")
    print(f"  Total brain voxels: {total_brain}")
    print(f"  WM: {wm_voxels} ({wm_voxels/total_brain*100:.1f}%) — REDUCED")
    print(f"  GM: {gm_voxels} ({gm_voxels/total_brain*100:.1f}%) — THINNED")
    print(f"  Ventricles: {vent_voxels} — ENLARGED")
    print(f"  Cyst count: {n_cysts} (diffuse)")
    print(f"  Cyst voxels: {cyst_voxels}")
    print("  ASYMMETRY: Left hemisphere reduced 25%")
    print("  DIAGNOSIS: Severe HIE + diffuse cystic encephalomalacia")

    return output_path


if __name__ == "__main__":
    create_damaged_brain()
