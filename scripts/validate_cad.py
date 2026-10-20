#!/usr/bin/env python3
"""Validate the committed CAD artifacts against their source and print constraints.

This is the mechanical-CAD half of ``scripts/validate.sh`` and the job that runs
in CI. It answers the questions a reviewer would otherwise check by hand:

  * do the committed STEP/STL files exist and parse?
  * is each STL a closed, consistently wound, single-body triangle mesh?
  * does it sit on Z=0 and fit the Bambu A1 mini bed (P1)?
  * does the mesh volume/area/envelope match the build123d solid (stale export?)
  * do the bake-off contenders still agree with the canonical solid?
  * do the STEP files re-import to the same solid?

Usage:
    scripts/validate_cad.py                 # artifacts only (needs build123d for STEP)
    scripts/validate_cad.py --rebuild       # also rebuild the model and compare
    scripts/validate_cad.py --repo /tmp/x   # validate another checkout
    scripts/validate_cad.py --json build/cad-validation.json

Exit codes: 0 = pass, 1 = validation failure, 2 = toolchain/environment error.
"""

from __future__ import annotations

import argparse
import json
import math
import struct
import sys
import tempfile
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

# Tolerances. The bake-off tools disagree at the 1e-4 relative level, so these
# are tight enough to catch a stale export or a dropped feature but loose enough
# not to depend on a kernel version's triangulation.
WELD_DECIMALS = 4          # weld coincident STL vertices at 0.1 um
VOLUME_REL_TOL = 0.002     # 0.2 %
AREA_REL_TOL = 0.002       # 0.2 %
BBOX_ABS_TOL = 0.05        # mm
BED_TOL = 0.05             # mm
CONTENDER_REL_TOL = 0.002  # bake-off solids must agree with the canonical one


@dataclass
class Model:
    name: str
    source: str
    stl: Path
    step: Path


@dataclass
class Mesh:
    triangles: list[tuple[tuple[float, float, float], ...]]
    binary: bool
    bbox_min: tuple[float, float, float]
    bbox_max: tuple[float, float, float]
    volume: float  # cm^3
    area: float    # mm^2

    @property
    def size(self) -> tuple[float, float, float]:
        return tuple(self.bbox_max[i] - self.bbox_min[i] for i in range(3))


@dataclass
class Result:
    name: str
    ok: bool = True
    errors: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    facts: dict = field(default_factory=dict)

    def fail(self, message: str) -> None:
        self.ok = False
        self.errors.append(message)

    def note(self, message: str) -> None:
        self.notes.append(message)


def rel_err(actual: float, expected: float) -> float:
    if expected == 0:
        return abs(actual)
    return abs(actual - expected) / abs(expected)


def read_stl(path: Path) -> Mesh:
    data = path.read_bytes()
    if len(data) >= 84:
        (n_tri,) = struct.unpack("<I", data[80:84])
        if 84 + n_tri * 50 == len(data):
            triangles = []
            for i in range(n_tri):
                off = 84 + i * 50
                vals = struct.unpack("<12f", data[off:off + 48])
                triangles.append(
                    (vals[3:6], vals[6:9], vals[9:12])  # type: ignore[arg-type]
                )
            return summarize(triangles, binary=True)

    text = data.decode("utf-8", errors="replace")
    if "facet" not in text or "vertex" not in text:
        raise ValueError("not a binary or ASCII STL")
    verts = []
    for line in text.splitlines():
        parts = line.split()
        if parts[:1] == ["vertex"] and len(parts) >= 4:
            verts.append(tuple(float(x) for x in parts[1:4]))
    if not verts or len(verts) % 3:
        raise ValueError(f"ASCII STL has {len(verts)} vertices (not a multiple of 3)")
    triangles = [tuple(verts[i:i + 3]) for i in range(0, len(verts), 3)]
    return summarize(triangles, binary=False)


def summarize(triangles, binary: bool) -> Mesh:
    if not triangles:
        raise ValueError("STL contains no triangles")
    pts = [v for tri in triangles for v in tri]
    lo = tuple(min(p[i] for p in pts) for i in range(3))
    hi = tuple(max(p[i] for p in pts) for i in range(3))

    volume6 = 0.0
    area = 0.0
    for a, b, c in triangles:
        volume6 += (
            a[0] * (b[1] * c[2] - b[2] * c[1])
            - a[1] * (b[0] * c[2] - b[2] * c[0])
            + a[2] * (b[0] * c[1] - b[1] * c[0])
        )
        ux, uy, uz = b[0] - a[0], b[1] - a[1], b[2] - a[2]
        vx, vy, vz = c[0] - a[0], c[1] - a[1], c[2] - a[2]
        cx, cy, cz = uy * vz - uz * vy, uz * vx - ux * vz, ux * vy - uy * vx
        area += 0.5 * math.sqrt(cx * cx + cy * cy + cz * cz)
    return Mesh(
        triangles=triangles,
        binary=binary,
        bbox_min=lo,
        bbox_max=hi,
        volume=abs(volume6) / 6.0 / 1000.0,
        area=area,
    )


def weld(v: tuple[float, float, float], q: int) -> tuple[int, int, int]:
    return (round(v[0] * q), round(v[1] * q), round(v[2] * q))


class DisjointSet:
    def __init__(self) -> None:
        self.parent: dict[tuple[int, int, int], tuple[int, int, int]] = {}

    def add(self, item):
        self.parent.setdefault(item, item)

    def find(self, item):
        root = item
        while self.parent[root] != root:
            root = self.parent[root]
        while self.parent[item] != root:
            self.parent[item], item = root, self.parent[item]
        return root

    def union(self, a, b) -> None:
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.parent[rb] = ra


def check_mesh(mesh: Mesh, result: Result, params) -> None:
    q = 10 ** WELD_DECIMALS
    keys = [[weld(v, q) for v in tri] for tri in mesh.triangles]

    degenerate = sum(1 for t in keys if len(set(t)) < 3)
    if degenerate:
        result.fail(f"{degenerate} degenerate triangle(s) (zero area)")

    directed: Counter = Counter()
    for tri in keys:
        for a, b in ((0, 1), (1, 2), (2, 0)):
            directed[(tri[a], tri[b])] += 1

    duplicated = sum(1 for count in directed.values() if count > 1)
    open_edges = sum(1 for (a, b) in directed if (b, a) not in directed)
    if duplicated or open_edges:
        result.fail(
            "mesh is not a closed, consistently wound surface "
            f"({open_edges} open edge(s), {duplicated} duplicated directed edge(s))"
        )

    ds = DisjointSet()
    for tri in keys:
        for a, b in ((0, 1), (1, 2), (2, 0)):
            ds.add(tri[a])
            ds.add(tri[b])
            ds.union(tri[a], tri[b])
    bodies = len({ds.find(k) for k in ds.parent})
    if bodies != 1:
        result.fail(f"mesh has {bodies} disconnected bodies (expected 1)")
    result.facts["bodies"] = bodies
    result.facts["triangles"] = len(mesh.triangles)
    result.facts["watertight"] = not (duplicated or open_edges or degenerate)

    lo = mesh.bbox_min
    hi = mesh.bbox_max
    if abs(lo[2]) > BED_TOL:
        result.fail(f"part does not sit on the bed: min Z = {lo[2]:.3f} mm (expected 0)")
    bed = (params.bed_x, params.bed_y, params.bed_z)
    for axis, label in enumerate("XYZ"):
        if mesh.size[axis] > bed[axis] + BED_TOL:
            result.fail(
                f"envelope {label} = {mesh.size[axis]:.2f} mm exceeds the "
                f"{bed[axis]:g} mm bed (P1)"
            )
    if hi[1] > params.depth + BED_TOL or lo[1] < -BED_TOL:
        result.note(f"Y span {lo[1]:.2f}..{hi[1]:.2f} mm (hot face at Y=0)")

    result.facts["envelope_mm"] = [round(x, 3) for x in mesh.size]
    result.facts["volume_cm3"] = round(mesh.volume, 3)
    result.facts["area_mm2"] = round(mesh.area, 1)


def check_step(model: Model, mesh: Mesh, result: Result) -> None:
    try:
        from build123d import import_step
    except Exception as exc:  # noqa: BLE001 - report, do not crash
        result.note(f"STEP check skipped: build123d unavailable ({exc})")
        return

    try:
        shape = import_step(str(model.step))
    except Exception as exc:  # noqa: BLE001
        result.fail(f"cannot import {model.step.name}: {exc}")
        return

    step_vol = shape.volume / 1000.0
    bb = shape.bounding_box()
    step_size = (bb.size.X, bb.size.Y, bb.size.Z)
    if rel_err(step_vol, mesh.volume) > VOLUME_REL_TOL:
        result.fail(
            f"STEP volume {step_vol:.3f} cm^3 differs from STL "
            f"{mesh.volume:.3f} cm^3 (limit {VOLUME_REL_TOL:.1%})"
        )
    for axis, label in enumerate("XYZ"):
        if abs(step_size[axis] - mesh.size[axis]) > BBOX_ABS_TOL:
            result.fail(
                f"STEP {label} size {step_size[axis]:.3f} mm differs from STL "
                f"{mesh.size[axis]:.3f} mm"
            )
    result.facts["step_volume_cm3"] = round(step_vol, 3)


def brep_available() -> bool:
    try:
        import build123d  # noqa: F401
        return True
    except Exception:  # noqa: BLE001
        return False


def rebuild(model: Model, params, result: Result, tmp: Path) -> Mesh | None:
    try:
        from build123d import export_stl
        from wedge import build_wedge
    except Exception as exc:  # noqa: BLE001
        result.note(f"rebuild skipped: build123d unavailable ({exc})")
        return None

    part = build_wedge(params)
    out = tmp / f"{model.name}.stl"
    export_stl(part, str(out))
    fresh = read_stl(out)

    brep_volume = part.volume / 1000.0
    result.facts["rebuilt_volume_cm3"] = round(brep_volume, 3)
    result.facts["rebuilt_stl_volume_cm3"] = round(fresh.volume, 3)
    if rel_err(fresh.volume, brep_volume) > VOLUME_REL_TOL:
        result.fail(
            f"rebuilt STL volume {fresh.volume:.3f} cm^3 disagrees with the "
            f"B-rep {brep_volume:.3f} cm^3"
        )
    return fresh


def compare_fresh(model: Model, committed: Mesh, fresh: Mesh, result: Result) -> None:
    if rel_err(fresh.volume, committed.volume) > VOLUME_REL_TOL:
        result.fail(
            f"committed STL is stale: volume {committed.volume:.3f} cm^3 vs "
            f"rebuilt {fresh.volume:.3f} cm^3 - run scripts/cad-run.sh"
        )
    if rel_err(fresh.area, committed.area) > AREA_REL_TOL:
        result.fail(
            f"committed STL is stale: surface area {committed.area:.1f} mm^2 vs "
            f"rebuilt {fresh.area:.1f} mm^2 - run scripts/cad-run.sh"
        )
    for axis, label in enumerate("XYZ"):
        if abs(fresh.size[axis] - committed.size[axis]) > BBOX_ABS_TOL:
            result.fail(
                f"committed STL is stale: {label} size {committed.size[axis]:.2f} mm "
                f"vs rebuilt {fresh.size[axis]:.2f} mm - run scripts/cad-run.sh"
            )


def parse_args(argv: list[str] | None) -> argparse.Namespace:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument(
        "--repo",
        type=Path,
        default=Path(__file__).resolve().parent.parent,
        help="repository root (default: this checkout)",
    )
    ap.add_argument("--rebuild", action="store_true",
                    help="rebuild the canonical model and fail if exports are stale")
    ap.add_argument("--no-step", action="store_true",
                    help="skip STEP re-import checks")
    ap.add_argument("--require-brep", action="store_true",
                    help="fail if build123d/OCP is unavailable instead of skipping")
    ap.add_argument("--json", type=Path, help="write a machine-readable report here")
    return ap.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    repo: Path = args.repo.resolve()
    sys.path.insert(0, str(repo / "cad"))
    from parameters import DEFAULTS  # noqa: E402

    params = DEFAULTS
    models = [
        Model("build123d", "cad/wedge.py",
              repo / "cad/exports/wedge_enclosure.stl",
              repo / "cad/exports/wedge_enclosure.step"),
        Model("cadquery", "cad/bakeoff/cadquery/wedge_cq.py",
              repo / "cad/bakeoff/cadquery/exports/wedge_enclosure.stl",
              repo / "cad/bakeoff/cadquery/exports/wedge_enclosure.step"),
        Model("solidcraft", "cad/bakeoff/solidcraft/wedge.json",
              repo / "cad/bakeoff/solidcraft/exports/wedge_enclosure.stl",
              repo / "cad/bakeoff/solidcraft/exports/wedge_enclosure.step"),
        Model("freecad", "cad/bakeoff/freecad/wedge_fc.py",
              repo / "cad/bakeoff/freecad/exports/wedge_enclosure.stl",
              repo / "cad/bakeoff/freecad/exports/wedge_enclosure.step"),
    ]

    results: list[Result] = []
    meshes: dict[str, Mesh] = {}

    # -- parameter invariants (the same ones the model enforces) -------------
    prm = Result("parameters")
    try:
        params.validate()
    except Exception as exc:  # noqa: BLE001
        prm.fail(f"invalid parameter set: {exc}")
    ok, msg = params.fits_bed()
    if not ok:
        prm.fail(f"parameter envelope does not fit the bed: {msg}")
    floor = params.wall - (params.magnet_thk + params.magnet_clearance)
    if floor < 1.0:
        prm.fail(f"magnet pocket floor {floor:.2f} mm < 1 mm (T4)")
    prm.facts.update(
        envelope_mm=[round(x, 3) for x in params.bounding_box()],
        bed_mm=[params.bed_x, params.bed_y, params.bed_z],
        magnet_floor_mm=round(floor, 3),
        clamp_force_n=round(params.clamp_force_n(), 0),
    )
    results.append(prm)

    has_brep = brep_available()
    tmp_ctx = tempfile.TemporaryDirectory(prefix="cad-validate-")
    tmp = Path(tmp_ctx.name)
    try:
        for model in models:
            result = Result(model.name)
            try:
                if not model.stl.is_file():
                    result.fail(f"missing STL {model.stl.relative_to(repo)}")
                if not model.step.is_file():
                    result.fail(f"missing STEP {model.step.relative_to(repo)}")
                if not result.ok:
                    results.append(result)
                    continue

                mesh = read_stl(model.stl)
                meshes[model.name] = mesh
                check_mesh(mesh, result, params)
                result.facts["binary_stl"] = mesh.binary
                result.facts["source"] = model.source
                expected = params.bounding_box()
                for axis, label in enumerate("XYZ"):
                    if abs(mesh.size[axis] - expected[axis]) > BBOX_ABS_TOL:
                        result.fail(
                            f"{label} envelope {mesh.size[axis]:.2f} mm does not "
                            f"match the parameters ({expected[axis]:.2f} mm)"
                        )

                if not args.no_step:
                    check_step(model, mesh, result)

            except Exception as exc:  # noqa: BLE001
                result.fail(f"validation error: {exc}")
            results.append(result)

        # -- all models must agree with the canonical solid ------------------
        if "build123d" in meshes:
            canonical = meshes["build123d"]
            for name, mesh in meshes.items():
                if name == "build123d":
                    continue
                result = next(r for r in results if r.name == name)
                if rel_err(mesh.volume, canonical.volume) > CONTENDER_REL_TOL:
                    result.fail(
                        f"volume {mesh.volume:.3f} cm^3 disagrees with build123d "
                        f"{canonical.volume:.3f} cm^3"
                    )
                for axis, label in enumerate("XYZ"):
                    if abs(mesh.size[axis] - canonical.size[axis]) > BBOX_ABS_TOL:
                        result.fail(
                            f"{label} envelope disagrees with build123d: "
                            f"{mesh.size[axis]:.2f} vs {canonical.size[axis]:.2f} mm"
                        )

        # -- rebuild the canonical part and compare --------------------------
        if args.rebuild:
            result = next(r for r in results if r.name == "build123d")
            try:
                fresh = rebuild(models[0], params, result, tmp)
            except Exception as exc:  # noqa: BLE001
                result.fail(f"rebuild failed: {exc}")
                fresh = None
            if fresh is not None and "build123d" in meshes:
                compare_fresh(models[0], meshes["build123d"], fresh, result)
    finally:
        tmp_ctx.cleanup()

    if args.require_brep and not has_brep:
        results.append(Result(
            "toolchain",
            ok=False,
            errors=["build123d/OCP is required for STEP validation but is unavailable"],
        ))

    failed = [r for r in results if not r.ok]
    for result in results:
        status = "PASS" if result.ok else "FAIL"
        facts = ", ".join(f"{k}={v}" for k, v in result.facts.items())
        print(f"[{status}] {result.name}" + (f"  ({facts})" if facts else ""))
        for note in result.notes:
            print(f"         note: {note}")
        for error in result.errors:
            print(f"         error: {error}")

    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(json.dumps(
            {
                "ok": not failed,
                "repo": str(repo),
                "params": {
                    "envelope_mm": list(params.bounding_box()),
                    "bed_mm": [params.bed_x, params.bed_y, params.bed_z],
                },
                "results": [
                    {
                        "name": r.name,
                        "ok": r.ok,
                        "facts": r.facts,
                        "notes": r.notes,
                        "errors": r.errors,
                    }
                    for r in results
                ],
            },
            indent=2,
            sort_keys=True,
        ) + "\n")
        print(f"report: {args.json}")

    if failed:
        print(f"\n{len(failed)} check(s) failed", file=sys.stderr)
        return 1
    print("\nall CAD artifact checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
