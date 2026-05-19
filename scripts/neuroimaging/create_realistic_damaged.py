"""
create_realistic_damaged.py — Generate HIE-damaged brain based on realistic anatomy.

Simulates Aleksandra's condition:
  - Diffuse cystic encephalomalacia (multiple cysts in WM)
  - Reduced white matter volume
  - Enlarged ventricles
  - Left hemisphere asymmetry
  - Preserved brainstem
"""

from __future__ import annotations

import os

import nibabel as nib
import numpy as np
from scipy import ndimage


def create_damaged_brain(
    shape: tuple[int, int, int] = (128, 128, 128),
    output_path: str = "tests/fixtures/realistic_damaged_128.nii.gz",
) -> str:
    """Generate damaged brain by modifying realistic healthy brain."""

    # First create base realistic brain
    from create_realistic_brain import create_realistic_brain

    healthy_path = "tests/fixtures/temp_healthy.nii.gz"
    create_realistic_brain(shape, output_path=healthy_path)

    img = nib.load(healthy_path)
    data = img.get_fdata().copy()

    sx, sy, sz = shape
    cx, cy, cz = sx // 2, sy // 2, sz // 2

    x = np.arange(sx) - cx
    y = np.arange(sy) - cy
    z = np.arange(sz) - cz
    X, Y, Z = np.meshgrid(x, y, z, indexing="ij")

    brain_mask = data > 15

    print("\nApplying HIE damage patterns...")

    # 1. DIFFUSE CYSTS in periventricular WM (classic HIE pattern)
    np.random.seed(42)
    n_cysts = 35

    for i in range(n_cysts):
        # Cysts cluster near ventricles and in WM
        cx_cyst = cx + np.random.normal(0, 18)
        cy_cyst = cy + np.random.normal(0, 15)
        cz_cyst = cz + np.random.normal(-5, 20)

        radius = np.random.uniform(2, 6)

        cyst = (
            ((X - (cx_cyst - cx)) / radius) ** 2
            + ((Y - (cy_cyst - cy)) / radius) ** 2
            + ((Z - (cz_cyst - cz)) / (radius * 0.8)) ** 2
        ) <= 1.0

        # Only affect WM (bright voxels)
        cyst &= (data > 100) & brain_mask
        data[cyst] = 8 + np.random.normal(0, 2, size=data[cyst].shape)

    print(f"  Added {n_cysts} cysts in white matter")

    # 2. ENLARGED VENTRICLES
    # Expand existing low-intensity regions
    ventricle_mask = data < 25
    ventricle_mask &= brain_mask

    # Dilate ventricles slightly
    ventricle_dilated = ndimage.binary_dilation(ventricle_mask, iterations=2)
    data[ventricle_dilated & brain_mask & (data > 30)] = 20.0

    print("  Enlarged ventricles")

    # 3. LEFT HEMISPHERE VOLUME LOSS (asymmetry)
    # Reduce left hemisphere (X < cx) intensity
    left_mask = (X < 0) & brain_mask & (data > 30)
    data[left_mask] *= 0.75  # Reduce intensity by 25%

    # Additional atrophy on left
    left_atrophy = (
        (X / (cx * 0.6)) ** 2 + (Y / (cy * 0.8)) ** 2 + ((Z + 5) / (cz * 0.7)) ** 2
    ) <= 1.0
    left_atrophy &= (X < 0) & brain_mask
    data[left_atrophy & (data > 40)] *= 0.6

    print("  Left hemisphere atrophy (25% volume loss)")

    # 4. REDUCED WM OVERALL
    # Global WM reduction
    wm_mask = data > 130
    # Randomly zero out some WM voxels
    wm_coords = np.argwhere(wm_mask)
    n_remove = int(len(wm_coords) * 0.25)
    remove_idx = np.random.choice(len(wm_coords), n_remove, replace=False)
    for idx in remove_idx:
        z, y, x = wm_coords[idx]
        data[z, y, x] = 40 + np.random.normal(0, 5)  # Become GM-like

    print(f"  Reduced WM by ~25% ({n_remove:,} voxels)")

    # 5. PRESERVED BRAINSTEM
    # Ensure brainstem stays intact
    brainstem = ((X / 6) ** 2 + ((Y + 2) / 5) ** 2 + ((Z - 22) / 12) ** 2) <= 1.0
    data[brainstem & (data > 0)] = np.clip(data[brainstem & (data > 0)] + 20, 0, 200)

    print("  Brainstem preserved")

    # 6. Final cleanup
    data = np.clip(data, 0, 400)
    data[~brain_mask] = 0.0
    data = ndimage.gaussian_filter(data, sigma=0.5)

    # Re-darken cysts after smoothing
    cyst_coords = np.argwhere(data < 15)
    for z, y, x in cyst_coords:
        if brain_mask[z, y, x]:
            data[z, y, x] = 8 + np.random.normal(0, 2)

    # Save
    affine = np.eye(4)
    affine[0, 0] = affine[1, 1] = affine[2, 2] = 1.0
    affine[:3, 3] = [-cx, -cy, -cz]

    img_out = nib.Nifti1Image(data, affine)
    img_out.header.set_xyzt_units(xyz="mm", t="sec")
    nib.save(img_out, output_path)

    # Stats
    total = int(brain_mask.sum())
    wm = int((data > 100).sum())
    gm = int(((data > 30) & (data <= 100)).sum())
    cysts = int((data < 20).sum())

    print(f"\nDAMAGED brain saved: {output_path}")
    print(f"  Total voxels: {total:,}")
    print(f"  WM: {wm:,} ({wm/total*100:.1f}%)")
    print(f"  GM: {gm:,} ({gm/total*100:.1f}%)")
    print(f"  Cysts/low intensity: {cysts:,}")
    print("  Asymmetry: Left hemisphere reduced")

    # Cleanup temp
    os.remove(healthy_path)

    return output_path


if __name__ == "__main__":
    create_damaged_brain()
