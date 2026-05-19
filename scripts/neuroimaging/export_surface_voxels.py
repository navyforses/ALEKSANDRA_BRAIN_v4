"""
export_surface_voxels.py — Export surface voxels with normals for web viewer.

Uses 6-connectivity to find surface voxels (voxels with at least one non-brain neighbor).
Computes normals from the outward direction to empty space.
Output: Inline JS with surface voxels only (much more brain-like than random sampling).
"""

from __future__ import annotations


import nibabel as nib
import numpy as np
from scipy import ndimage


def find_surface_voxels(data, threshold=20):
    """Find surface voxels using 6-connectivity."""
    mask = data > threshold

    # Erode by 1 to get inner voxels
    eroded = ndimage.binary_erosion(mask, structure=np.ones((3, 3, 3)))
    # Surface = mask minus eroded
    surface = mask & ~eroded

    return surface


def compute_surface_normals(data, surface_mask, threshold=20):
    """Compute outward-pointing normals for surface voxels."""
    mask = data > threshold

    # For each surface voxel, find the direction of the nearest non-brain voxel
    # Simple approach: use distance transform on inverted mask
    inv_dist = ndimage.distance_transform_edt(~mask)

    # Compute gradient of distance transform (points outward from brain)
    gy, gx, gz = np.gradient(inv_dist)

    # Normalize
    norm = np.sqrt(gx**2 + gy**2 + gz**2) + 1e-8
    gx /= norm
    gy /= norm
    gz /= norm

    return gx, gy, gz


def export_surface_js(
    nifti_path: str = "tests/fixtures/realistic_brain_128.nii.gz",
    output_path: str = "viewer/brain_surface.js",
    max_points: int = 12000,
):
    """Export surface voxels as inline JS."""
    print(f"Loading: {nifti_path}")
    img = nib.load(nifti_path)
    data = img.get_fdata()

    print("Finding surface voxels...")
    surface = find_surface_voxels(data)

    print("Computing normals...")
    gx, gy, gz = compute_surface_normals(data, surface)

    coords = np.argwhere(surface)
    intensities = data[surface]
    nx = gx[surface]
    ny = gy[surface]
    nz = gz[surface]

    print(f"Surface voxels: {len(coords):,}")

    # Downsample if needed
    if len(coords) > max_points:
        step = len(coords) // max_points
        indices = np.arange(0, len(coords), step)[:max_points]
        coords = coords[indices]
        intensities = intensities[indices]
        nx, ny, nz = nx[indices], ny[indices], nz[indices]

    # Build JS
    js_lines = ["const BRAIN_SURFACE = ["]
    for (z, y, x), intensity, nxv, nyv, nzv in zip(coords, intensities, nx, ny, nz):
        js_lines.append(
            f"  {{x:{x},y:{y},z:{z},i:{round(float(intensity),1)},nx:{round(float(nxv),3)},ny:{round(float(nyv),3)},nz:{round(float(nzv),3)}}},"
        )
    js_lines.append("];")

    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(js_lines))

    print(f"Saved {len(coords):,} surface voxels -> {output_path}")

    wm = np.sum(intensities > 100)
    gm = np.sum((intensities > 30) & (intensities <= 100))
    csf = np.sum(intensities <= 30)
    total = len(intensities)
    print(f"  WM: {wm} ({wm/total*100:.1f}%)")
    print(f"  GM: {gm} ({gm/total*100:.1f}%)")
    print(f"  CSF: {csf} ({csf/total*100:.1f}%)")


if __name__ == "__main__":
    export_surface_js()
