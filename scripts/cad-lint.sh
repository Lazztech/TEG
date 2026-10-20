#!/usr/bin/env bash
# Static analysis for the code-CAD sources: ruff + mypy (config in pyproject.toml).
#
#   scripts/cad-lint.sh
#
# Needs the repo-local .venv with the dev tools:
#     scripts/cad-setup.sh --dev
set -euo pipefail
cd "$(dirname "$0")/.."
VENV="$PWD/.venv"

if [ ! -x "$VENV/bin/ruff" ] || [ ! -x "$VENV/bin/mypy" ]; then
    echo "cad-lint: dev tools missing - run scripts/cad-setup.sh --dev" >&2
    exit 2
fi

echo "== ruff =="
"$VENV/bin/ruff" check cad tests
echo "== mypy =="
"$VENV/bin/mypy"
