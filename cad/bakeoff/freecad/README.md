# FreeCAD contender — the wedge enclosure as a Python Part script

`wedge_fc.py` builds the enclosure with FreeCAD's `Part` scripting API and
exports STEP + a binary STL. It reads the same shared parameters as the other
tools (`cad/parameters.py`), so it is the same design as contenders #1–#3.

- **Tool:** [FreeCAD](https://github.com/FreeCAD/FreeCAD) 1.1.4 — scriptable via
  its Python API, headless through the `freecadcmd` console binary.
- **Pin / install:** `scripts/cad-run-freecad.sh` downloads the pinned AppImage
  into `.freecad/` (gitignored) and unpacks it — no FUSE, no root.
- **Exports:** `exports/wedge_enclosure.{step,stl,png}`.

```bash
scripts/cad-run-freecad.sh              # build -> STEP + STL
scripts/cad-run-freecad.sh --no-export  # measure only
```

## Conventions / gotchas found while authoring

- Coordinate system matches `cad/parameters.py`: X = width, Y = depth (0 at the
  hot face), Z = height (0 at the bed). The profile is drawn in the `x = 0`
  plane as the trapezoid `(0,0) → (depth,0) → (depth,back_height) →
  (0,front_height)` in (Y,Z), extruded along +X.
- Cut the rebate/bores with `Part.makeCylinder(radius, height, pnt, dir)` so the
  cylinders point along +Y without a separate rotation.
- **Shell:** FreeCAD 1.1 has no `Part.makeThickSolidByJoin`; use the shape
  method `shape.makeThickness(faces, -wall, tol)` with the bottom face selected.
- **freecadcmd quirk:** it runs the file with `__name__` set to the script stem
  (not `"__main__"`) and `sys.argv = [freecadcmd, script.py, ...]`, so the script
  runs its entry point unconditionally and parses args after the script path.
  Also `raise SystemExit` truncates buffered stdout — flush instead.
- **STL:** `Shape.exportStl` writes a very fine ASCII mesh; the script uses
  `MeshPart.meshFromShape(...).write(...)` for a compact binary STL.
