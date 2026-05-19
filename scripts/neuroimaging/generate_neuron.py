"""
generate_neuron.py — Procedural pyramidal neuron generation for 3D visualization.

Anatomically-informed components:
  - Soma: slightly irregular pyramidal body
  - Apical dendrite: single trunk extending from apex, moderate branching
  - Basal dendrites: bushy tree radiating from base, heavy branching
  - Axon: single process with initial segment, myelin sheaths, nodes of Ranvier
  - Dendritic spines: small protrusions on dendrites
  - Synaptic boutons: terminal swellings on axon

Output: Inline JS for Three.js point cloud viewer
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List

import numpy as np


@dataclass
class Segment:
    """A line segment in 3D space."""

    x1: float
    y1: float
    z1: float
    x2: float
    y2: float
    z2: float
    radius: float
    comp_type: (
        str  # 'soma', 'apical', 'basal', 'axon', 'myelin', 'spine', 'bouton', 'node'
    )


def sample_line(x1, y1, z1, x2, y2, z2, radius, comp_type, density=5.0):
    """Sample points along a line segment."""
    length = np.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2 + (z2 - z1) ** 2)
    n_points = max(2, int(length * density))

    points = []
    for i in range(n_points):
        t = i / (n_points - 1)
        x = x1 + t * (x2 - x1)
        y = y1 + t * (y2 - y1)
        z = z1 + t * (z2 - z1)

        # Add slight jitter for organic look
        jitter = radius * 0.15
        x += np.random.normal(0, jitter)
        y += np.random.normal(0, jitter)
        z += np.random.normal(0, jitter)

        # Normal = perpendicular to line direction
        dx, dy, dz = x2 - x1, y2 - y1, z2 - z1
        length_dir = np.sqrt(dx**2 + dy**2 + dz**2) + 1e-8
        dx, dy, dz = dx / length_dir, dy / length_dir, dz / length_dir

        # Find perpendicular vector
        if abs(dz) < 0.9:
            nx, ny, nz = -dy, dx, 0
        else:
            nx, ny, nz = 1, 0, 0
        nlen = np.sqrt(nx**2 + ny**2 + nz**2) + 1e-8
        nx, ny, nz = nx / nlen, ny / nlen, nz / nlen

        points.append(
            {
                "x": round(x, 2),
                "y": round(y, 2),
                "z": round(z, 2),
                "r": round(radius, 3),
                "nx": round(nx, 3),
                "ny": round(ny, 3),
                "nz": round(nz, 3),
                "type": comp_type,
            }
        )

    return points


def generate_soma(cx=0, cy=0, cz=0, size=12.0):
    """Generate soma surface points — slightly irregular ellipsoid."""
    points = []
    n_theta = 20
    n_phi = 16

    for i in range(n_theta):
        theta = np.pi * i / (n_theta - 1)
        for j in range(n_phi):
            phi = 2 * np.pi * j / (n_phi - 1)

            # Pyramidal-ish shape: taller than wide
            r = size * (0.9 + 0.1 * np.sin(theta) ** 2)
            x = r * np.sin(theta) * np.cos(phi) * 0.85
            y = r * np.sin(theta) * np.sin(phi) * 0.85
            z = r * np.cos(theta) * 1.2

            # Add irregularity
            x += np.random.normal(0, 0.8)
            y += np.random.normal(0, 0.8)
            z += np.random.normal(0, 0.8)

            # Normal
            nx = np.sin(theta) * np.cos(phi)
            ny = np.sin(theta) * np.sin(phi)
            nz = np.cos(theta)

            points.append(
                {
                    "x": round(cx + x, 2),
                    "y": round(cy + y, 2),
                    "z": round(cz + z, 2),
                    "r": 1.5,
                    "nx": round(nx, 3),
                    "ny": round(ny, 3),
                    "nz": round(nz, 3),
                    "type": "soma",
                }
            )

    return points


def branch_recursive(
    x,
    y,
    z,
    dx,
    dy,
    dz,
    length,
    radius,
    generation,
    max_gen,
    branch_angle,
    comp_type,
    segments: List[Segment],
):
    """Recursively generate dendritic branches."""
    if generation > max_gen or length < 1.5 or radius < 0.15:
        return

    # Add some wandering to direction
    wander = 0.15 * (1 + generation * 0.1)
    dx += np.random.normal(0, wander)
    dy += np.random.normal(0, wander)
    dz += np.random.normal(0, wander)

    # Normalize
    dlen = np.sqrt(dx**2 + dy**2 + dz**2) + 1e-8
    dx, dy, dz = dx / dlen, dy / dlen, dz / dlen

    x2 = x + dx * length
    y2 = y + dy * length
    z2 = z + dz * length

    segments.append(Segment(x, y, z, x2, y2, z2, radius, comp_type))

    # Branching probability decreases with generation
    branch_prob = max(0.1, 0.9 - generation * 0.25)

    if np.random.random() < branch_prob and generation < max_gen:
        n_branches = np.random.choice([2, 3], p=[0.7, 0.3])

        for b in range(n_branches):
            # Rotate direction around perpendicular axis
            angle = branch_angle + np.random.normal(0, 0.15)

            # Create perpendicular vector
            if abs(dz) < 0.8:
                px, py, pz = -dy, dx, 0
            else:
                px, py, pz = 1, 0, 0
            plen = np.sqrt(px**2 + py**2 + pz**2) + 1e-8
            px, py, pz = px / plen, py / plen, pz / plen

            # Rotate
            cos_a = np.cos(angle * (1 if b == 0 else -1))
            sin_a = np.sin(angle * (1 if b == 0 else -1))

            ndx = dx * cos_a + px * sin_a
            ndy = dy * cos_a + py * sin_a
            ndz = dz * cos_a + pz * sin_a

            # Add random rotation around original axis
            rot = np.random.uniform(0, 2 * np.pi)
            # Simple cross product rotation
            ox, oy, oz = dy * pz - dz * py, dz * px - dx * pz, dx * py - dy * px
            olen = np.sqrt(ox**2 + oy**2 + oz**2) + 1e-8
            ox, oy, oz = ox / olen, oy / olen, oz / olen

            cos_r = np.cos(rot)
            sin_r = np.sin(rot)

            fdx = ndx * cos_r + ox * sin_r
            fdy = ndy * cos_r + oy * sin_r
            fdz = ndz * cos_r + oz * sin_r

            new_radius = radius * np.random.uniform(0.6, 0.85)
            new_length = length * np.random.uniform(0.6, 0.9)

            branch_recursive(
                x2,
                y2,
                z2,
                fdx,
                fdy,
                fdz,
                new_length,
                new_radius,
                generation + 1,
                max_gen,
                branch_angle * 0.9,
                comp_type,
                segments,
            )


def generate_dendritic_spines(segments: List[Segment], density=0.3):
    """Add dendritic spines along dendrite segments."""
    spines = []

    for seg in segments:
        if seg.comp_type not in ("apical", "basal"):
            continue

        length = np.sqrt(
            (seg.x2 - seg.x1) ** 2 + (seg.y2 - seg.y1) ** 2 + (seg.z2 - seg.z1) ** 2
        )
        n_spines = int(length * density)

        for _ in range(n_spines):
            t = np.random.uniform(0, 1)
            x = seg.x1 + t * (seg.x2 - seg.x1)
            y = seg.y1 + t * (seg.y2 - seg.y1)
            z = seg.z1 + t * (seg.z2 - seg.z1)

            # Random direction away from dendrite
            dx = np.random.normal(0, 1)
            dy = np.random.normal(0, 1)
            dz = np.random.normal(0, 1)
            dlen = np.sqrt(dx**2 + dy**2 + dz**2) + 1e-8

            spine_len = np.random.uniform(0.3, 1.0)
            x2 = x + dx / dlen * spine_len
            y2 = y + dy / dlen * spine_len
            z2 = z + dz / dlen * spine_len

            spines.append(Segment(x, y, z, x2, y2, z2, 0.08, "spine"))

    return spines


def generate_axon(x_start, y_start, z_start, length=80.0):
    """Generate axon with myelin sheaths and nodes of Ranvier."""
    segments = []

    # Initial segment: thicker, unmyelinated
    n_initial = 8
    x, y, z = x_start, y_start, z_start
    dx, dy, dz = np.random.normal(0, 0.3), -1.0, np.random.normal(0, 0.3)
    dlen = np.sqrt(dx**2 + dy**2 + dz**2) + 1e-8
    dx, dy, dz = dx / dlen, dy / dlen, dz / dlen

    init_len = length * 0.06
    for i in range(n_initial):
        step = init_len / n_initial
        # Slight meandering
        dx += np.random.normal(0, 0.05)
        dz += np.random.normal(0, 0.05)
        dlen = np.sqrt(dx**2 + dy**2 + dz**2) + 1e-8
        dx, dy, dz = dx / dlen, dy / dlen, dz / dlen

        x2 = x + dx * step
        y2 = y + dy * step
        z2 = z + dz * step

        r = 0.4 * (1 - i / n_initial * 0.3)
        segments.append(Segment(x, y, z, x2, y2, z2, r, "axon"))
        x, y, z = x2, y2, z2

    # Myelinated segments with nodes of Ranvier
    n_internodes = 12
    internode_len = length * 0.7 / n_internodes
    node_len = length * 0.02

    for i in range(n_internodes):
        # Node of Ranvier (gap)
        dx += np.random.normal(0, 0.08)
        dz += np.random.normal(0, 0.08)
        dlen = np.sqrt(dx**2 + dy**2 + dz**2) + 1e-8
        dx, dy, dz = dx / dlen, dy / dlen, dz / dlen

        x2 = x + dx * node_len
        y2 = y + dy * node_len
        z2 = z + dz * node_len
        segments.append(Segment(x, y, z, x2, y2, z2, 0.2, "node"))
        x, y, z = x2, y2, z2

        # Myelin sheath
        for j in range(5):
            step = internode_len / 5
            dx += np.random.normal(0, 0.03)
            dz += np.random.normal(0, 0.03)
            dlen = np.sqrt(dx**2 + dy**2 + dz**2) + 1e-8
            dx, dy, dz = dx / dlen, dy / dlen, dz / dlen

            x2 = x + dx * step
            y2 = y + dy * step
            z2 = z + dz * step

            r = 0.35 + 0.15 * np.sin(np.pi * j / 4)  # Slight bulge in middle
            segments.append(Segment(x, y, z, x2, y2, z2, r, "myelin"))
            x, y, z = x2, y2, z2

    # Terminal arborization (branching at end)
    for _ in range(4):
        tdx = dx + np.random.normal(0, 0.5)
        tdy = dy + np.random.normal(0, 0.5)
        tdz = dz + np.random.normal(0, 0.5)
        tlen = np.sqrt(tdx**2 + tdy**2 + tdz**2) + 1e-8

        tx2 = x + tdx / tlen * length * 0.08
        ty2 = y + tdy / tlen * length * 0.08
        tz2 = z + tdz / tlen * length * 0.08

        segments.append(Segment(x, y, z, tx2, ty2, tz2, 0.15, "axon"))

        # Synaptic bouton at end
        segments.append(Segment(tx2, ty2, tz2, tx2, ty2, tz2, 0.5, "bouton"))

    return segments


def generate_pyramidal_neuron(seed: int = 42) -> List[dict]:
    """Generate a complete pyramidal neuron as point cloud data."""
    np.random.seed(seed)

    all_points = []

    # === SOMA ===
    soma_points = generate_soma(0, 0, 0, size=10.0)
    all_points.extend(soma_points)

    # === APICAL DENDRITE ===
    # Emerges from top of soma, extends upward
    apical_segments = []
    branch_recursive(
        0,
        0,
        10,
        0,
        0,
        1,
        length=18.0,
        radius=1.0,
        generation=0,
        max_gen=5,
        branch_angle=0.6,
        comp_type="apical",
        segments=apical_segments,
    )

    for seg in apical_segments:
        pts = sample_line(
            seg.x1,
            seg.y1,
            seg.z1,
            seg.x2,
            seg.y2,
            seg.z2,
            seg.radius,
            seg.comp_type,
            density=4.0,
        )
        all_points.extend(pts)

    # === BASAL DENDRITES ===
    # Multiple main trunks radiating from base of soma
    basal_segments = []
    n_basal_trunks = 5
    for i in range(n_basal_trunks):
        angle = 2 * np.pi * i / n_basal_trunks + np.random.normal(0, 0.3)
        # Spread downward and outward
        dx = np.cos(angle) * 0.6
        dy = np.sin(angle) * 0.6
        dz = -0.5 + np.random.normal(0, 0.2)

        dlen = np.sqrt(dx**2 + dy**2 + dz**2) + 1e-8
        dx, dy, dz = dx / dlen, dy / dlen, dz / dlen

        branch_recursive(
            np.random.normal(0, 2),
            np.random.normal(0, 2),
            -8,
            dx,
            dy,
            dz,
            length=12.0,
            radius=0.7,
            generation=0,
            max_gen=6,
            branch_angle=0.8,
            comp_type="basal",
            segments=basal_segments,
        )

    for seg in basal_segments:
        pts = sample_line(
            seg.x1,
            seg.y1,
            seg.z1,
            seg.x2,
            seg.y2,
            seg.z2,
            seg.radius,
            seg.comp_type,
            density=4.5,
        )
        all_points.extend(pts)

    # === DENDRITIC SPINES ===
    spine_segments = generate_dendritic_spines(
        apical_segments + basal_segments, density=0.4
    )
    for seg in spine_segments:
        pts = sample_line(
            seg.x1,
            seg.y1,
            seg.z1,
            seg.x2,
            seg.y2,
            seg.z2,
            seg.radius,
            seg.comp_type,
            density=8.0,
        )
        all_points.extend(pts)

    # === AXON ===
    axon_segments = generate_axon(0, 0, -10, length=70.0)
    for seg in axon_segments:
        if seg.comp_type == "bouton":
            # Bouton as small cluster
            for _ in range(5):
                bx = seg.x1 + np.random.normal(0, seg.radius * 0.5)
                by = seg.y1 + np.random.normal(0, seg.radius * 0.5)
                bz = seg.z1 + np.random.normal(0, seg.radius * 0.5)
                all_points.append(
                    {
                        "x": round(bx, 2),
                        "y": round(by, 2),
                        "z": round(bz, 2),
                        "r": round(seg.radius * 0.6, 3),
                        "nx": 0,
                        "ny": 0,
                        "nz": 1,
                        "type": "bouton",
                    }
                )
        else:
            pts = sample_line(
                seg.x1,
                seg.y1,
                seg.z1,
                seg.x2,
                seg.y2,
                seg.z2,
                seg.radius,
                seg.comp_type,
                density=5.0,
            )
            all_points.extend(pts)

    return all_points


def export_neuron_js(output_path: str = "viewer/neuron_data.js"):
    """Generate neuron and export as inline JS."""
    print("Generating pyramidal neuron...")
    points = generate_pyramidal_neuron(seed=42)

    # Count by type
    from collections import Counter

    counts = Counter(p["type"] for p in points)
    print("Neuron components:")
    for ctype, count in sorted(counts.items()):
        print(f"  {ctype}: {count:,} points")
    print(f"  TOTAL: {len(points):,} points")

    # Build JS
    js_lines = ["const NEURON_POINTS = ["]
    for p in points:
        js_lines.append(
            f"  {{x:{p['x']},y:{p['y']},z:{p['z']},r:{p['r']},nx:{p['nx']},ny:{p['ny']},nz:{p['nz']},t:'{p['type']}'}},"
        )
    js_lines.append("];")

    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(js_lines))

    print(f"\nSaved -> {output_path}")
    return len(points)


if __name__ == "__main__":
    export_neuron_js()
