#!/usr/bin/env bash
# Bootstrap the CadQuery toolchain for the LAZ-24 bake-off (contender #2), no sudo.
#
#   scripts/cad-setup-cadquery.sh
#
# Creates .venv-cadquery/ (Python 3.12 - cadquery-ocp has no 3.13 wheels yet) and
# installs cad/bakeoff/cadquery/requirements.txt. Reuses the headless GL/X
# libraries that scripts/cad-setup.sh staged for the build123d toolchain (both
# use the OpenCASCADE kernel). Idempotent - safe to re-run.
set -euo pipefail
cd "$(dirname "$0")/.."
REPO="$PWD"
VENV="$REPO/.venv-cadquery"

say() { printf 'cad-setup-cadquery: %s\n' "$*"; }

if ! command -v uv >/dev/null 2>&1; then
    export PATH="$HOME/.local/bin:$PATH"
fi
if ! command -v uv >/dev/null 2>&1; then
    say "installing uv to ~/.local/bin"
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.local/bin:$PATH"
fi

# OCCT (cadquery-ocp) links the same headless GL/X libraries as build123d.
if [ ! -e "$REPO/.venv/gl-libs/usr/lib/x86_64-linux-gnu/libGL.so.1" ]; then
    say "staging headless GL/X libraries via scripts/cad-setup.sh"
    scripts/cad-setup.sh
fi

if [ ! -x "$VENV/bin/python" ]; then
    say "creating virtualenv at .venv-cadquery (python 3.12)"
    uv venv --python 3.12 "$VENV"
fi
say "installing cad/bakeoff/cadquery/requirements.txt"
uv pip install --python "$VENV/bin/python" -r "$REPO/cad/bakeoff/cadquery/requirements.txt"

export LD_LIBRARY_PATH="$REPO/.venv/gl-libs/usr/lib/x86_64-linux-gnu${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
"$VENV/bin/python" - <<'PY'
import cadquery
print("cad-setup-cadquery: cadquery", cadquery.__version__, "imports OK (via scripts/cad-run-cadquery.sh)")
PY
say "done - run 'scripts/cad-run-cadquery.sh'"
