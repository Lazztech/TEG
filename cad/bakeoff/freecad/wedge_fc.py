#!/usr/bin/env python3
"""Author the TEG wedge enclosure in FreeCAD — LAZ-24 tool bake-off, contender #4.

A faithful port of the build123d model (``cad/wedge.py``) using FreeCAD's
``Part`` scripting API, so the four tools are compared on the same design and the
same shared parameters (``cad/parameters.py``). Read that file for the intent and
the requirements mapping (P1–P5, T1–T5, S2, §8).

Coordinate convention (matches ``cad/parameters.py``):
  * X = width, Y = depth (0 at the hot face), Z = height (0 at the bed).

Run headless with FreeCAD's console binary (see cad/bakeoff/freecad/README.md):

    scripts/cad-run-freecad.sh                 # build + export STEP/STL
    scripts/cad-run-freecad.sh --no-export     # build + report only
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import FreeCAD
import Mesh
import MeshPart
import Part
from FreeCAD import Vector

HERE = Path(__file__).resolve().parent
CAD = HERE.parents[1]  # .../cad
sys.path.insert(0, str(CAD))
from parameters import DEFAULTS, WedgeParams  # noqa: E402


def _ycyl(radius: float, y0: float, height: float, x: float, z: float) -> Part.Shape:
    """A cylinder along +Y from ``y0`` of length ``height`` centred at (x, z)."""
    return Part.makeCylinder(radius, height, Vector(x, y0, z), Vector(0, 1, 0))


def build_wedge(p: WedgeParams) -> Part.Shape:
    p.validate()

    # -- wedge profile (P2) in the Y-Z plane, extruded across the width --------
    outline = [
        Vector(0, 0, 0),
        Vector(0, p.depth, 0),
        Vector(0, p.depth, p.back_height),
        Vector(0, 0, p.front_height),
        Vector(0, 0, 0),
    ]
    profile = Part.Face(Part.makePolygon(outline))
    part = profile.extrude(Vector(p.width, 0, 0)).translate(Vector(-p.width / 2, 0, 0))

    # -- hollow it out, open at the bottom (Z=0) ------------------------------
    bottom = [f for f in part.Faces if abs(f.normalAt(0, 0).z + 1.0) < 1e-6]
    part = part.makeThickness(bottom, -p.wall, 1e-4)

    # -- hot face (Y=0): metal interface-plate rebate + thermal break ----------
    rebate = Part.makeBox(
        p.plate_w,
        p.plate_pocket_depth,
        p.plate_h,
        Vector(-p.plate_w / 2, 0, p.front_height / 2 - p.plate_h / 2),
    )
    part = part.cut(rebate)

    # -- magnets (T4): four SmCo pockets on the hot-face rim ------------------
    mag_r = (p.magnet_dia + 2 * p.magnet_clearance) / 2
    mag_h = p.magnet_thk + p.magnet_clearance
    mx = p.width / 2 - p.magnet_inset
    for cx, cz in [
        (0, p.front_height - p.magnet_inset),
        (0, p.magnet_inset),
        (-mx, p.front_height / 2),
        (mx, p.front_height / 2),
    ]:
        part = part.cut(_ycyl(mag_r, 0.0, mag_h, cx, cz))

    # -- mechanical retention screws (S2): M3 through-holes at the corners ----
    rx = p.width / 2 - p.retention_inset
    rz = p.front_height / 2 - p.retention_inset
    for sx in (-rx, rx):
        for sz in (p.front_height / 2 - rz, p.front_height / 2 + rz):
            part = part.cut(_ycyl(p.retention_screw_dia / 2, -5.0, 30.0, sx, sz))

    # -- cold side (Y=depth): fan opening + mounting holes (P5) ---------------
    part = part.cut(
        _ycyl(p.fan_hole_dia / 2, p.depth - 1.5 * p.wall, 3 * p.wall, 0,
              p.back_height / 2)
    )
    fan_q = p.fan_mount_pitch / 2
    for fx in (-fan_q, fan_q):
        for fz in (p.back_height / 2 - fan_q, p.back_height / 2 + fan_q):
            part = part.cut(
                _ycyl(p.fan_mount_dia / 2, p.depth - 1.5 * p.wall, 3 * p.wall,
                      fx, fz)
            )

    # -- clamp (§8): bosses + M4 clearance holes carry the 1.4 MPa stack load -
    aw, ah = p.teg_array_size()
    boss_x = aw / 2 + p.clamp_boss_dia / 2
    boss_z = ah / 2 + p.clamp_boss_dia / 2
    hole_depth = max(4.0, p.clamp_boss_len - 2.0)
    for bx in (-boss_x, boss_x):
        for bz in (p.front_height / 2 - boss_z, p.front_height / 2 + boss_z):
            part = part.fuse(
                _ycyl(p.clamp_boss_dia / 2, p.wall, p.clamp_boss_len, bx, bz)
            )
            part = part.cut(
                _ycyl(p.clamp_screw_dia / 2, p.wall + p.clamp_boss_len - hole_depth,
                      hole_depth, bx, bz)
            )

    return part


def report(p: WedgeParams, part: Part.Shape) -> None:
    ok, msg = p.fits_bed()
    bb = part.BoundBox
    print("wedge enclosure (FreeCAD)")
    print(f"  envelope (params) : {msg}  -> {'FITS' if ok else 'TOO BIG'}")
    print(f"  solid bbox        : {bb.XLength:.2f} x {bb.YLength:.2f} x "
          f"{bb.ZLength:.2f} mm")
    print(f"  volume            : {part.Volume / 1000.0:.1f} cm^3")
    floor = p.wall - (p.magnet_thk + p.magnet_clearance)
    print(f"  magnet pocket     : {p.magnet_dia:g} x {p.magnet_thk:g} mm SmCo, "
          f"{floor:.2f} mm floor behind pocket")
    if floor < 1.0:
        raise RuntimeError("ERROR: magnet pocket breaks through the front wall (T4)")
    if not ok:
        raise RuntimeError("ERROR: part exceeds the printer bed (P1)")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--params", type=Path, help="JSON file overriding defaults")
    ap.add_argument("--out", type=Path, default=HERE / "exports",
                    help="output directory (default cad/bakeoff/freecad/exports)")
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
        part.exportStep(str(step_path))
        # A binary STL with a controlled tessellation (matching the CadQuery
        # tolerance); Shape.exportStl writes a very fine ASCII mesh by default.
        mesh = MeshPart.meshFromShape(
            Shape=part, LinearDeflection=0.1, AngularDeflection=0.3, Relative=False
        )
        mesh.write(str(stl_path))
        print(f"  wrote             : {step_path} ({mesh.CountFacets} facets)")
        print(f"  wrote             : {stl_path}")
    return 0


# freecadcmd executes this file with ``__name__`` set to the script stem (not
# "__main__") and with sys.argv = [freecadcmd, script.py, ("--pass",) ...args].
# Run unconditionally and parse the args that follow the script path.
_argv = sys.argv[1:]
if _argv and _argv[0].endswith("wedge_fc.py"):
    _argv = _argv[1:]
main([a for a in _argv if a != "--pass"])
sys.stdout.flush()  # SystemExit would truncate buffered stdout under freecadcmd
