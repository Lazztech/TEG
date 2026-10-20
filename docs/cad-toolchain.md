# CAD toolchain — code-CAD for the TEG wedge and printed parts

An AI agent can author and edit the **wedge enclosure** and its printed parts in
this repository, and export both a **STEP** (design interchange) and a printable
**STL** — with no human in the loop. This document is the contract for that
toolchain: the tool we chose, where the source of truth lives, how exports reach
the print task, and the conventions to follow.

Related: [REQUIREMENTS.md](../REQUIREMENTS.md) (P1–P5, T1–T5, S1–S4 and §8),
issue **LAZ-24**, and the Bambu print task that consumes the STL.

---

## 1. Decision: build123d (code-CAD)

| Option | Verdict |
|--------|---------|
| **build123d / CadQuery** (Python, OpenCASCADE) | **Chosen.** Scriptable, headless, git-diffable source — matches this repo's script-heavy KiCad generators (`scripts/gen_schematic.py`, `scripts/gen_board.py`). |
| FreeCAD | Scriptable, but a heavyweight GUI app to install and drive; no advantage over a bare library here. |
| Onshape | Cloud SaaS; needs a human-owned account and network auth — awkward for unattended agents. |
| Fusion 360 | Cloud, script/API limited, licence-gated. |

**build123d** is a modern layer over the same OCCT kernel as CadQuery and is
under active development, so it is the pick. A model is a Python program: the
geometry diff is the source diff, reviewable in a pull request.

The toolchain is **repo-local and sudo-free**: `scripts/cad-setup.sh` creates
`.venv/` with `uv` and installs `cad/requirements.txt` (build123d + matplotlib).
The only non-Python step is unpacking a few headless GL/X libraries that OCCT
links against but that a server often lacks — still no root.

## 2. Where the source of truth lives

```
cad/
  parameters.py          # every dimension: the single place to edit numbers
  wedge.py               # the model: builds the part, exports STEP/STL/PNG
  requirements.txt       # pinned toolchain
  exports/               # committed build output (see §4)
    wedge_enclosure.step
    wedge_enclosure.stl
    wedge_enclosure.png
scripts/
  cad-setup.sh           # one-time bootstrap of .venv/ + GL libs
  cad-run.sh             # run the model with the right env
```

`cad/parameters.py` is authoritative. `WedgeParams` is a frozen dataclass whose
defaults are the design; `cad/wedge.py` reads it and builds the solid. Changing a
number is the whole diff.

## 3. Running it

```bash
scripts/cad-setup.sh --dev      # once per host: create .venv, install deps + dev tools
scripts/cad-run.sh              # build default part -> cad/exports/*.{step,stl,png}
scripts/cad-run.sh --no-render  # faster, no PNG
scripts/cad-run.sh --params cad/params.json   # override parameters (JSON)
scripts/cad-test.sh             # geometry tests (pytest)
scripts/cad-lint.sh             # ruff + mypy
```

`--params` reads a JSON object whose keys are `WedgeParams` field names; unknown
keys are rejected so a typo cannot silently change nothing:

```json
{ "width": 160.0, "teg_count": 3, "fan_size": 92.0 }
```

The model prints an envelope check and **fails loudly** if the part exceeds the
printer bed (P1) or if a magnet pocket would break through the front wall (T4).

## 4. Export pipeline (how the print task gets its STL)

`cad/wedge.py` writes three files into `cad/exports/`:

| File | Consumer |
|------|----------|
| `wedge_enclosure.step` | Human CAD / editing interchange; re-import into any CAD tool. |
| `wedge_enclosure.stl` | **The printable mesh — the input to the Bambu print task.** |
| `wedge_enclosure.png` | 4-view preview for review in the issue/PR. |

The STL is committed on purpose so the print task (and reviewers) can consume a
fixed artifact without re-running the toolchain. It is a binary STL in
millimetres, exported with the default resolution.

> Conventions for printability: model in **millimetres**, Z up, the open bottom
> on the bed (Z=0). Slicer/printer settings live in the print task, not here.

### 4.1 Validation and CI

Committed exports are checked, not assumed. `scripts/validate.sh --cad` runs
`scripts/validate_cad.py`, which verifies that every committed STL is a closed,
consistently wound, single-body mesh; sits on Z=0 and fits the A1 mini bed;
matches the STEP volume and envelope; and still matches a fresh rebuild of
`cad/wedge.py`. The three bake-off exports must also agree with the canonical
solid. A stale artifact fails with the exact regeneration command.

GitHub Actions runs this on every pull request
([`.github/workflows/validate.yml`](../.github/workflows/validate.yml)) next to
the KiCad ERC/DRC and script-syntax jobs. Full contract:
**[docs/validation.md](validation.md)**.

### 4.2 Code quality gate (ruff, mypy, pytest)

The model is Python, so it is linted and tested like Python — no bespoke CAD
linter required. All three tools are pinned in `cad/requirements-dev.txt` and
configured once in `pyproject.toml`:

| Tool | What it proves | Command |
|------|----------------|---------|
| **ruff** | imports, unused names, bugbear traps, pyupgrade on `cad/` and `tests/` (the archived `cad/bakeoff/` is excluded) | `scripts/cad-lint.sh` |
| **mypy** | type consistency in `cad/parameters.py`, `cad/wedge.py`, `tests/`; kernel bindings are treated as a trusted third-party surface | `scripts/cad-lint.sh` |
| **pytest** | the *solid*, not the source: one valid body, envelope vs the 180 mm bed, wall thickness, rebate depth, four magnet pockets with an intact floor, retention holes, fan bore/mounts, clamp bosses, §8 clamp load, and a golden volume | `scripts/cad-test.sh` |

The two halves are complementary: `validate_cad.py` checks the committed
*artifacts* (watertight mesh, STEP↔STL agreement, freshness), while pytest checks
the *generated solid* feature by feature, so a broken feature fails with a named
test rather than as a volume drift.

`pre-commit` runs lint on commit and the geometry tests on push
(`.pre-commit-config.yaml`, using the repo `.venv`), and CI runs both in the
`quality` job.

## 5. Conventions

- **Units:** millimetres everywhere.
- **Axes:** X = width, Y = depth (0 at the hot face), Z = height (0 at the base).
  See the docstring in `cad/parameters.py`.
- **One part, one module.** The wedge is `cad/wedge.py`; add further printed
  parts as sibling modules and export them the same way.
- **No magic numbers in `wedge.py`** — derive from `WedgeParams`; if a value is
  needed, add a field (with a unit comment) to `parameters.py`.
- **Best-effort render.** Preview rendering never fails the build.
- **Estimates are marked.** Values not yet datasheet-verified carry `(estimate)`,
  matching the convention in `REQUIREMENTS.md`.

## 6. How the model maps to requirements

| Requirement | How the model satisfies it |
|-------------|----------------------------|
| **P1** fits the A1 mini 180³ bed | `fits_bed()` checks the envelope; default 150 × 55 × 150 mm. The build aborts if it grows past the bed. |
| **P2** wedge | Trapezoid profile: full height (150 mm) at the flat hot face, tapering to 100 mm at the cold-side back face. |
| **P5** fan-forced cooling | Ø76 mm fan bore + 71.5 mm Noctua NF-A8 mounting holes in the back face. |
| **T1/T2/T5** keep plastic off the hot path | The *metal* interface plate sits in a 96 × 96 mm rebate in the front face; printed plastic never bears the hot face, and a `thermal_break_gap` air gap separates plate and pocket. |
| **T4** SmCo magnets survive | Four 10 × 3 mm magnet pockets in the front rim; the build refuses if the pocket floor is under 1 mm. |
| **S2** mechanical retention | Four M3 through-holes at the corners as a positive backup to the magnets. |
| **§8** clamp the TEG stack at 1.4 MPa | Four M4 clamp bosses carry the load; the model reports total force (~2857 N) and per-screw load. |

## 7. §8 clamp load (why the bosses are there)

The Coherent TG12-4 datasheet specifies a **1.4 MPa (200 psi)** clamp on the
module's 34.01 × 30 mm face. With two modules that is ~**2.9 kN** — a real
mechanical load the enclosure carries, not a suggestion. The four M4 bosses take
~714 N each; the clamp plate that presses the stack is a separate part (metal),
not modelled here.

## 8. Status & next steps

- ✅ Tool chosen (build123d, confirmed by the user), source layout established,
      exports wired.
- ✅ Parameterised wedge builds and exports STEP + STL, fits the bed.
- ✅ Committed artifacts validated in CI (manifold mesh, bed fit, STEP↔STL,
      bake-off agreement, stale-export rebuild).
- ✅ Code-quality gate: ruff + mypy (static) and pytest (geometry), wired into
      pre-commit and a dedicated CI job; printable STL/STEP/PNG uploaded as
      workflow artifacts.
- ✅ GUI/editor review path: VS Code OCP CAD Viewer for live preview, FreeCAD
      for independent STEP inspection (§11).
- ⬜ **Hand the STL to the Bambu print task** (sibling issue) — the artifact is
  committed in `cad/exports/`.
- ⬜ Extract the TG12-4 mechanical drawing (datasheet p.3) to confirm the module
  footprint and the array envelope (see REQUIREMENTS.md open items 5).
- ⬜ Choose the SmCo magnet grade once the fireplace surface temperature is known
  (T4).
- ⬜ Split the enclosure into front/back shells and add the metal interface plate
  and clamp plate as their own parts.
- ⬜ 3MF export. build123d 0.13 ships the Lib3MF binding but has no
  `export_3mf()` one-liner; the Bambu print task consumes STL today. Add a small
  exporter when a multi-object/print-settings 3MF is actually needed.

## 9. Bake-off: the same wedge in four tools

On the user's request, the enclosure is also authored with three more
agent-drivable tools so the result can be judged by review and print quality —
same parameters, four tools. See **[cad/bakeoff/README.md](../cad/bakeoff/README.md)**.

| Tool | Kernel | Source | Exports |
|------|--------|--------|---------|
| build123d | OCCT | `cad/wedge.py` | `cad/exports/` |
| CadQuery | OCCT | `cad/bakeoff/cadquery/wedge_cq.py` | `cad/bakeoff/cadquery/exports/` |
| SolidCraft | truck | `cad/bakeoff/solidcraft/wedge.json` | `cad/bakeoff/solidcraft/exports/` |
| FreeCAD | OCCT | `cad/bakeoff/freecad/wedge_fc.py` | `cad/bakeoff/freecad/exports/` |

```bash
scripts/cad-run-cadquery.sh   # bootstrap: scripts/cad-setup-cadquery.sh
scripts/cad-solidcraft.sh     # downloads a pinned SolidCraft CLI into .solidcraft/
scripts/cad-run-freecad.sh    # downloads a pinned FreeCAD AppImage into .freecad/
```

All four fit the bed and agree on the solid to <0.01% volume. build123d keeps the
canonical `cad/exports/` that the print task consumes.

## 10. Prior art in this repo

The KiCad pipeline already proves the pattern this toolchain follows: **source is
a script, output is generated**. `scripts/gen_board.py` regenerates `TEG.kicad_pcb`
the same way `cad/wedge.py` regenerates the STEP/STL. Keep CAD source and exports
in the same commit.

## 11. Editing and review in a GUI

The workflow is **code-first with a live viewer**. No mature tool round-trips
click-and-drag edits back into build123d source, so the source of truth stays the
Python; the GUI is for looking, measuring and reviewing.

### VS Code — OCP CAD Viewer (primary)

The extension is recommended in `.vscode/extensions.json`
(`bernhard-42.ocp-cad-viewer`). It renders both build123d and CadQuery and
refreshes when the script runs.

```bash
uv pip install --python .venv/bin/python ocp-vscode   # Python side, matches the extension
```

```python
from ocp_vscode import show
from wedge import build_wedge
from parameters import DEFAULTS

show(build_wedge(DEFAULTS))
```

- **Ctrl-F5** (Run Without Debugging) rebuilds and re-renders.
- **F5** (Start Debugging) steps through the model with the view updating, which
  is how to find the operation that produced a bad face.
- The viewer shows exact topology (faces/edges), supports sectioning, and
  measures volume and bounding box on the tessellated mesh.

On a headless Linux box, start VS Code from a shell that has the GL path
exported (the same one `scripts/cad-run.sh` sets):

```bash
export LD_LIBRARY_PATH="$PWD/.venv/gl-libs/usr/lib/x86_64-linux-gnu"
code .
```

### FreeCAD (secondary, independent review)

Open `cad/exports/wedge_enclosure.step` in FreeCAD 1.x for a second opinion in a
mature B-Rep GUI: inspect faces, take measurements, check the rebate and magnet
pockets, and export a drawing if needed. FreeCAD is deliberately **not** the
source of truth: `.FCStd` is a zip container that git cannot diff usefully, and
its scripting API has no advantage over build123d for headless agents.

## 12. Agent tooling evaluated (not adopted as the toolchain)

Two community projects were checked against this workflow. Both are useful and
neither replaces the git + lint + test pipeline above.

### text-to-cad — `earthtojake/text-to-cad`

| | |
|---|---|
| **Licence** | MIT |
| **Activity** | Created 2026-04-22; ~22k stars, ~2.2k forks; release **v0.7.25** and commits on 2026-10-20 (actively developed) |
| **What it is** | A library of agent skills (Claude Code, Codex, Cursor, Gemini, Grok, or the Skills CLI) plus a local MCP server and browser CAD viewer. The CAD skill wraps **build123d / OpenCASCADE** and exports **STEP, STL, 3MF, GLB**; other skills cover DfAM checks, engineering drawings, DXF, G-code slicing with OrcaSlicer, **Bambu Labs handoff** (Bambu Connect / Bambu Studio), SendCutSend, and DFM |
| **Requirements** | `uv`, Python 3.11+, Node 20+; telemetry is on by default (`uvx cadgen telemetry off`) |
| **Fit** | **Strong complement, not a replacement.** It is exactly the agent-facing CAD/fabrication layer we would otherwise build, and its Bambu and slicing skills directly serve the print handoff (LAZ-23). But it is 0.x with near-daily releases, ships its own runtime/daemon, and does not own our source, lint or tests |

**Recommendation:** pilot it on the next physical print — pinned (`cadgen==0.7.26`),
telemetry off — as the slicer/Bambu handoff, keeping `cad/wedge.py` and this
repo's gates as the source of truth. Do not make it the toolchain until it is 1.x
and we have a printer profile worth encoding.

### vcad — `ecto/vcad`

| | |
|---|---|
| **Licence** | Apache-2.0 |
| **Activity** | Created 2026-01-27; ~440 stars, 130 open issues; latest **tagged** release v0.9.4 (2026-04-29) though commits land daily |
| **What it is** | A Rust/WASM **B-Rep kernel** with web, desktop and CLI surfaces, an `@vcad/mcp` server, assemblies, simulation, STEP import and STL/GLB/STEP/DXF export (no 3MF) |
| **Fit** | This is the "web + desktop + CLI for humans and agents" model. **Experimental:** 0.x, small community, a large open-issue count, and no tagged release in ~6 months despite daily commits |

**Recommendation:** watchlist. Re-evaluate at 1.0, and only if it adds 3MF and a
credible assembly/mates story; switching a working kernel for an unproven one is
the opposite of the maturity goal.
