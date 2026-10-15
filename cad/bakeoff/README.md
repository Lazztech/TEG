# CAD tool bake-off — the same wedge enclosure in three tools (LAZ-24)

The same enclosure, designed three times with three agent-drivable tools, so the
result can be judged by **review and print quality** rather than by description.
All three read the **same parameters** (`cad/parameters.py`), so this is an
apples-to-apples comparison of the tools, not of three different designs.

| # | Tool | Kernel | Model source | Status exports |
|---|------|--------|--------------|----------------|
| 1 | **build123d** | OpenCASCADE (OCCT) | Python code — `cad/wedge.py` | `cad/exports/` |
| 2 | **CadQuery** | OpenCASCADE (OCCT) | Python code — `cad/bakeoff/cadquery/wedge_cq.py` | `cad/bakeoff/cadquery/exports/` |
| 3 | **SolidCraft** | `truck` (Rust) | JSON command script — `cad/bakeoff/solidcraft/wedge.json` | `cad/bakeoff/solidcraft/exports/` |

These are the three tools from the LAZ-24 evaluation that meet the hard
requirement (3D solids, STEP + printable STL, text source in the repo,
agent-drivable). CADCraft was evaluated and excluded — it is 2D drafting only.
SolidCraft additionally drives an MCP server (agent-native); build123d/CadQuery
are driven by writing Python.

## The design

A faithful port of the build123d model in `cad/wedge.py` — read that file's
docstring for the intent and the requirements mapping (P1–P5, T1–T5, S2, §8).
Coordinate convention: X = width, Y = depth (0 at the hot face), Z = height
(0 at the bed).

## Running each tool

```bash
# 1. build123d (repo-local .venv)
scripts/cad-setup.sh && scripts/cad-run.sh

# 2. CadQuery (separate .venv-cadquery; python 3.12)
scripts/cad-setup-cadquery.sh && scripts/cad-run-cadquery.sh

# 3. SolidCraft (downloads a pinned CLI release into .solidcraft/)
scripts/cad-solidcraft.sh
```

Preview PNGs are rendered from the exported STL by `cad/bakeoff/render_stl.py`
(run with the build123d `.venv`, which has matplotlib) so all three previews
look alike. SolidCraft renders its own PNG via its `snapshot` command.

## Results (default parameters)

| Tool | Envelope (mm) | Volume | STEP | STL | STL triangles |
|------|---------------|--------|------|-----|---------------|
| build123d | 150 × 55 × 150 | 248.4 cm³ | 152 KB | 586 KB | 12,008 |
| CadQuery | 150 × 55 × 150 | 248.4 cm³ | 175 KB | 685 KB | 14,016 |
| SolidCraft | 150 × 55 × 150 | 248.38 cm³ | 173 KB | 273 KB | 5,588 |

All three fit the Bambu A1 mini 180³ bed, meet the magnet-floor check, and agree
on the solid to <0.01% volume (the three kernels tessellate the same B-rep
differently, so the meshes differ in triangle count, not in shape).

### Observations

- **build123d vs CadQuery** run on the same OCCT kernel and produce the same
  solid; only the Python API differs (build123d's builder contexts vs CadQuery's
  fluent `Workplane`). The wedge port was mostly mechanical — the one real
  gotcha was CadQuery's `extrude(.., both=True)` meaning *distance in each
  direction*, so cylinders are built at half length.
- **SolidCraft** matched the OCCT geometry to rounding with its own `truck`
  kernel and produced the smallest, coarsest mesh (fewest triangles). Its model
  is a plain JSON command script; the one coordinate gotcha is that a sketch on
  the `XZ` plane has its local v-axis pointing **−Z**, so Z values are negated.

## What to review / print

Each tool's `exports/` holds `wedge_enclosure.step` (design interchange) and
`wedge_enclosure.stl` (printable mesh). **The STL is the thing to print.** Slice
all three for the A1 mini and compare the printed result — part fit, the magnet
pockets and rebate, the fan bore, and how cleanly the thin walls print.

Print settings live with the print task, not here; this repo is source + the
committed artifacts.

## Scope / status

- Proven: all three tools build the enclosure headless and export STEP + STL.
- build123d keeps its canonical output at `cad/exports/` (what the Bambu print
  task consumes); the bake-off contenders export under `cad/bakeoff/<tool>/`.
- Open: pick the winner after printing; then possibly split the enclosure into
  shells and add the metal interface / clamp plates (see `docs/cad-toolchain.md`).
