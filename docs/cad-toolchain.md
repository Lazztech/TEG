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
scripts/cad-setup.sh            # once per host: create .venv, install deps
scripts/cad-run.sh              # build default part -> cad/exports/*.{step,stl,png}
scripts/cad-run.sh --no-render  # faster, no PNG
scripts/cad-run.sh --params cad/params.json   # override parameters (JSON)
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

- ✅ Tool chosen (build123d), source layout established, exports wired.
- ✅ Parameterised wedge builds and exports STEP + STL, fits the bed.
- ✅ Committed artifacts validated in CI (manifold mesh, bed fit, STEP↔STL,
      bake-off agreement, stale-export rebuild).
- ⬜ **Hand the STL to the Bambu print task** (sibling issue) — the artifact is
  committed in `cad/exports/`.
- ⬜ Extract the TG12-4 mechanical drawing (datasheet p.3) to confirm the module
  footprint and the array envelope (see REQUIREMENTS.md open items 5).
- ⬜ Choose the SmCo magnet grade once the fireplace surface temperature is known
  (T4).
- ⬜ Split the enclosure into front/back shells and add the metal interface plate
  and clamp plate as their own parts.

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
