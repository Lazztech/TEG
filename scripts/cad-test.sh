#!/usr/bin/env bash
# Geometry tests for the code-CAD sources (pytest, config in pyproject.toml).
#
#   scripts/cad-test.sh                 # all tests
#   scripts/cad-test.sh tests/test_wedge.py -k magnet
#
# Sets the headless GL/X library path that OpenCASCADE needs, then runs pytest.
set -euo pipefail
cd "$(dirname "$0")/.."
VENV="$PWD/.venv"

if [ ! -x "$VENV/bin/python" ]; then
    echo "cad-test: no .venv yet - run scripts/cad-setup.sh --dev first" >&2
    exit 2
fi
if [ ! -x "$VENV/bin/pytest" ]; then
    echo "cad-test: pytest missing - run scripts/cad-setup.sh --dev" >&2
    exit 2
fi

export LD_LIBRARY_PATH="$VENV/gl-libs/usr/lib/x86_64-linux-gnu${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
exec "$VENV/bin/python" -m pytest "$@"
