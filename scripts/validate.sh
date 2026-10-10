#!/usr/bin/env bash
# Validate the generated KiCad files with kicad-cli (ERC + DRC).
# Usage: scripts/validate.sh
set -uo pipefail
cd "$(dirname "$0")/.."

KICAD_CLI="$(command -v kicad-cli || echo "$HOME/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli")"
echo "using: $KICAD_CLI"
"$KICAD_CLI" version

echo "== ERC (schematic) =="
"$KICAD_CLI" sch erc hardware/TEG.kicad_sch --severity-all --exit-code-violations -o build/erc.rpt || true
cat build/erc.rpt

echo "== DRC (board) =="
"$KICAD_CLI" pcb drc hardware/TEG.kicad_pcb --severity-all --exit-code-violations -o build/drc.rpt || true
cat build/drc.rpt

echo "done"
