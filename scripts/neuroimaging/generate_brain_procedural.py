"""
generate_brain_procedural.py — Procedural brain as interconnected branching structures.

Like the neuron, each anatomical component is generated procedurally:
  - Cortex: branching surface tubes forming gyri/sulci
  - WM tracts: tubular connections (corpus callosum, internal capsule, etc.)
  - Deep gray: clustered irregular bodies
  - Brainstem: stacked segmented structure
  - Cerebellum: parallel folia branches
  - Ventricles: branching cavity network

Output: Inline JS for Three.js viewer
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List

import numpy as np


@dataclass
class BrainPoint:
    x: float
    y: float
    z: float
    nx: float = 0.0
    ny: float = 0.0
    nz: float = 1.0
    r: float = 1.0
    comp_type: str = "cortex"
    intensity: float = 100.0


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================


def normalize(v: np.ndarray) -> np.ndarray:
    n = np.linalg.norm(v) + 1e-8
    return v / n


def perpendicular(v: np.ndarray) -> np.ndarray:
    """Return a vector perpendicular to v."""
    if abs(v[2]) < 0.9:
        p = np.array([-v[1], v[0], 0.0])
    else:
        p = np.array([1.0, 0.0, 0.0])
    return normalize(p)


def sample_tube_line(
    x1: float,
    y1: float,
    z1: float,
    x2: float,
    y2: float,
    z2: float,
    radius: float,
    comp_type: str,
    intensity: float,
    density: float = 3.0,
    jitter: float = 0.3,
) -> List[BrainPoint]:
    """Sample points along a line with tube-like cross-section."""
    length = np.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2 + (z2 - z1) ** 2)
    n_points = max(2, int(length * density))

    points = []
    dx, dy, dz = x2 - x1, y2 - y1, z2 - z1
    line_dir = normalize(np.array([dx, dy, dz]))
    perp1 = perpendicular(line_dir)
    perp2 = np.cross(line_dir, perp1)
    perp2 = normalize(perp2)

    for i in range(n_points):
        t = i / (n_points - 1)
        cx = x1 + t * dx
        cy = y1 + t * dy
        cz = z1 + t * dz

        # Tube cross-section: multiple points around the radius
        n_ring = max(3, int(radius * 2.5))
        for j in range(n_ring):
            angle = 2 * np.pi * j / n_ring
            # Random radius variation for organic look
            r_var = radius * (0.85 + 0.15 * np.random.random())
            off_x = perp1[0] * np.cos(angle) * r_var + perp2[0] * np.sin(angle) * r_var
            off_y = perp1[1] * np.cos(angle) * r_var + perp2[1] * np.sin(angle) * r_var
            off_z = perp1[2] * np.cos(angle) * r_var + perp2[2] * np.sin(angle) * r_var

            px = cx + off_x + np.random.normal(0, jitter * radius * 0.1)
            py = cy + off_y + np.random.normal(0, jitter * radius * 0.1)
            pz = cz + off_z + np.random.normal(0, jitter * radius * 0.1)

            # Normal points outward from centerline
            nx = off_x / (r_var + 1e-8)
            ny = off_y / (r_var + 1e-8)
            nz = off_z / (r_var + 1e-8)
            nx, ny, nz = normalize(np.array([nx, ny, nz]))

            points.append(
                BrainPoint(
                    x=round(px, 2),
                    y=round(py, 2),
                    z=round(pz, 2),
                    nx=round(nx, 3),
                    ny=round(ny, 3),
                    nz=round(nz, 3),
                    r=round(radius, 3),
                    comp_type=comp_type,
                    intensity=round(intensity, 1),
                )
            )

    return points


def branch_recursive_tube(
    x: float,
    y: float,
    z: float,
    dx: float,
    dy: float,
    dz: float,
    length: float,
    radius: float,
    generation: int,
    max_gen: int,
    branch_angle: float,
    comp_type: str,
    intensity: float,
    length_decay: float = 0.75,
    radius_decay: float = 0.7,
    branch_prob: float = 0.85,
    points_list: List[BrainPoint] = None,
    density: float = 2.5,
) -> List[BrainPoint]:
    """Recursively generate branching tube structure."""
    if points_list is None:
        points_list = []

    if generation > max_gen or length < 2.0 or radius < 0.5:
        return points_list

    # Wandering direction
    wander = 0.08 * (1 + generation * 0.05)
    dx += np.random.normal(0, wander)
    dy += np.random.normal(0, wander)
    dz += np.random.normal(0, wander)
    dx, dy, dz = normalize(np.array([dx, dy, dz]))

    x2 = x + dx * length
    y2 = y + dy * length
    z2 = z + dz * length

    pts = sample_tube_line(x, y, z, x2, y2, z2, radius, comp_type, intensity, density)
    points_list.extend(pts)

    # Branching
    if np.random.random() < branch_prob and generation < max_gen:
        n_branches = np.random.choice([2, 3], p=[0.75, 0.25])

        for b in range(n_branches):
            angle = branch_angle + np.random.normal(0, 0.12)

            # Perpendicular axis
            p = perpendicular(np.array([dx, dy, dz]))
            # Rotate around original direction
            rot = np.random.uniform(0, 2 * np.pi) + b * 2.1  # Spread branches
            cos_r, sin_r = np.cos(rot), np.sin(rot)

            # Rotate p around direction vector
            d = np.array([dx, dy, dz])
            cos_a, sin_a = np.cos(angle), np.sin(angle)

            nd = d * cos_a + p * sin_a
            # Rotate around d
            o = np.cross(d, p)
            o = normalize(o)
            fd = nd * cos_r + o * sin_r
            fd = normalize(fd)

            new_radius = radius * radius_decay * np.random.uniform(0.8, 1.0)
            new_length = length * length_decay * np.random.uniform(0.7, 1.0)

            branch_recursive_tube(
                x2,
                y2,
                z2,
                fd[0],
                fd[1],
                fd[2],
                new_length,
                new_radius,
                generation + 1,
                max_gen,
                branch_angle * 0.9,
                comp_type,
                intensity,
                length_decay,
                radius_decay,
                branch_prob,
                points_list,
                density,
            )

    return points_list


# =============================================================================
# BRAIN COMPONENT GENERATORS
# =============================================================================


def generate_cortex_hemisphere(
    cx: float, cy: float, cz: float, side: str = "left"
) -> List[BrainPoint]:
    """Generate cortical surface as branching gyri/sulci on a hemisphere."""
    points = []
    np.random.seed(42 if side == "left" else 43)

    # Seed points on hemisphere surface (ellipsoid)
    n_seeds = 6
    a, b, c = 30.0, 35.0, 28.0  # Hemisphere dimensions

    for i in range(n_seeds):
        theta = np.pi * i / (n_seeds - 1) * 0.85  # Slightly less than full hemisphere
        for j in range(2):
            phi = 2 * np.pi * j / 4 + np.random.normal(0, 0.3)

            # Hemisphere: x flipped for right side
            sx = cx + (a if side == "right" else -a) * np.sin(theta) * np.cos(phi) * 0.9
            sy = cy + b * np.sin(theta) * np.sin(phi) * 0.85
            sz = cz + c * np.cos(theta) * 0.9

            # Outward direction from center
            dx = sx - cx
            dy = sy - cy
            dz = sz - cz
            dx, dy, dz = normalize(np.array([dx, dy, dz]))

            # Branch to form gyrus
            pts = branch_recursive_tube(
                sx,
                sy,
                sz,
                dx,
                dy,
                dz,
                length=12.0 + np.random.uniform(0, 6),
                radius=2.5 + np.random.uniform(0, 1.5),
                generation=0,
                max_gen=2,
                branch_angle=0.7,
                comp_type="cortex",
                intensity=np.random.uniform(85, 110),
                length_decay=0.7,
                radius_decay=0.65,
                branch_prob=0.8,
                density=0.18,
            )
            points.extend(pts)

    # Major sulci (deeper grooves) — represented as lower-density branching
    for i in range(6):
        theta = np.pi * (0.2 + 0.6 * i / 5)
        phi = np.random.uniform(0, 2 * np.pi)

        sx = cx + (a if side == "right" else -a) * np.sin(theta) * np.cos(phi) * 0.7
        sy = cy + b * np.sin(theta) * np.sin(phi) * 0.7
        sz = cz + c * np.cos(theta) * 0.7

        dx = sx - cx
        dy = sy - cy
        dz = sz - cz
        dx, dy, dz = normalize(np.array([dx, dy, dz]))

        # Sulcus goes inward
        pts = branch_recursive_tube(
            sx,
            sy,
            sz,
            -dx * 0.3,
            -dy * 0.3,
            -dz * 0.3,
            length=8.0,
            radius=1.8,
            generation=0,
            max_gen=3,
            branch_angle=0.5,
            comp_type="sulcus",
            intensity=25.0,
            density=1.5,
        )
        points.extend(pts)

    return points


def generate_corpus_callosum(cx: float, cy: float, cz: float) -> List[BrainPoint]:
    """Generate corpus callosum as arched white matter tract."""
    points = []

    # Arc from front to back, curving upward
    n_segments = 20
    for i in range(n_segments):
        t = i / (n_segments - 1)
        # Arc shape: parabola in Z, ellipse in XY
        x = cx + np.sin(t * np.pi) * 3.0  # Thin in X
        y = cy + 25.0 - t * 50.0  # From front (y=+25) to back (y=-25)
        z = cz + 15.0 + np.sin(t * np.pi) * 8.0  # Arches upward in middle

        # Next point for direction
        t2 = (i + 1) / (n_segments - 1)
        x2 = cx + np.sin(t2 * np.pi) * 3.0
        y2 = cy + 25.0 - t2 * 50.0
        z2 = cz + 15.0 + np.sin(t2 * np.pi) * 8.0

        # Varying radius: thicker in middle (genu/splenium)
        r = 3.5 + 2.0 * np.sin(t * np.pi)

        pts = sample_tube_line(x, y, z, x2, y2, z2, r, "wm_tract", 170.0, density=3.5)
        points.extend(pts)

    # Radiating fibers (corona radiata) — branches from CC to cortex
    for i in range(4):
        t = i / 11
        sx = cx + np.sin(t * np.pi) * 3.0
        sy = cy + 25.0 - t * 50.0
        sz = cz + 15.0 + np.sin(t * np.pi) * 8.0

        # Radiate outward to cortex
        angle = 2 * np.pi * i / 12
        dx = np.cos(angle) * 0.8
        dy = np.sin(angle) * 0.3
        dz = 0.6
        dx, dy, dz = normalize(np.array([dx, dy, dz]))

        pts = branch_recursive_tube(
            sx,
            sy,
            sz,
            dx,
            dy,
            dz,
            length=15.0,
            radius=1.2,
            generation=0,
            max_gen=3,
            branch_angle=0.6,
            comp_type="wm_tract",
            intensity=165.0,
            density=2.0,
        )
        points.extend(pts)

    return points


def generate_internal_capsule(cx: float, cy: float, cz: float) -> List[BrainPoint]:
    """Generate internal capsule — vertical white matter column."""
    points = []

    # Two capsules, left and right
    for side in [-1, 1]:
        x0 = cx + side * 12.0
        y0 = cy - 5.0
        z0 = cz + 5.0

        # Vertical column with slight angle
        for i in range(12):
            t = i / 24
            x = x0 + side * t * 3.0
            y = y0 + t * 15.0 - 7.5
            z = z0 - t * 20.0 + 10.0

            t2 = (i + 1) / 24
            x2 = x0 + side * t2 * 3.0
            y2 = y0 + t2 * 15.0 - 7.5
            z2 = z0 - t2 * 20.0 + 10.0

            r = 2.5 + 0.5 * np.sin(t * np.pi)
            pts = sample_tube_line(
                x, y, z, x2, y2, z2, r, "wm_tract", 175.0, density=2.0
            )
            points.extend(pts)

    return points


def generate_deep_gray(cx: float, cy: float, cz: float) -> List[BrainPoint]:
    """Generate deep gray nuclei as irregular clustered bodies."""
    points = []

    # Thalamus (paired, central)
    for side in [-1, 1]:
        for _ in range(300):
            # Ellipsoid cluster
            u = np.random.uniform(0, 2 * np.pi)
            v = np.random.uniform(0, np.pi)
            r = np.random.uniform(0, 1.0) ** (1 / 3)  # Uniform in sphere

            px = cx + side * 8.0 + r * 5.0 * np.sin(v) * np.cos(u)
            py = cy + r * 4.0 * np.sin(v) * np.sin(u)
            pz = cz + 3.0 + r * 5.0 * np.cos(v)

            # Normal points outward from center
            nx = (px - cx - side * 8.0) / 5.0
            ny = (py - cy) / 4.0
            nz = (pz - cz - 3.0) / 5.0
            nx, ny, nz = normalize(np.array([nx, ny, nz]))

            points.append(
                BrainPoint(
                    x=round(px, 2),
                    y=round(py, 2),
                    z=round(pz, 2),
                    nx=round(nx, 3),
                    ny=round(ny, 3),
                    nz=round(nz, 3),
                    r=1.2,
                    comp_type="deep_gray",
                    intensity=np.random.uniform(90, 110),
                )
            )

    # Lentiform nucleus (lateral to thalamus)
    for side in [-1, 1]:
        for _ in range(250):
            u = np.random.uniform(0, 2 * np.pi)
            v = np.random.uniform(0, np.pi)
            r = np.random.uniform(0, 1.0) ** (1 / 3)

            px = cx + side * 16.0 + r * 4.0 * np.sin(v) * np.cos(u)
            py = cy + r * 5.0 * np.sin(v) * np.sin(u)
            pz = cz + 2.0 + r * 4.5 * np.cos(v)

            nx = (px - cx - side * 16.0) / 4.0
            ny = (py - cy) / 5.0
            nz = (pz - cz - 2.0) / 4.5
            nx, ny, nz = normalize(np.array([nx, ny, nz]))

            points.append(
                BrainPoint(
                    x=round(px, 2),
                    y=round(py, 2),
                    z=round(pz, 2),
                    nx=round(nx, 3),
                    ny=round(ny, 3),
                    nz=round(nz, 3),
                    r=1.0,
                    comp_type="deep_gray",
                    intensity=np.random.uniform(85, 105),
                )
            )

    return points


def generate_brainstem(cx: float, cy: float, cz: float) -> List[BrainPoint]:
    """Generate brainstem as stacked segmented tubes."""
    points = []

    # Midbrain (top)
    for i in range(8):
        t = i / 14
        x = cx + np.sin(t * np.pi * 2) * 0.5
        y = cy + np.cos(t * np.pi * 2) * 0.5
        z = cz - 12.0 + t * 5.0

        t2 = (i + 1) / 14
        x2 = cx + np.sin(t2 * np.pi * 2) * 0.5
        y2 = cy + np.cos(t2 * np.pi * 2) * 0.5
        z2 = cz - 12.0 + t2 * 5.0

        r = 4.0 + np.sin(t * np.pi) * 0.5
        pts = sample_tube_line(x, y, z, x2, y2, z2, r, "brainstem", 95.0, density=3.0)
        points.extend(pts)

    # Pons (bulging middle)
    for i in range(20):
        t = i / 19
        x = cx + np.sin(t * np.pi * 3) * 0.3
        y = cy + t * 1.5 - 0.75
        z = cz - 17.0 + t * 5.0

        t2 = (i + 1) / 19
        x2 = cx + np.sin(t2 * np.pi * 3) * 0.3
        y2 = cy + t2 * 1.5 - 0.75
        z2 = cz - 17.0 + t2 * 5.0

        # Pons bulges anteriorly
        r = 4.5 + 2.0 * np.sin(t * np.pi) ** 2
        pts = sample_tube_line(x, y, z, x2, y2, z2, r, "brainstem", 90.0, density=3.0)
        points.extend(pts)

    # Medulla (tapering bottom)
    for i in range(18):
        t = i / 17
        x = cx
        y = cy
        z = cz - 22.0 + t * 6.0

        t2 = (i + 1) / 17
        x2 = cx
        y2 = cy
        z2 = cz - 22.0 + t2 * 6.0

        r = 3.5 - t * 1.5  # Tapers
        pts = sample_tube_line(x, y, z, x2, y2, z2, r, "brainstem", 88.0, density=3.0)
        points.extend(pts)

    return points


def generate_cerebellum(cx: float, cy: float, cz: float) -> List[BrainPoint]:
    """Generate cerebellum with parallel folia."""
    points = []

    # Two hemispheres + vermis
    for side in [-1, 1]:
        # Folia = parallel branching sheets
        for folia_i in range(5):
            angle = folia_i / 7 * np.pi * 0.6 - np.pi * 0.3

            # Start point
            sx = cx + side * (10.0 + folia_i * 1.5)
            sy = cy - 25.0 + folia_i * 0.5
            sz = cz - 18.0

            # Direction: curved back and slightly up
            dx = side * np.cos(angle) * 0.3
            dy = -0.8 + np.sin(angle) * 0.2
            dz = 0.5
            dx, dy, dz = normalize(np.array([dx, dy, dz]))

            pts = branch_recursive_tube(
                sx,
                sy,
                sz,
                dx,
                dy,
                dz,
                length=10.0 + folia_i * 0.5,
                radius=1.5 + np.random.uniform(0, 0.5),
                generation=0,
                max_gen=2,
                branch_angle=0.4,
                comp_type="cerebellum",
                intensity=np.random.uniform(80, 100),
                length_decay=0.8,
                radius_decay=0.75,
                branch_prob=0.6,
                density=0.18,
            )
            points.extend(pts)

    # Vermis (midline)
    for folia_i in range(3):
        sx = cx + np.random.normal(0, 0.5)
        sy = cy - 25.0 + folia_i * 0.3
        sz = cz - 18.0

        dx = np.random.normal(0, 0.2)
        dy = -0.8
        dz = 0.5
        dx, dy, dz = normalize(np.array([dx, dy, dz]))

        pts = branch_recursive_tube(
            sx,
            sy,
            sz,
            dx,
            dy,
            dz,
            length=8.0,
            radius=1.2,
            generation=0,
            max_gen=2,
            branch_angle=0.3,
            comp_type="cerebellum",
            intensity=np.random.uniform(85, 95),
            density=2.0,
        )
        points.extend(pts)

    return points


def generate_ventricles(cx: float, cy: float, cz: float) -> List[BrainPoint]:
    """Generate ventricular system as branching cavity tubes."""
    points = []

    # Lateral ventricles (C-shape simplified)
    for side in [-1, 1]:
        # Body -> occipital horn -> temporal horn
        n_seg = 12
        for i in range(n_seg):
            t = i / (n_seg - 1)

            # C-shape parametric
            x = cx + side * (5.0 + 3.0 * np.sin(t * np.pi))
            y = cy + 5.0 - t * 20.0
            z = cz + 8.0 + 5.0 * np.cos(t * np.pi * 0.8)

            t2 = (i + 1) / (n_seg - 1)
            x2 = cx + side * (5.0 + 3.0 * np.sin(t2 * np.pi))
            y2 = cy + 5.0 - t2 * 20.0
            z2 = cz + 8.0 + 5.0 * np.cos(t2 * np.pi * 0.8)

            r = 2.5 + np.sin(t * np.pi) * 1.0
            pts = sample_tube_line(
                x, y, z, x2, y2, z2, r, "ventricle", 15.0, density=2.0
            )
            points.extend(pts)

    # Third ventricle (thin slit)
    for i in range(8):
        t = i / 14
        x = cx + np.sin(t * np.pi) * 1.5
        y = cy + 2.0 - t * 8.0
        z = cz + 6.0

        t2 = (i + 1) / 14
        x2 = cx + np.sin(t2 * np.pi) * 1.5
        y2 = cy + 2.0 - t2 * 8.0
        z2 = cz + 6.0

        pts = sample_tube_line(x, y, z, x2, y2, z2, 1.2, "ventricle", 12.0, density=2.5)
        points.extend(pts)

    return points


# =============================================================================
# MAIN EXPORT
# =============================================================================


def generate_procedural_brain(seed: int = 42) -> List[BrainPoint]:
    """Generate complete procedural brain."""
    np.random.seed(seed)

    cx, cy, cz = 0, 0, 0
    all_points = []

    print("Generating procedural brain...")

    print("  Cortex (left hemisphere)...")
    all_points.extend(generate_cortex_hemisphere(cx, cy, cz, "left"))

    print("  Cortex (right hemisphere)...")
    all_points.extend(generate_cortex_hemisphere(cx, cy, cz, "right"))

    print("  Corpus callosum...")
    all_points.extend(generate_corpus_callosum(cx, cy, cz))

    print("  Internal capsule...")
    all_points.extend(generate_internal_capsule(cx, cy, cz))

    print("  Deep gray nuclei...")
    all_points.extend(generate_deep_gray(cx, cy, cz))

    print("  Brainstem...")
    all_points.extend(generate_brainstem(cx, cy, cz))

    print("  Cerebellum...")
    all_points.extend(generate_cerebellum(cx, cy, cz))

    print("  Ventricles...")
    all_points.extend(generate_ventricles(cx, cy, cz))

    return all_points


def export_brain_js(output_path: str = "viewer/brain_procedural.js"):
    """Export procedural brain as inline JS."""
    points = generate_procedural_brain()

    from collections import Counter

    counts = Counter(p.comp_type for p in points)
    print("\nBrain components:")
    for ctype, count in sorted(counts.items()):
        print(f"  {ctype}: {count:,} points")
    print(f"  TOTAL: {len(points):,} points")

    # Center and scale
    xs = [p.x for p in points]
    ys = [p.y for p in points]
    zs = [p.z for p in points]
    mx, my, mz = np.mean(xs), np.mean(ys), np.mean(zs)

    # Scale to ~128 range and center
    scale = 1.2

    js_lines = ["const BRAIN_PROCEDURAL = ["]
    for p in points:
        js_lines.append(
            f"  {{x:{round((p.x - mx)*scale + 64, 2)},y:{round((p.y - my)*scale + 64, 2)},z:{round((p.z - mz)*scale + 64, 2)},"
            f"nx:{p.nx},ny:{p.ny},nz:{p.nz},r:{p.r},t:'{p.comp_type}',i:{p.intensity}}},"
        )
    js_lines.append("];")

    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(js_lines))

    print(f"\nSaved -> {output_path}")
    return len(points)


if __name__ == "__main__":
    export_brain_js()
