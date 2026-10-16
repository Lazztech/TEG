# CAD tool bake-off — the same wedge enclosure in four tools (LAZ-24)

The same enclosure, designed four times with four agent-drivable tools, so the
result can be judged by **review and print quality** rather than by description.
All four read the **same parameters** (`cad/parameters.py`), so this is an
apples-to-apples comparison of the tools, not of four different designs.

| # | Tool | Kernel | Model source | Exports |
|---|------|--------|--------------|---------|
| 1 | **build123d** | OpenCASCADE (OCCT) | `cad/wedge.py` (Python, builder API) | `cad/exports/` |
| 2 | **CadQuery** | OpenCASCADE (OCCT) | `cad/bakeoff/cadquery/wedge_cq.py` (Python, fluent API) | `cad/bakeoff/cadquery/exports/` |
| 3 | **SolidCraft** | `truck` (Rust) | `cad/bakeoff/solidcraft/wedge.json` (JSON commands) | `cad/bakeoff/solidcraft/exports/` |
| 4 | **FreeCAD** | OpenCASCADE (OCCT) | `cad/bakeoff/freecad/wedge_fc.py` (Python `Part` API) | `cad/bakeoff/freecad/exports/` |

These are the tools from the LAZ-24 evaluation that meet the hard requirement
(3D solids, STEP + printable STL, text source in the repo, agent-drivable).
CADCraft was evaluated and excluded — it is 2D drafting only. SolidCraft also
drives an MCP server (agent-native); the others are driven by writing Python/JSON.

## The design

A faithful port of the build123d model in `cad/wedge.py` — read that file's
docstring for the intent and the requirements mapping (P1–P5, T1–T5, S2, §8).
Coordinate convention: X = width, Y = depth (0 at the hot face), Z = height
(0 at the bed).

## Running each tool

```bash
scripts/cad-setup.sh && scripts/cad-run.sh                     # 1. build123d  (.venv)
scripts/cad-setup-cadquery.sh && scripts/cad-run-cadquery.sh   # 2. CadQuery  (.venv-cadquery, py3.12)
scripts/cad-solidcraft.sh                                      # 3. SolidCraft (.solidcraft/, pinned CLI)
scripts/cad-run-freecad.sh                                     # 4. FreeCAD   (.freecad/, pinned AppImage)
```

Preview PNGs are rendered from each exported STL by `cad/bakeoff/render_stl.py`
(run with the build123d `.venv`, which has matplotlib) so the previews look
alike. SolidCraft renders its own PNG via its `snapshot` command.

## Results (default parameters)

| Tool | Envelope (mm) | Volume | STEP | STL | STL triangles |
|------|---------------|--------|------|-----|---------------|
| build123d | 150 × 55 × 150 | 248.4 cm³ | 152 KB | 586 KB | 12,008 |
| CadQuery | 150 × 55 × 150 | 248.4 cm³ | 175 KB | 685 KB | 14,016 |
| SolidCraft | 150 × 55 × 150 | 248.38 cm³ | 173 KB | 273 KB | 5,588 |
| FreeCAD | 150 × 55 × 150 | 248.4 cm³ | 54 KB | 201 KB | 4,112 |

All four fit the Bambu A1 mini 180³ bed, meet the magnet-floor check, and agree
on the solid to <0.01% volume (the kernels tessellate the same B-rep differently,
so the meshes differ in triangle count, not in shape).

### Observations

- **build123d, CadQuery and FreeCAD** all run on the OCCT kernel and produce the
  same solid; only the Python API differs (builder contexts, fluent `Workplane`,
  and FreeCAD's `Part` shapes). Ports were mostly mechanical, with a couple of
  real gotchas (see each tool's README): CadQuery's `extrude(.., both=True)` means
  *distance in each direction*; FreeCAD 1.1 dropped `makeThickSolidByJoin` in
  favour of `shape.makeThickness`, and `freecadcmd` runs scripts with
  `__name__` set to the file stem.
- **SolidCraft** matched the OCCT geometry to rounding with its own `truck`
  kernel and produced the smallest, coarsest mesh. Its model is a plain JSON
  command script; a sketch on the `XZ` plane has its local v-axis pointing **−Z**.
- FreeCAD wrote by far the smallest STEP (54 KB) and the fewest STL triangles;
  build123d/CadQuery tessellate more finely at their defaults.

## What to review / print

Each tool's `exports/` holds `wedge_enclosure.step` (design interchange) and
`wedge_enclosure.stl` (printable mesh). **The STL is the thing to print.** Slice
all four for the A1 mini and compare the printed result — part fit, the magnet
pockets and rebate, the fan bore, and how cleanly the thin walls print.

Print settings live with the print task, not here; this repo is source + the
committed artifacts.

## Scope / status

- Proven: all four tools build the enclosure headless and export STEP + STL.
- build123d keeps its canonical output at `cad/exports/` (what the Bambu print
  task consumes); the bake-off contenders export under `cad/bakeoff/<tool>/`.
- Open: pick the winner after printing; then possibly split the enclosure into
  shells and add the metal interface / clamp plates (see `docs/cad-toolchain.md`).
