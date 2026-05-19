"""
create_realistic_brain.py — Generate an anatomically-informed synthetic neonatal brain.

Key improvements over simple ellipsoid:
  - Gyri/sulci pattern on cortical surface (realistic folding)
  - Proper ventricular system (lateral ventricles with horns)
  - Corpus callosum, thalamus, basal ganglia
  - Cerebellum with folia pattern
  - Brainstem (pons, medulla)
  - Asymmetric left/right hemispheres (normal slight asymmetry)

Output: tests/fixtures/realistic_brain_128.nii.gz
"""

from __future__ import annotations

import os

import nibabel as nib
import numpy as np
from scipy import ndimage


def create_realistic_brain(
    shape: tuple[int, int, int] = (128, 128, 128),
    voxel_size: tuple[float, float, float] = (1.0, 1.0, 1.0),
    output_path: str = "tests/fixtures/realistic_brain_128.nii.gz",
) -> str:
    """Generate an anatomically-informed neonatal brain."""
    sx, sy, sz = shape
    cx, cy, cz = sx // 2, sy // 2, sz // 2

    x = np.arange(sx) - cx
    y = np.arange(sy) - cy
    z = np.arange(sz) - cz
    X, Y, Z = np.meshgrid(x, y, z, indexing="ij")

    data = np.zeros(shape, dtype=np.float32)

    # ==== 1. BASE BRAIN SHAPE (modified superellipsoid with asymmetry) ====
    # Anterior-posterior is longer than superior-inferior
    # Left-right slight asymmetry (normal)

    a, b, c = sx * 0.38, sy * 0.44, sz * 0.35

    # Asymmetry factor: left hemisphere slightly larger (normal)
    asym_x = np.where(X < 0, 1.02, 0.98)

    base_shape = ((X / (a * asym_x)) ** 2 + (Y / b) ** 2 + (Z / c) ** 2) <= 1.0

    # Flatten bottom for cerebellum/brainstem
    base_shape &= Z > -cz * 0.85

    # Frontal poles extend forward
    frontal_extension = (
        (X / (a * 0.7)) ** 2
        + ((Y - cy * 0.3) / (b * 0.5)) ** 2
        + ((Z - cz * 0.1) / (c * 0.6)) ** 2
    ) <= 1.0

    # Occipital pole extends back
    occipital_extension = (
        (X / (a * 0.5)) ** 2
        + ((Y + cy * 0.4) / (b * 0.4)) ** 2
        + ((Z + cz * 0.15) / (c * 0.55)) ** 2
    ) <= 1.0

    brain_mask = base_shape | frontal_extension | occipital_extension

    # ==== 2. GYRI / SULCI PATTERN ====
    # Realistic cortical folding using multiple spatial frequencies
    angle = np.arctan2(Y, X)
    _radius = np.sqrt(X**2 + Y**2)  # noqa: F841 reserved for radial-distance variants

    # Primary sulci (major folds)
    sulci_1 = np.sin(angle * 3 + Z * 0.08) * np.cos(Z * 0.12) * 12
    # Secondary sulci (finer folds)
    sulci_2 = np.sin(angle * 7 + Y * 0.15) * np.cos(X * 0.1) * 6
    # Tertiary (finest)
    sulci_3 = np.sin(angle * 12 + Z * 0.2) * 3

    cortical_depth = sulci_1 + sulci_2 + sulci_3

    # Apply folding to outer surface
    # Regions where cortical_depth > threshold = sulcus (indentation)
    dist_from_center = np.sqrt(X**2 + Y**2 + Z**2)
    normalized_dist = dist_from_center / np.sqrt(cx**2 + cy**2 + cz**2)

    # Adjust brain mask with sulci (remove voxels where sulcus cuts deep)
    sulcus_mask = (
        (cortical_depth > 8) & (normalized_dist > 0.55) & (normalized_dist < 0.85)
    )
    brain_mask &= ~sulcus_mask

    # ==== 3. VENTRICULAR SYSTEM ====
    # Lateral ventricles: C-shaped, extending into frontal, temporal, occipital horns

    # Body of lateral ventricles (central, superior)
    lv_body = (((X - 5) / 5) ** 2 + ((Y - 2) / 4) ** 2 + ((Z + 8) / 6) ** 2) <= 1.0

    lv_body_right = (
        ((X + 5) / 5) ** 2 + ((Y - 2) / 4) ** 2 + ((Z + 8) / 6) ** 2
    ) <= 1.0

    # Frontal horns (extend anteriorly and slightly down)
    lv_frontal = (((X - 5) / 3) ** 2 + ((Y - 12) / 8) ** 2 + ((Z + 3) / 4) ** 2) <= 1.0

    lv_frontal_right = (
        ((X + 5) / 3) ** 2 + ((Y - 12) / 8) ** 2 + ((Z + 3) / 4) ** 2
    ) <= 1.0

    # Temporal horns (extend down and back)
    lv_temporal = (((X - 12) / 4) ** 2 + ((Y + 2) / 3) ** 2 + ((Z - 8) / 7) ** 2) <= 1.0

    lv_temporal_right = (
        ((X + 12) / 4) ** 2 + ((Y + 2) / 3) ** 2 + ((Z - 8) / 7) ** 2
    ) <= 1.0

    # Occipital horns (extend posteriorly)
    lv_occipital = (
        ((X - 3) / 3) ** 2 + ((Y + 10) / 5) ** 2 + ((Z + 5) / 4) ** 2
    ) <= 1.0

    lv_occipital_right = (
        ((X + 3) / 3) ** 2 + ((Y + 10) / 5) ** 2 + ((Z + 5) / 4) ** 2
    ) <= 1.0

    # Third ventricle (thin slit between thalami)
    third_vent = ((abs(X) / 1.5) ** 2 + ((Y - 1) / 6) ** 2 + ((Z + 6) / 5) ** 2) <= 1.0

    # Fourth ventricle (diamond shape, anterior to cerebellum)
    fourth_vent = ((X / 3) ** 2 + ((Y + 2) / 4) ** 2 + ((Z - 18) / 5) ** 2) <= 1.0

    all_ventricles = (
        lv_body
        | lv_body_right
        | lv_frontal
        | lv_frontal_right
        | lv_temporal
        | lv_temporal_right
        | lv_occipital
        | lv_occipital_right
        | third_vent
        | fourth_vent
    )

    brain_mask &= ~all_ventricles

    # ==== 4. DEEP GRAY MATTER STRUCTURES ====

    # Thalamus (paired, central, superior to brainstem)
    thalamus_left = (
        ((X - 7) / 5) ** 2 + ((Y - 2) / 4) ** 2 + ((Z + 2) / 5) ** 2
    ) <= 1.0

    thalamus_right = (
        ((X + 7) / 5) ** 2 + ((Y - 2) / 4) ** 2 + ((Z + 2) / 5) ** 2
    ) <= 1.0

    # Lentiform nucleus (putamen + globus pallidus) — lateral to thalamus
    lentiform_left = (
        ((X - 16) / 4) ** 2 + ((Y - 2) / 5) ** 2 + ((Z + 1) / 5) ** 2
    ) <= 1.0

    lentiform_right = (
        ((X + 16) / 4) ** 2 + ((Y - 2) / 5) ** 2 + ((Z + 1) / 5) ** 2
    ) <= 1.0

    # Caudate nucleus (C-shaped, wrapping around thalamus)
    caudate_left = (
        ((X - 12) / 3) ** 2 + ((Y - 8) / 6) ** 2 + ((Z + 6) / 4) ** 2
    ) <= 1.0

    caudate_right = (
        ((X + 12) / 3) ** 2 + ((Y - 8) / 6) ** 2 + ((Z + 6) / 4) ** 2
    ) <= 1.0

    deep_gray = (
        thalamus_left
        | thalamus_right
        | lentiform_left
        | lentiform_right
        | caudate_left
        | caudate_right
    )

    # ==== 5. CORPUS CALLOSUM ====
    # White matter tract connecting hemispheres, arched shape
    cc_body = ((X / 12) ** 2 + ((Y - 1) / 18) ** 2 + ((Z + 10) / 4) ** 2) <= 1.0

    cc_genu = (((X) / 8) ** 2 + ((Y - 16) / 5) ** 2 + ((Z + 7) / 4) ** 2) <= 1.0

    cc_splenium = (((X) / 9) ** 2 + ((Y + 14) / 5) ** 2 + ((Z + 8) / 4) ** 2) <= 1.0

    corpus_callosum = cc_body | cc_genu | cc_splenium

    # ==== 6. CEREBELLUM ====
    # Two hemispheres + vermis, with folia pattern
    cerebellum_left = (
        ((X - 12) / 10) ** 2 + ((Y + 18) / 8) ** 2 + ((Z - 20) / 10) ** 2
    ) <= 1.0

    cerebellum_right = (
        ((X + 12) / 10) ** 2 + ((Y + 18) / 8) ** 2 + ((Z - 20) / 10) ** 2
    ) <= 1.0

    cerebellum_vermis = (
        (X / 3) ** 2 + ((Y + 20) / 5) ** 2 + ((Z - 18) / 8) ** 2
    ) <= 1.0

    cerebellum = cerebellum_left | cerebellum_right | cerebellum_vermis

    # Cerebellar folia (fine parallel folds)
    cb_folia = np.sin((Y + 20) * 0.8) * np.cos((Z + 18) * 0.3) * 4
    cb_sulci = (cb_folia > 2) & cerebellum
    cerebellum &= ~cb_sulci

    # ==== 7. BRAINSTEM ====
    # Midbrain, pons, medulla (bottom to top in our Z coords)

    # Midbrain (top of brainstem)
    midbrain = ((X / 5) ** 2 + ((Y + 2) / 4) ** 2 + ((Z - 12) / 5) ** 2) <= 1.0

    # Pons (bulging anteriorly)
    pons = (((X) / 6) ** 2 + ((Y + 2) / 5) ** 2 + ((Z - 20) / 6) ** 2) <= 1.0

    # Pons bulge
    pons_bulge = (((X) / 8) ** 2 + ((Y - 3) / 4) ** 2 + ((Z - 20) / 5) ** 2) <= 1.0

    # Medulla (tapering inferiorly)
    medulla = ((X / 4) ** 2 + ((Y + 2) / 3) ** 2 + ((Z - 28) / 7) ** 2) <= 1.0

    brainstem = midbrain | pons | pons_bulge | medulla

    # ==== 8. COMBINE ALL STRUCTURES ====
    full_brain = brain_mask | cerebellum | brainstem

    # Internal capsule (white matter lateral to thalamus) — define before wm_mask
    ic_left = (((X - 11) / 2) ** 2 + ((Y - 2) / 3) ** 2 + ((Z + 1) / 4) ** 2) <= 1.0

    ic_right = (((X + 11) / 2) ** 2 + ((Y - 2) / 3) ** 2 + ((Z + 1) / 4) ** 2) <= 1.0

    # Cerebellar white matter — define before wm_mask
    cb_wm = cerebellum & (np.sqrt((X - 12) ** 2 + (Y + 18) ** 2 + (Z - 20) ** 2) < 5)
    cb_wm |= cerebellum & (np.sqrt((X + 12) ** 2 + (Y + 18) ** 2 + (Z - 20) ** 2) < 5)

    # ==== 9. TISSUE CLASSIFICATION ====

    # Initialize with CSF background
    data[full_brain] = 20.0

    # White matter (inner, corpus callosum, cerebellar white matter)
    # WM = deep white matter only, NOT all central regions
    # More GM in neonates than adults
    wm_mask = (
        ((normalized_dist < 0.28) & brain_mask & ~deep_gray & ~all_ventricles)
        | corpus_callosum
        | ic_left
        | ic_right
        | cb_wm
    )

    # Gray matter (cortex, deep gray, cerebellar cortex)
    # GM forms thicker cortical ribbon in neonates
    gm_mask = (
        (normalized_dist >= 0.28)
        & (normalized_dist < 0.75)
        & brain_mask
        & ~wm_mask
        & ~all_ventricles
        & ~sulcus_mask
    )

    # Deep gray matter
    gm_mask |= deep_gray

    # Cerebellar cortex (outer shell)
    cb_cortex = cerebellum & (
        np.sqrt((X - np.sign(X) * 12) ** 2 + (Y + 18) ** 2 + (Z - 20) ** 2) > 4
    )
    gm_mask |= cb_cortex

    # Brainstem = GM/WM mix, slightly darker
    brainstem_mask = brainstem

    # CSF (surface, sulci, ventricles)
    csf_mask = ((normalized_dist >= 0.78) & brain_mask) | sulcus_mask | all_ventricles

    # ==== 10. ASSIGN INTENSITIES (neonatal T1-like) ====
    # Neonatal T1: WM brighter than GM (opposite of adult!)

    np.random.seed(42)

    data[wm_mask] = 170 + np.random.normal(0, 7, size=data[wm_mask].shape)
    data[gm_mask] = 110 + np.random.normal(0, 6, size=data[gm_mask].shape)
    data[brainstem_mask] = 95 + np.random.normal(0, 5, size=data[brainstem_mask].shape)
    data[csf_mask] = 18 + np.random.normal(0, 3, size=data[csf_mask].shape)
    data[cerebellum & ~cb_cortex & ~cb_wm] = 100 + np.random.normal(
        0, 5, size=data[cerebellum & ~cb_cortex & ~cb_wm].shape
    )

    # Corpus callosum brightest
    data[corpus_callosum] = 185 + np.random.normal(
        0, 5, size=data[corpus_callosum].shape
    )

    # ==== 11. SMOOTH AND CLEAN ====
    data = np.clip(data, 0, 400)
    data[~full_brain] = 0.0

    # Slight Gaussian smooth for realistic tissue boundaries
    data = ndimage.gaussian_filter(data, sigma=0.6)

    # Ensure ventricles stay dark after smoothing
    data[all_ventricles] = 15 + np.random.normal(0, 2, size=data[all_ventricles].shape)
    data[all_ventricles] = np.clip(data[all_ventricles], 0, 400)

    # ==== 12. AFFINE ====
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
    total = int(full_brain.sum())
    wm_voxels = int(wm_mask.sum())
    gm_voxels = int(gm_mask.sum())
    csf_voxels = int(csf_mask.sum())
    vent_voxels = int(all_ventricles.sum())
    cb_voxels = int(cerebellum.sum())
    bs_voxels = int(brainstem.sum())

    print(f"REALISTIC brain saved: {output_path}")
    print(f"  Shape: {shape}")
    print(f"  Total brain voxels: {total:,}")
    print(f"  White Matter: {wm_voxels:,} ({wm_voxels/total*100:.1f}%)")
    print(f"  Gray Matter: {gm_voxels:,} ({gm_voxels/total*100:.1f}%)")
    print(f"  CSF (surface + sulci): {csf_voxels - vent_voxels:,}")
    print(f"  Ventricles: {vent_voxels:,}")
    print(f"  Cerebellum: {cb_voxels:,}")
    print(f"  Brainstem: {bs_voxels:,}")
    print(f"  Corpus Callosum: {int(corpus_callosum.sum()):,}")
    print(f"  Deep Gray (thalamus/basal ganglia): {int(deep_gray.sum()):,}")
    print(f"  Intensity range: [{data.min():.1f}, {data.max():.1f}]")

    return output_path


if __name__ == "__main__":
    create_realistic_brain()
