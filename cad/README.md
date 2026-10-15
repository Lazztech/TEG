# cad/ — code-CAD for the printed parts

The wedge enclosure and other printed mechanical parts are authored **in code**
with [build123d](https://build123d.readthedocs.io/), not in a GUI. Source is a
program, so a change is a reviewable diff and an agent can drive it end to end.

- `parameters.py` — every dimension (the single source of truth).
- `wedge.py` — the wedge model; exports `exports/wedge_enclosure.{step,stl,png}`.
- `exports/` — committed build output. The **STL feeds the Bambu print task**.

```bash
scripts/cad-setup.sh   # once: create .venv/ and install deps (no sudo)
scripts/cad-run.sh     # build + export
```

Full contract, conventions, and the requirements mapping:
**[docs/cad-toolchain.md](../docs/cad-toolchain.md)**.
