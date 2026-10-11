#!/usr/bin/env bash
# Render 3D views of the board (parts included) into build/render/.
# KiCad's 3D view shows the board, silkscreen and component bodies - NOT the copper
# traces (they sit under the soldermask); use the gerbers/PDF for those.
set -uo pipefail
cd "$(dirname "$0")/.."
KC="${KICAD_CLI:-$HOME/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli}"
[ -x "$KC" ] || { echo "kicad-cli not found (set KICAD_CLI)" >&2; exit 1; }
mkdir -p build/render
V=(-w 2000 -h 1400 --quality high --perspective)

"$KC" pcb render --side top    "${V[@]}" --floor --zoom 1.05 -o build/render/TEG-top.png hardware/TEG.kicad_pcb
"$KC" pcb render --side top    "${V[@]}" --floor --rotate -35,0,25 --zoom 1.15 -o build/render/TEG-isometric.png hardware/TEG.kicad_pcb
"$KC" pcb render --side bottom "${V[@]}" --floor --zoom 1.05 -o build/render/TEG-bottom.png hardware/TEG.kicad_pcb
"$KC" pcb render --side top    --w 1800 --h 1400 --quality high --perspective --floor \
      --rotate -30,0,20 --zoom 2.6 --pivot "-1.9,-1.5,0" -o build/render/TEG-harvester-closeup.png hardware/TEG.kicad_pcb
echo "renders in build/render/"
