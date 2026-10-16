#!/usr/bin/env python3
"""Author the TEG wedge enclosure as editable code and export STEP + STL.

The wedge carries the TEG array, the hot-side metal interface plate, the
cold-side heatsink/fan and the power board, and holds itself to a metal
fireplace face with SmCo magnets plus mechanical retention. Design intent and
the requirements it must satisfy (REQUIREMENTS.md):

  * P1  the whole printed part fits the Bambu A1 mini 180 mm cube;
  * P2  a flat vertical *hot* face tapers back to the heatsink;
  * T2  printed plastic stays off the hot path - the metal interface plate sits
        in a rebate and never loads the plastic;
  * T5  a thermal-break air gap separates plate and printed pocket;
  * T4  magnet pockets are sized for high-temperature SmCo discs;
  * S2  M3 retention screws are a mechanical backup to the magnets;
  * section 8  the clamp carries the ~1.4 MPa TEG-stack preload.

Run with the repo toolchain (see docs/cad-toolchain.md):

    scripts/cad-run.sh                       # export default part
    scripts/cad-run.sh --params cad/params.json
    scripts/cad-run.sh --out cad/exports --no-render

Outputs (default ``cad/exports/``): ``<stem>.step`` (design interchange) and
``<stem>.stl`` (printable mesh). The STL is what the Bambu print task consumes.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from build123d import (
    Axis,
    Box,
    BuildLine,
    BuildPart,
    BuildSketch,
    Cylinder,
    Plane,
    Polyline,
    Pos,
    Rot,
    export_step,
    export_stl,
    extrude,
    make_face,
    offset,
)

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from parameters import DEFAULTS, WedgeParams  # noqa: E402


# --------------------------------------------------------------------------- #
# geometry
# --------------------------------------------------------------------------- #
def build_wedge(p: WedgeParams):
    """Return a build123d Part for the wedge enclosure."""
    p.validate()

    with BuildPart() as bp:
        # Side profile in the Y-Z plane, extruded across the full width. The
        # profile is a trapezoid: full height at the hot face (Y=0) tapering to
        # ``back_height`` at the back face (Y=depth) - the defining wedge (P2).
        with BuildSketch(Plane.YZ):
            with BuildLine():
                Polyline(
                    (0, 0),
                    (p.depth, 0),
                    (p.depth, p.back_height),
                    (0, p.front_height),
                    (0, 0),
                )
            make_face()
        extrude(amount=p.width / 2, both=True)

        # Hollow it out, open at the bottom (Z=0) so the electronics/TEG stack
        # slide in and the back face stays intact for the fan/heatsink. A
        # negative offset keeps the outer envelope and adds an inward wall.
        bottom = bp.faces().sort_by(Axis.Z)[0]
        offset(openings=bottom, amount=-p.wall)

    part = bp.part

    # -- hot face (Y=0): metal interface-plate rebate + thermal break (T1/T2/T5)
    plate_pocket = Pos(0, p.plate_pocket_depth / 2, p.front_height / 2) * Box(
        p.plate_w, p.plate_pocket_depth, p.plate_h
    )
    part -= plate_pocket

    # -- magnets (T4): four SmCo pockets on the hot-face rim ------------------
    mag_r = (p.magnet_dia + 2 * p.magnet_clearance) / 2
    mag_h = p.magnet_thk + p.magnet_clearance
    mx = p.width / 2 - p.magnet_inset
    mz = p.front_height / 2 - p.magnet_inset
    magnet_centres = [
        (0, 0, p.front_height - p.magnet_inset),   # top edge
        (0, 0, p.magnet_inset),                    # bottom edge
        (-mx, 0, p.front_height / 2),              # left edge
        (mx, 0, p.front_height / 2),               # right edge
    ]
    for cx, _cy, cz in magnet_centres:
        part -= Pos(cx, mag_h / 2, cz) * Rot(X=90) * Cylinder(mag_r, mag_h)

    # -- mechanical retention screws (S2): M3 through-holes at the corners ----
    rx = p.width / 2 - p.retention_inset
    rz = p.front_height / 2 - p.retention_inset
    for sx in (-rx, rx):
        for sz in (p.front_height / 2 - rz, p.front_height / 2 + rz):
            part -= Pos(sx, 10, sz) * Rot(X=90) * Cylinder(
                p.retention_screw_dia / 2, 30
            )

    # -- cold side (Y=depth): fan opening + mounting holes (P5) ---------------
    back_face_y = p.depth
    part -= Pos(0, back_face_y, p.back_height / 2) * Rot(X=90) * Cylinder(
        p.fan_hole_dia / 2, 3 * p.wall
    )
    fan_q = p.fan_mount_pitch / 2
    for fx in (-fan_q, fan_q):
        for fz in (p.back_height / 2 - fan_q, p.back_height / 2 + fan_q):
            part -= Pos(fx, back_face_y, fz) * Rot(X=90) * Cylinder(
                p.fan_mount_dia / 2, 3 * p.wall
            )

    # -- clamp (section 8): bosses + M4 clearance holes carry the 1.4 MPa load -
    # The holes are tapped into the bosses from the *cavity* side (heat-set
    # inserts); they deliberately do not break through the hot face.
    aw, ah = p.teg_array_size()
    boss_x = aw / 2 + p.clamp_boss_dia / 2
    boss_z = ah / 2 + p.clamp_boss_dia / 2
    hole_depth = max(4.0, p.clamp_boss_len - 2.0)
    for bx in (-boss_x, boss_x):
        for bz in (p.front_height / 2 - boss_z, p.front_height / 2 + boss_z):
            part += Pos(bx, p.wall + p.clamp_boss_len / 2, bz) * Rot(X=90) * Cylinder(
                p.clamp_boss_dia / 2, p.clamp_boss_len
            )
            part -= Pos(bx, p.wall + p.clamp_boss_len - hole_depth / 2, bz) * Rot(
                X=90
            ) * Cylinder(p.clamp_screw_dia / 2, hole_depth)

    return part


# --------------------------------------------------------------------------- #
# preview render (best-effort PNG from the exported STL)
# --------------------------------------------------------------------------- #
def render_preview(stl_path: Path, png_path: Path) -> None:
    """Shade the exported binary STL and save a 4-view PNG for review."""
    import struct

    import numpy as np
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from mpl_toolkits.mplot3d.art3d import Poly3DCollection

    with open(stl_path, "rb") as fh:
        fh.read(80)
        (n_tri,) = struct.unpack("<I", fh.read(4))
        raw = np.frombuffer(fh.read(n_tri * 50), dtype=np.uint8)
    rec = raw.reshape(n_tri, 50)
    tris = rec[:, 12:48].copy().view("<f4").reshape(n_tri, 3, 3)

    # Outward normals follow the STL winding; a light behind the camera keeps
    # recesses (magnet pockets, rebate, fan bore) reading as dark holes.
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


# --------------------------------------------------------------------------- #
# reporting
# --------------------------------------------------------------------------- #
def report(p: WedgeParams, part) -> None:
    ok, msg = p.fits_bed()
    bb = part.bounding_box()
    print("wedge enclosure")
    print(f"  envelope (params) : {msg}  -> {'FITS' if ok else 'TOO BIG'}")
    print(f"  solid bbox        : {bb.size.X:.2f} x {bb.size.Y:.2f} x {bb.size.Z:.2f} mm")
    print(f"  volume            : {part.volume / 1000.0:.1f} cm^3")
    print(f"  TEG stack         : {p.teg_count} x TG12-4 "
          f"({p.teg_len} x {p.teg_wid} x {p.teg_thk} mm)")
    print(f"  clamp load        : {p.clamp_pressure_mpa:g} MPa -> "
          f"{p.clamp_force_n():.0f} N total, "
          f"{p.clamp_force_per_screw_n():.0f} N per M4 screw "
          f"({p.clamp_screw_count} screws)")
    floor = p.wall - (p.magnet_thk + p.magnet_clearance)
    print(f"  magnet pocket     : {p.magnet_dia:g} x {p.magnet_thk:g} mm SmCo, "
          f"{floor:.2f} mm floor behind pocket")
    if floor < 1.0:
        raise SystemExit("ERROR: magnet pocket breaks through the front wall (T4)")
    if not ok:
        raise SystemExit("ERROR: part exceeds the printer bed (P1)")


# --------------------------------------------------------------------------- #
# main
# --------------------------------------------------------------------------- #
def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--params", type=Path, help="JSON file overriding defaults")
    ap.add_argument("--out", type=Path, default=HERE / "exports",
                    help="output directory (default cad/exports)")
    ap.add_argument("--no-export", action="store_true",
                    help="build + report only, write nothing")
    ap.add_argument("--no-render", dest="render", action="store_false",
                    help="skip the PNG preview render")
    ap.set_defaults(render=True)
    args = ap.parse_args(argv)

    p = WedgeParams.from_json_file(args.params) if args.params else DEFAULTS
    part = build_wedge(p)
    report(p, part)

    if not args.no_export:
        args.out.mkdir(parents=True, exist_ok=True)
        step_path = args.out / f"{p.export_stem}.step"
        stl_path = args.out / f"{p.export_stem}.stl"
        export_step(part, str(step_path))
        export_stl(part, str(stl_path))
        print(f"  wrote             : {step_path}")
        print(f"  wrote             : {stl_path}")

    if args.render and not args.no_export:
        png = args.out / f"{p.export_stem}.png"
        try:
            render_preview(stl_path, png)
            print(f"  wrote             : {png}")
        except Exception as exc:  # rendering is best-effort, never fatal
            print(f"  render skipped    : {exc}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
