"""
export_voxel_data.py — Export voxel data as inline JS for web viewer.

Computes surface normals for better shading in point cloud visualization.
Downsamples for browser performance while preserving anatomical detail.
"""

from __future__ import annotations


import nibabel as nib
import numpy as np
from scipy import ndimage


def estimate_normals(data, mask):
    """Estimate surface normals from intensity gradient."""
    # Compute gradient in each direction
    gx = ndimage.sobel(data, axis=0)
    gy = ndimage.sobel(data, axis=1)
    gz = ndimage.sobel(data, axis=2)

    # Normalize
    norm = np.sqrt(gx**2 + gy**2 + gz**2) + 1e-8
    gx /= norm
    gy /= norm
    gz /= norm

    return gx, gy, gz


def export_voxel_js(
    nifti_path: str = "tests/fixtures/realistic_brain_128.nii.gz",
    output_path: str = "viewer/brain_data.js",
    max_points: int = 8000,
):
    """Export voxel data as inline JS array."""
    print(f"Loading: {nifti_path}")
    img = nib.load(nifti_path)
    data = img.get_fdata()

    # Extract surface voxels (exclude deep interior for efficiency)
    # Brain tissue mask
    tissue_mask = data > 20

    # Distance transform: how far from outside
    dist = ndimage.distance_transform_edt(tissue_mask)

    # Keep voxels near surface (0-4 voxels from edge) + some deep WM
    # This gives us the "shell" of the brain with internal structures
    surface_band = ((dist < 5) & tissue_mask) | ((data > 120) & tissue_mask)

    coords = np.argwhere(surface_band)
    intensities = data[surface_band]

    print(f"Surface band voxels: {len(coords):,}")

    # Compute normals
    gx, gy, gz = estimate_normals(data, tissue_mask)
    nx = gx[surface_band]
    ny = gy[surface_band]
    nz = gz[surface_band]

    # Downsample if too many
    if len(coords) > max_points:
        step = len(coords) // max_points
        indices = np.arange(0, len(coords), step)[:max_points]
        coords = coords[indices]
        intensities = intensities[indices]
        nx, ny, nz = nx[indices], ny[indices], nz[indices]

    # Build JS array
    js_lines = ["const BRAIN_VOXELS = ["]
    for (z, y, x), intensity, nxv, nyv, nzv in zip(coords, intensities, nx, ny, nz):
        js_lines.append(
            f"  {{x:{x},y:{y},z:{z},i:{round(float(intensity),1)},nx:{round(float(nxv),3)},ny:{round(float(nyv),3)},nz:{round(float(nzv),3)}}},"
        )
    js_lines.append("];")

    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(js_lines))

    print(f"Saved {len(coords):,} voxels -> {output_path}")

    # Print tissue stats
    wm = np.sum(intensities > 130)
    gm = np.sum((intensities > 40) & (intensities <= 130))
    csf = np.sum(intensities <= 40)
    print(f"  WM points: {wm} ({wm/len(intensities)*100:.1f}%)")
    print(f"  GM points: {gm} ({gm/len(intensities)*100:.1f}%)")
    print(f"  CSF points: {csf} ({csf/len(intensities)*100:.1f}%)")


if __name__ == "__main__":
    export_voxel_js()
