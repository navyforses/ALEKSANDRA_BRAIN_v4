"""
create_test_nifti.py — Generate a synthetic brain NIfTI for swarm testing.

Simulates:
  - 128³ volume with an ellipsoidal "brain"
  - Cyst-like low-intensity regions (HIE / cystic encephalomalacia)
  - White/gray matter contrast
  - Gaussian noise
  - Realistic 1mm isotropic affine

Output: tests/fixtures/test_brain_128.nii.gz
"""

from __future__ import annotations

import os

import nibabel as nib
import numpy as np


def create_synthetic_brain(
    shape: tuple[int, int, int] = (128, 128, 128),
    voxel_size: tuple[float, float, float] = (1.0, 1.0, 1.0),
    output_path: str = "tests/fixtures/test_brain_128.nii.gz",
) -> str:
    """Generate a synthetic brain volume with cystic lesions."""
    sx, sy, sz = shape
    cx, cy, cz = sx // 2, sy // 2, sz // 2

    # Coordinate grids
    x = np.arange(sx) - cx
    y = np.arange(sy) - cy
    z = np.arange(sz) - cz
    X, Y, Z = np.meshgrid(x, y, z, indexing="ij")

    # Base brain: ellipsoid
    brain_mask = (
        (X / (sx * 0.35)) ** 2 + (Y / (sy * 0.40)) ** 2 + (Z / (sz * 0.35)) ** 2
    ) <= 1.0

    # Intensity map
    data = np.zeros(shape, dtype=np.float32)

    # CSF = dark, GM = mid, WM = bright
    # Distance from center as a proxy for tissue type
    dist_from_center = np.sqrt(X**2 + Y**2 + Z**2)
    max_dist = np.sqrt(cx**2 + cy**2 + cz**2)
    tissue_ratio = dist_from_center / (max_dist + 1e-6)

    # Inner = WM (bright), mid = GM (medium), outer = CSF (dark)
    data[brain_mask] = 80 + 120 * (1 - tissue_ratio[brain_mask])

    # Add ventricles (dark CSF cavities near center)
    ventricle_mask = (
        ((X - 8) / 6) ** 2 + ((Y - 5) / 5) ** 2 + ((Z + 2) / 7) ** 2
    ) <= 1.0
    data[ventricle_mask] = 15.0

    # Add cystic lesions (HIE simulation) — multiple small low-intensity spheres
    np.random.seed(42)
    n_cysts = 8
    for _ in range(n_cysts):
        cx_c = np.random.randint(cx - 25, cx + 25)
        cy_c = np.random.randint(cy - 30, cy + 30)
        cz_c = np.random.randint(cz - 25, cz + 25)
        radius = np.random.uniform(2.5, 6.0)
        cyst_mask = ((X - cx_c) ** 2 + (Y - cy_c) ** 2 + (Z - cz_c) ** 2) <= radius**2
        data[cyst_mask] = np.random.uniform(3.0, 12.0)

    # Add Gaussian noise
    noise = np.random.normal(0, 4.0, shape)
    data = data + noise
    data = np.clip(data, 0, 400)

    # Build NIfTI with realistic affine
    affine = np.eye(4)
    affine[0, 0] = voxel_size[0]
    affine[1, 1] = voxel_size[1]
    affine[2, 2] = voxel_size[2]
    affine[:3, 3] = [-cx * voxel_size[0], -cy * voxel_size[1], -cz * voxel_size[2]]

    img = nib.Nifti1Image(data, affine)
    img.header.set_xyzt_units(xyz="mm", t="sec")

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    nib.save(img, output_path)

    print(f"Synthetic brain saved: {output_path}")
    print(f"  Shape: {shape}")
    print(f"  Voxel size: {voxel_size}")
    print(f"  Intensity range: [{data.min():.1f}, {data.max():.1f}]")
    print(f"  Cyst regions: {n_cysts}")
    print(f"  Brain voxels: {int(brain_mask.sum())}")

    return output_path


if __name__ == "__main__":
    create_synthetic_brain()
