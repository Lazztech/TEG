#!/usr/bin/env python3
"""Render a 4-view preview PNG from a binary STL — used by the CAD bake-off.

Standalone (numpy + matplotlib only) so it can shade an STL from *any* of the
bake-off tools without importing that tool's CAD kernel. The shading and view
list match ``cad/wedge.py`` so all three tools' previews look alike.

    .venv/bin/python cad/bakeoff/render_stl.py IN.stl OUT.png
"""

from __future__ import annotations

import struct
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from mpl_toolkits.mplot3d.art3d import Poly3DCollection  # noqa: E402


def load_binary_stl(path: Path) -> np.ndarray:
    with open(path, "rb") as fh:
        fh.read(80)
        (n_tri,) = struct.unpack("<I", fh.read(4))
        raw = np.frombuffer(fh.read(n_tri * 50), dtype=np.uint8)
    return raw.reshape(n_tri, 50)[:, 12:48].copy().view("<f4").reshape(n_tri, 3, 3)


def render(stl_path: Path, png_path: Path) -> None:
    tris = load_binary_stl(stl_path)
    light = np.array([0.3, -0.8, 0.5])
    light = light / np.linalg.norm(light)
    normals = np.cross(tris[:, 1] - tris[:, 0], tris[:, 2] - tris[:, 0])
    norm = np.linalg.norm(normals, axis=1, keepdims=True)
    norm[norm == 0] = 1.0
    shade = np.clip((normals / norm) @ light, 0.12, 1.0)
    pts = tris.reshape(-1, 3)
    lo, hi = pts.min(0), pts.max(0)
    ctr, span = (lo + hi) / 2, (hi - lo).max() * 0.55
    base_col = plt.cm.Blues(np.clip(shade, 0.0, 1.0))
    views = [
        ("isometric", 25, -55),
        ("hot face (front)", 0, -90),
        ("cold face (back)", 0, 90),
        ("top", 89, -90),
    ]
    fig = plt.figure(figsize=(11, 11), dpi=130)
    for i, (name, elev, azim) in enumerate(views, 1):
        ax = fig.add_subplot(2, 2, i, projection="3d")
        ax.add_collection3d(
            Poly3DCollection(tris, facecolors=base_col, edgecolors="none")
        )
        ax.view_init(elev=elev, azim=azim)
        ax.set_xlim(ctr[0] - span, ctr[0] + span)
        ax.set_ylim(ctr[1] - span, ctr[1] + span)
        ax.set_zlim(ctr[2] - span, ctr[2] + span)
        ax.set_box_aspect((1, 1, 1))
        ax.set_title(name, fontsize=10)
        ax.set_axis_off()
    fig.tight_layout()
    fig.savefig(png_path, transparent=False, facecolor="white")
    plt.close(fig)


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit(__doc__.splitlines()[-1])
    render(Path(sys.argv[1]), Path(sys.argv[2]))
    print(f"rendered {sys.argv[2]}")
