#!/usr/bin/env bash
# Run the CAD model with the repo-local toolchain (build123d in .venv/).
#
#   scripts/cad-run.sh                              # build default part, export
#   scripts/cad-run.sh --no-render                  # skip the PNG preview
#   scripts/cad-run.sh --params cad/params.json     # override parameters
#   scripts/cad-run.sh --out cad/exports            # output directory
#
# Installs nothing; run scripts/cad-setup.sh once first.
set -euo pipefail
cd "$(dirname "$0")/.."
REPO="$PWD"
VENV="$REPO/.venv"

if [ ! -x "$VENV/bin/python" ]; then
    echo "cad-run: no .venv yet - run scripts/cad-setup.sh first" >&2
    exit 1
fi

export LD_LIBRARY_PATH="$VENV/gl-libs/usr/lib/x86_64-linux-gnu${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
exec "$VENV/bin/python" "$REPO/cad/wedge.py" "$@"
