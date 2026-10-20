# cad/ — code-CAD for the printed parts

The wedge enclosure and other printed mechanical parts are authored **in code**
with [build123d](https://build123d.readthedocs.io/), not in a GUI. Source is a
program, so a change is a reviewable diff and an agent can drive it end to end.

- `parameters.py` — every dimension (the single source of truth).
- `wedge.py` — the wedge model; exports `exports/wedge_enclosure.{step,stl,png}`.
- `exports/` — committed build output. The **STL feeds the Bambu print task**.
- `requirements.txt` — pinned model toolchain; `requirements-dev.txt` adds
  ruff, mypy and pytest for the quality gate.

```bash
scripts/cad-setup.sh --dev   # once: create .venv/ and install deps (no sudo)
scripts/cad-run.sh           # build + export
scripts/cad-lint.sh          # ruff + mypy
scripts/cad-test.sh          # geometry tests
```

For live review, open the model in VS Code with the **OCP CAD Viewer** extension
(pinned in `.vscode/extensions.json`); see
[docs/cad-toolchain.md §10](../docs/cad-toolchain.md#10-editing-and-review-in-a-gui).

Full contract, conventions, and the requirements mapping:
**[docs/cad-toolchain.md](../docs/cad-toolchain.md)**.
