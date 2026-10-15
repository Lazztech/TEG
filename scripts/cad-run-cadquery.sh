#!/usr/bin/env bash
# Run the CadQuery model with the bake-off toolchain (.venv-cadquery/).
#
#   scripts/cad-run-cadquery.sh                 # build + export STEP/STL
#   scripts/cad-run-cadquery.sh --no-export     # build + report only
#   scripts/cad-run-cadquery.sh --params cad/params.json
#
# Installs nothing; run scripts/cad-setup-cadquery.sh once first.
set -euo pipefail
cd "$(dirname "$0")/.."
REPO="$PWD"
VENV="$REPO/.venv-cadquery"

if [ ! -x "$VENV/bin/python" ]; then
    echo "cad-run-cadquery: no .venv-cadquery yet - run scripts/cad-setup-cadquery.sh first" >&2
    exit 1
fi

export LD_LIBRARY_PATH="$REPO/.venv/gl-libs/usr/lib/x86_64-linux-gnu${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
exec "$VENV/bin/python" "$REPO/cad/bakeoff/cadquery/wedge_cq.py" "$@"
