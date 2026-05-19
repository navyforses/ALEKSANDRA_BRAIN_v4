"""Extract a small subset of points for inline HTML demo."""

import numpy as np
import nibabel as nib

img = nib.load("tests/fixtures/healthy_brain_128.nii.gz")
data = img.get_fdata()

# Get non-zero voxels
mask = data > 0
coords = np.argwhere(mask)
intensities = data[mask]

# Sample ~800 points evenly distributed
step = max(1, len(coords) // 800)
sample_coords = coords[::step][:800]
sample_intensities = intensities[::step][:800]

points = []
for (z, y, x), intensity in zip(sample_coords, sample_intensities):
    points.append(
        {"x": int(x), "y": int(y), "z": int(z), "i": round(float(intensity), 1)}
    )

# Generate inline JS
js_lines = ["const DEMO_POINTS = ["]
for p in points:
    js_lines.append(f"  {{x:{p['x']},y:{p['y']},z:{p['z']},i:{p['i']}}},")
js_lines.append("];")

with open("viewer/demo_points.js", "w", encoding="utf-8") as f:
    f.write("\n".join(js_lines))

print(f"Generated inline demo with {len(points)} points")
