"""
export_brain_meshes.py — Export brain regions as surface meshes using Marching Cubes.

Uses scikit-image.measure.marching_cubes to extract realistic surfaces.
Output: JSON files for Three.js in viewer/meshes/
"""

from __future__ import annotations

import json
import os

import nibabel as nib
import numpy as np
from skimage.measure import marching_cubes


def export_mesh(data, mask, region_name, output_dir, level=50, step=1):
    """Extract mesh from binary mask using marching cubes."""
    print(f"  Extracting {region_name}...")

    # Downsample for performance if needed
    if step > 1:
        mask = mask[::step, ::step, ::step]

    if mask.sum() < 10:
        print(f"    SKIP: too few voxels ({mask.sum()})")
        return None

    try:
        verts, faces, normals, _ = marching_cubes(mask, level=0.5)

        # Scale back up
        verts = verts * step

        # Center
        verts = verts - np.mean(verts, axis=0)

        mesh_data = {
            "name": region_name,
            "vertices": verts.tolist(),
            "faces": faces.tolist(),
            "normals": normals.tolist(),
            "vertex_count": len(verts),
            "face_count": len(faces),
        }

        output_path = f"{output_dir}/{region_name}_mesh.json"
        with open(output_path, "w") as f:
            json.dump(mesh_data, f)

        print(f"    → {len(verts):,} verts, {len(faces):,} faces → {output_path}")
        return mesh_data

    except Exception as e:
        print(f"    ERROR: {e}")
        return None


def export_brain_meshes(
    nifti_path: str = "tests/fixtures/realistic_brain_128.nii.gz",
    output_dir: str = "viewer/meshes",
):
    """Export all brain region meshes."""
    os.makedirs(output_dir, exist_ok=True)

    print(f"Loading: {nifti_path}")
    img = nib.load(nifti_path)
    data = img.get_fdata()

    # Overall brain surface
    brain_mask = data > 5
    export_mesh(data, brain_mask, "brain", output_dir, step=2)

    # Tissue surfaces
    wm_mask = data > 130
    export_mesh(data, wm_mask, "white_matter", output_dir, step=2)

    gm_mask = (data > 50) & (data <= 130)
    export_mesh(data, gm_mask, "gray_matter", output_dir, step=2)

    # Ventricles (CSF)
    csf_mask = data < 35
    brain_csf = csf_mask & brain_mask
    export_mesh(data, brain_csf, "ventricles", output_dir, step=1)

    print(f"\nAll meshes exported to {output_dir}/")


if __name__ == "__main__":
    export_brain_meshes()
