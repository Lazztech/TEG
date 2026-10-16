#!/usr/bin/env python3
"""Author the TEG wedge enclosure in CadQuery — LAZ-24 tool bake-off, contender #2.

This is a **faithful port** of the build123d model (`cad/wedge.py`) so the three
tools are compared on the same design and the same shared parameters
(`cad/parameters.py`). Read the intent, the requirements mapping (P1–P5, T1–T5,
S2, §8) and the coordinate convention there; only the API differs here.

    Workplane "YZ": local x -> global Y (depth), local y -> global Z (height).

Run with the CadQuery toolchain (see cad/bakeoff/README.md):

    scripts/cad-run-cadquery.sh                 # build + export STEP/STL
    scripts/cad-run-cadquery.sh --no-export     # build + report only

Outputs (default ``cad/bakeoff/cadquery/exports``): ``<stem>.step`` and
``<stem>.stl``. The STL is what a print/review task consumes.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import cadquery as cq

HERE = Path(__file__).resolve().parent
CAD = HERE.parents[1]  # .../cad
sys.path.insert(0, str(CAD))
from parameters import DEFAULTS, WedgeParams  # noqa: E402


# --------------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------------- #
def _ycyl(radius: float, height: float, centre: tuple[float, float, float]):
    """A cylinder whose axis is global +Y, length ``height`` centred on ``centre``.

    CadQuery's ``extrude(.., both=True)`` extrudes that distance in *each*
    direction, so halve it to get a total length of ``height`` — matching
    build123d's centred ``Cylinder(radius, height)``.
    """
    return (
        cq.Workplane("XY")
        .circle(radius)
        .extrude(height / 2, both=True)
        .rotate((0, 0, 0), (1, 0, 0), 90)
        .translate(centre)
    )


# --------------------------------------------------------------------------- #
# geometry
# --------------------------------------------------------------------------- #
def build_wedge(p: WedgeParams):
    """Return a CadQuery Workplane/solid for the wedge enclosure."""
    p.validate()

    # -- wedge profile (P2) in the YZ plane, extruded across the width ---------
    part = (
        cq.Workplane("YZ")
        .moveTo(0, 0)
        .lineTo(p.depth, 0)
        .lineTo(p.depth, p.back_height)
        .lineTo(0, p.front_height)
        .close()
        .extrude(p.width / 2, both=True)
    )

    # -- hollow it out, open at the bottom (Z=0) ------------------------------
    part = part.faces("<Z").shell(-p.wall)

    # -- hot face (Y=0): metal interface-plate rebate + thermal break (T1/T2/T5)
    rebate = (
        cq.Workplane("XY")
        .box(p.plate_w, p.plate_pocket_depth, p.plate_h)
        .translate((0, p.plate_pocket_depth / 2, p.front_height / 2))
    )
    part = part.cut(rebate)

    # -- magnets (T4): four SmCo pockets on the hot-face rim ------------------
    mag_r = (p.magnet_dia + 2 * p.magnet_clearance) / 2
    mag_h = p.magnet_thk + p.magnet_clearance
    mx = p.width / 2 - p.magnet_inset
    magnet_centres = [
        (0, mag_h / 2, p.front_height - p.magnet_inset),  # top edge
        (0, mag_h / 2, p.magnet_inset),                   # bottom edge
        (-mx, mag_h / 2, p.front_height / 2),             # left edge
        (mx, mag_h / 2, p.front_height / 2),              # right edge
    ]
    for c in magnet_centres:
        part = part.cut(_ycyl(mag_r, mag_h, c))

    # -- mechanical retention screws (S2): M3 through-holes at the corners ----
    rx = p.width / 2 - p.retention_inset
    rz = p.front_height / 2 - p.retention_inset
    for sx in (-rx, rx):
        for sz in (p.front_height / 2 - rz, p.front_height / 2 + rz):
            part = part.cut(_ycyl(p.retention_screw_dia / 2, 30, (sx, 10, sz)))

    # -- cold side (Y=depth): fan opening + mounting holes (P5) ---------------
    part = part.cut(
        _ycyl(p.fan_hole_dia / 2, 3 * p.wall, (0, p.depth, p.back_height / 2))
    )
    fan_q = p.fan_mount_pitch / 2
    for fx in (-fan_q, fan_q):
        for fz in (p.back_height / 2 - fan_q, p.back_height / 2 + fan_q):
            part = part.cut(
                _ycyl(p.fan_mount_dia / 2, 3 * p.wall, (fx, p.depth, fz))
            )

    # -- clamp (§8): bosses + M4 clearance holes carry the 1.4 MPa stack load -
    aw, ah = p.teg_array_size()
    boss_x = aw / 2 + p.clamp_boss_dia / 2
    boss_z = ah / 2 + p.clamp_boss_dia / 2
    hole_depth = max(4.0, p.clamp_boss_len - 2.0)
    for bx in (-boss_x, boss_x):
        for bz in (p.front_height / 2 - boss_z, p.front_height / 2 + boss_z):
            part = part.union(
                _ycyl(
                    p.clamp_boss_dia / 2,
                    p.clamp_boss_len,
                    (bx, p.wall + p.clamp_boss_len / 2, bz),
                )
            )
            part = part.cut(
                _ycyl(
                    p.clamp_screw_dia / 2,
                    hole_depth,
                    (bx, p.wall + p.clamp_boss_len - hole_depth / 2, bz),
                )
            )

    return part


def report(p: WedgeParams, part) -> None:
    ok, msg = p.fits_bed()
    bb = part.val().BoundingBox()
    print("wedge enclosure (CadQuery)")
    print(f"  envelope (params) : {msg}  -> {'FITS' if ok else 'TOO BIG'}")
    print(f"  solid bbox        : {bb.xlen:.2f} x {bb.ylen:.2f} x {bb.zlen:.2f} mm")
    print(f"  volume            : {part.val().Volume() / 1000.0:.1f} cm^3")
    floor = p.wall - (p.magnet_thk + p.magnet_clearance)
    print(f"  magnet pocket     : {p.magnet_dia:g} x {p.magnet_thk:g} mm SmCo, "
          f"{floor:.2f} mm floor behind pocket")
    if floor < 1.0:
        raise SystemExit("ERROR: magnet pocket breaks through the front wall (T4)")
    if not ok:
        raise SystemExit("ERROR: part exceeds the printer bed (P1)")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--params", type=Path, help="JSON file overriding defaults")
    ap.add_argument("--out", type=Path, default=HERE / "exports",
                    help="output directory (default cad/bakeoff/cadquery/exports)")
    ap.add_argument("--no-export", action="store_true",
                    help="build + report only, write nothing")
    args = ap.parse_args(argv)

    p = WedgeParams.from_json_file(args.params) if args.params else DEFAULTS
    part = build_wedge(p)
    report(p, part)

    if not args.no_export:
        args.out.mkdir(parents=True, exist_ok=True)
        step_path = args.out / f"{p.export_stem}.step"
        stl_path = args.out / f"{p.export_stem}.stl"
        cq.exporters.export(part, str(step_path))
        cq.exporters.export(part, str(stl_path), tolerance=0.1, angularTolerance=0.1)
        print(f"  wrote             : {step_path}")
        print(f"  wrote             : {stl_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
