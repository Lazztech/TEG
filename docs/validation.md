# Validation pipeline — what CI checks, and how to run it locally

Every push to `main` and every pull request runs
[`.github/workflows/validate.yml`](../.github/workflows/validate.yml). The same
checks run locally through one entry point:

```bash
scripts/cad-setup.sh --dev  # once per host: .venv with build123d, ruff, mypy, pytest
scripts/cad-lint.sh         # ruff + mypy on the model code
scripts/cad-test.sh         # geometry tests on the generated solid
scripts/validate.sh         # CAD artifacts + KiCad ERC/DRC
scripts/validate.sh --cad   # mechanical CAD only
scripts/validate.sh --hardware   # ERC/DRC only
```

Exit codes: `0` pass, `1` validation failure, `2` a required toolchain is
missing. The job split mirrors the two toolchains, so a CAD failure and a KiCad
failure are reported independently.

## Jobs

| Job | Toolchain | Command |
|-----|-----------|---------|
| `cad` | Python 3.13 + pinned `build123d` in `.venv/` | `scripts/validate.sh --cad` |
| `quality` | same `.venv` + pinned `ruff`/`mypy`/`pytest` | `scripts/cad-lint.sh`, then `scripts/cad-test.sh` |
| `hardware` | KiCad 10 (`kicad-cli`) from the official PPA | `scripts/validate.sh --hardware`, then `scripts/fab_export.sh` |
| `scripts` | Python + bash | `bash -n` every script, `compileall` the Python sources |

The CAD job uploads `build/cad-validation.json` and the printable artifacts
(`cad/exports/wedge_enclosure.{stl,step,png}`). The hardware job uploads the
full ERC/DRC reports (`build/erc-all.rpt`, `build/drc-all.rpt`, plus the
error-gated `build/erc.rpt` and `build/drc.rpt`) and the generated JLCPCB
package (`TEG-gerbers.zip`, BOM, CPL). Everything is retained as run artifacts
for review evidence.

## What the CAD checks prove

`scripts/validate_cad.py` checks the **committed** artifacts, not just a fresh
build:

1. **Parameters are valid** — `WedgeParams.validate()`, bed fit (P1), and the
   magnet pocket floor (T4, must stay ≥ 1 mm).
2. **Artifacts exist and parse** — `wedge_enclosure.step` and `.stl` for the
   canonical build123d model.
3. **The STL is printable geometry** — binary/ASCII parsing, no degenerate
   triangles, every edge shared by exactly two oppositely wound triangles, and
   a single connected body. Vertices are welded at 0.1 µm first, because STL is
   a triangle soup and exporters do not share vertices.
4. **It fits the printer** — millimetre envelope, sits on `Z=0`, and fits the
   Bambu A1 mini 180 mm cube.
5. **STEP and STL agree** — the STEP re-imports through OCCT and matches the
   mesh volume (0.2 %) and envelope (0.05 mm).
6. **The exports are fresh** (`--rebuild`) — the canonical model is rebuilt in a
   temp directory and its STL volume, surface area, and envelope must match the
   committed STL. This is what catches "I changed `parameters.py` but forgot to
   re-run `scripts/cad-run.sh`".

Tolerances are deliberately loose enough to survive OCCT version skew and
different tessellation of the same B-rep, but tight enough that a dropped
feature or stale export fails.

### Fixing a CAD failure

| Failure | Fix |
|---------|-----|
| `committed STL is stale` | `scripts/cad-run.sh` then commit `cad/exports/` |
| `mesh is not a closed ... surface` | Re-export the STL; if it persists, the source solid is not manifold |
| `envelope ... exceeds the ... bed` | Change `cad/parameters.py`; the model refuses to build an oversized part |
| `STEP volume ... differs from STL` | Re-export both from the same source revision |
| `missing STL/STEP` | Restore the artifact or add the newly introduced process to the registry in `scripts/validate_cad.py` |
| `.venv` missing | `scripts/cad-setup.sh` |

## What the hardware checks prove

`scripts/validate.sh --hardware` runs `kicad-cli sch erc` and
`kicad-cli pcb drc`. The **error** severity gates the build; warnings are
reported and do not fail it. The repo currently carries two known cosmetic
warnings, documented in [README.md](../README.md#opening-the-project):

- 3 × `lib_symbol_mismatch` on recently fetched symbols (embedded text is
  byte-identical to the library),
- 1 × `silk_overlap` on the 8 mm electrolytic's reference text.

Anything at error severity, or any non-`0`/`5` `kicad-cli` exit (which means a
tool/IO failure rather than a violation), fails the job.

After ERC/DRC the job runs `scripts/fab_export.sh`, which exercises the whole
manufacturing export path: Gerbers, Excellon drill, pick-and-place, the JLCPCB
CPL, the BOM restricted to the CPL designators, and the zipped upload package.
It **does not order anything**; the package is uploaded as a build artifact for
review. The ordering gate in
[docs/jlcpcb-fabrication.md](jlcpcb-fabrication.md) is unchanged.

## Deliberately out of scope

The pipeline does not slice the STL or simulate the print, does not order
boards or parts, and does not validate datasheet claims. Those stay human
review and approval steps. It also does not check 3D renders/PNGs — those are
best-effort previews, not manufacturing artifacts.
