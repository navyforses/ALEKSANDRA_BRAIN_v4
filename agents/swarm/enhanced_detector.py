"""
enhanced_detector.py — Baseline-aware cyst/lesion detector for brain chunks.

Uses a healthy baseline brain for comparison. Detects anomalies via:
  1. Intensity drop vs baseline (Z-score)
  2. Texture loss (local std, entropy, gradient)
  3. Connected component analysis (cyst size filtering)
  4. Multi-criteria fusion scoring

Usage:
    from agents.swarm.enhanced_detector import EnhancedDetector
    det = EnhancedDetector("healthy_brain.nii.gz")
    findings = det.analyze_chunk(damaged_chunk, coords)
"""

from __future__ import annotations

from typing import Any

import nibabel as nib
import numpy as np

# Optional GLCM via scikit-image
try:
    from skimage.feature import graycomatrix, graycoprops

    SKIMAGE_AVAILABLE = True
except ImportError:
    SKIMAGE_AVAILABLE = False


class EnhancedDetector:
    """
    Detects cysts and lesions by comparing damaged brain chunks
    against a healthy baseline chunk.
    """

    def __init__(self, healthy_path: str):
        self.healthy_img = nib.load(healthy_path)
        self.healthy = self.healthy_img.get_fdata()

    def _get_baseline_chunk(self, coords: dict[str, int]) -> np.ndarray:
        """Extract the corresponding chunk from the healthy baseline."""
        x0, x1 = coords["x_start"], coords["x_end"]
        y0, y1 = coords["y_start"], coords["y_end"]
        z0, z1 = coords["z_start"], coords["z_end"]
        return self.healthy[x0:x1, y0:y1, z0:z1]

    def _intensity_features(
        self, damaged: np.ndarray, baseline: np.ndarray
    ) -> dict[str, float]:
        """Compare intensity statistics."""
        d_mask = damaged > 0
        b_mask = baseline > 0

        d_mean = float(np.mean(damaged[d_mask])) if d_mask.any() else 0.0
        b_mean = float(np.mean(baseline[b_mask])) if b_mask.any() else 0.0
        d_std = float(np.std(damaged[d_mask])) if d_mask.any() else 0.0
        b_std = float(np.std(baseline[b_mask])) if b_mask.any() else 0.0

        # Z-score of intensity drop
        z_drop = (b_mean - d_mean) / (b_std + 1e-6) if b_std > 0 else 0.0

        return {
            "damaged_mean": d_mean,
            "baseline_mean": b_mean,
            "mean_diff": b_mean - d_mean,
            "damaged_std": d_std,
            "baseline_std": b_std,
            "std_ratio": d_std / (b_std + 1e-6),
            "z_drop": z_drop,
        }

    def _texture_features(self, damaged: np.ndarray) -> dict[str, float]:
        """Extract texture features from damaged chunk."""
        features: dict[str, float] = {}

        # Local standard deviation (loss of texture = lower std)
        features["local_std"] = float(np.std(damaged))

        # Entropy (histogram-based)
        hist, _ = np.histogram(damaged.flatten(), bins=32, range=(0, 200))
        hist = hist / (hist.sum() + 1e-6)
        entropy = -np.sum(hist * np.log2(hist + 1e-10))
        features["entropy"] = float(entropy)

        # Gradient magnitude (edges)
        grad = np.gradient(damaged.astype(np.float32))
        grad_mag = np.sqrt(sum(g**2 for g in grad))
        features["gradient_mean"] = float(np.mean(grad_mag))
        features["gradient_max"] = float(np.max(grad_mag))

        # Laplacian (second derivative, good for blob detection)
        laplacian = (
            np.roll(damaged, 1, axis=0)
            + np.roll(damaged, -1, axis=0)
            + np.roll(damaged, 1, axis=1)
            + np.roll(damaged, -1, axis=1)
            + np.roll(damaged, 1, axis=2)
            + np.roll(damaged, -1, axis=2)
            - 6 * damaged
        )
        features["laplacian_std"] = float(np.std(laplacian))

        # Optional GLCM on a central 2D slice
        if SKIMAGE_AVAILABLE and damaged.ndim == 3 and min(damaged.shape) >= 8:
            mid_slice = damaged[:, :, damaged.shape[2] // 2]
            # Normalize to 0-255 for GLCM
            smin, smax = mid_slice.min(), mid_slice.max()
            if smax > smin:
                norm = ((mid_slice - smin) / (smax - smin) * 63).astype(np.uint8)
                glcm = graycomatrix(
                    norm,
                    distances=[1],
                    angles=[0],
                    levels=64,
                    symmetric=True,
                    normed=True,
                )
                features["glcm_contrast"] = float(graycoprops(glcm, "contrast")[0, 0])
                features["glcm_homogeneity"] = float(
                    graycoprops(glcm, "homogeneity")[0, 0]
                )
                features["glcm_energy"] = float(graycoprops(glcm, "energy")[0, 0])
            else:
                features["glcm_contrast"] = 0.0
                features["glcm_homogeneity"] = 1.0
                features["glcm_energy"] = 1.0
        else:
            features["glcm_contrast"] = 0.0
            features["glcm_homogeneity"] = 1.0
            features["glcm_energy"] = 1.0

        return features

    def _connected_components(
        self, damaged: np.ndarray, baseline: np.ndarray
    ) -> list[dict[str, Any]]:
        """
        Find connected components that are likely cysts.
        Cysts: very low intensity in damaged, normal in baseline.
        """
        from scipy import ndimage

        # Threshold: damaged < 20 AND baseline > 50 (was normal, now dark)
        cyst_mask = (damaged < 20) & (baseline > 50)

        if not cyst_mask.any():
            return []

        # 26-connectivity labeling
        labeled, num_features = ndimage.label(cyst_mask)

        components = []
        for i in range(1, num_features + 1):
            comp_mask = labeled == i
            size = int(comp_mask.sum())

            # Filter by size: cysts are typically 5-5000 voxels
            if size < 5 or size > 5000:
                continue

            # Get bounding box center
            coords = np.argwhere(comp_mask)
            center = coords.mean(axis=0).astype(int).tolist()

            # Intensity stats within component
            comp_damaged = damaged[comp_mask]
            comp_baseline = baseline[comp_mask]

            components.append(
                {
                    "label_id": i,
                    "size_voxels": size,
                    "center": center,
                    "damaged_mean": float(np.mean(comp_damaged)),
                    "baseline_mean": float(np.mean(comp_baseline)),
                    "intensity_drop": float(
                        np.mean(comp_baseline) - np.mean(comp_damaged)
                    ),
                }
            )

        return components

    def analyze_chunk(
        self,
        damaged: np.ndarray,
        coords: dict[str, int],
    ) -> dict[str, Any]:
        """
        Full analysis of one chunk against baseline.
        Returns findings, score, and confidence.
        """
        baseline = self._get_baseline_chunk(coords)

        # Ensure same shape
        if damaged.shape != baseline.shape:
            return {
                "status": "error",
                "message": f"Shape mismatch: damaged {damaged.shape} vs baseline {baseline.shape}",
            }

        # 1. Intensity features
        int_feats = self._intensity_features(damaged, baseline)

        # 2. Texture features
        tex_feats = self._texture_features(damaged)

        # 3. Connected components (cysts)
        components = self._connected_components(damaged, baseline)

        # 4. Multi-criteria scoring
        score = 0.0
        reasons: list[str] = []

        # Intensity drop (Z-score > 2 = significant)
        if int_feats["z_drop"] > 2.0:
            score += 2.0
            reasons.append(f"intensity_drop_z{int_feats['z_drop']:.1f}")

        # Texture loss (std reduced by >50%)
        if int_feats["std_ratio"] < 0.5:
            score += 1.0
            reasons.append("texture_loss")

        # Low entropy (homogenization)
        if tex_feats["entropy"] < 2.0:
            score += 1.0
            reasons.append("low_entropy")

        # Cyst components found
        if len(components) > 0:
            score += min(len(components) * 1.5, 4.0)
            reasons.append(f"cysts_n{len(components)}")

        # Confidence based on score
        if score >= 4.0:
            confidence = "high"
        elif score >= 2.0:
            confidence = "medium"
        elif score >= 0.5:
            confidence = "low"
        else:
            confidence = "none"

        # Lesion list for downstream
        lesions: list[dict[str, Any]] = []
        for comp in components:
            lesions.append(
                {
                    "type": "cyst",
                    "confidence": 0.7 if confidence == "high" else 0.5,
                    "center_voxel": comp["center"],
                    "size_voxels": comp["size_voxels"],
                    "intensity_drop": round(comp["intensity_drop"], 2),
                }
            )

        return {
            "status": "success",
            "score": round(score, 2),
            "confidence": confidence,
            "reasons": reasons,
            "intensity_features": {k: round(v, 4) for k, v in int_feats.items()},
            "texture_features": {k: round(v, 4) for k, v in tex_feats.items()},
            "components": components,
            "lesions": lesions,
        }


if __name__ == "__main__":
    # Quick test
    healthy_path = "tests/fixtures/healthy_brain_128.nii.gz"
    damaged_path = "tests/fixtures/damaged_brain_128.nii.gz"

    det = EnhancedDetector(healthy_path)
    damaged = nib.load(damaged_path).get_fdata()

    # Test a few chunks
    test_coords = [
        {
            "x_start": 50,
            "x_end": 60,
            "y_start": 50,
            "y_end": 60,
            "z_start": 50,
            "z_end": 60,
        },
        {
            "x_start": 60,
            "x_end": 70,
            "y_start": 60,
            "y_end": 70,
            "z_start": 60,
            "z_end": 70,
        },
        {
            "x_start": 0,
            "x_end": 10,
            "y_start": 0,
            "y_end": 10,
            "z_start": 0,
            "z_end": 10,
        },
    ]

    print("EnhancedDetector quick test:")
    for coords in test_coords:
        x0, x1 = coords["x_start"], coords["x_end"]
        y0, y1 = coords["y_start"], coords["y_end"]
        z0, z1 = coords["z_start"], coords["z_end"]
        chunk = damaged[x0:x1, y0:y1, z0:z1]
        result = det.analyze_chunk(chunk, coords)
        print(
            f"  Chunk ({x0},{y0},{z0}): score={result['score']}, confidence={result['confidence']}, cysts={len(result['components'])}"
        )
