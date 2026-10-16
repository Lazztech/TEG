#!/usr/bin/env bash
# Build the wedge enclosure with FreeCAD (bake-off contender #4) and export.
#
#   scripts/cad-run-freecad.sh                 # build -> STEP + STL
#   scripts/cad-run-freecad.sh --no-export     # build + report only
#
# Downloads the pinned FreeCAD AppImage into .freecad/ (gitignored) on first run
# and unpacks it (--appimage-extract, no FUSE, no root). The model is the Python
# script cad/bakeoff/freecad/wedge_fc.py, run by FreeCAD's headless `freecadcmd`.
set -euo pipefail
cd "$(dirname "$0")/.."
REPO="$PWD"
VER="1.1.4"
ARCH="Linux-x86_64-py311"
CLI="$REPO/.freecad/squashfs-root/usr/bin/freecadcmd"
SCRIPT="$REPO/cad/bakeoff/freecad/wedge_fc.py"

if [ ! -x "$CLI" ]; then
    echo "cad-run-freecad: downloading FreeCAD $VER AppImage -> .freecad/ (gitignored)"
    mkdir -p "$REPO/.freecad"
    curl -fLsS -o "$REPO/.freecad/FreeCAD.AppImage" \
        "https://github.com/FreeCAD/FreeCAD/releases/download/$VER/FreeCAD_$VER-$ARCH.AppImage"
    chmod +x "$REPO/.freecad/FreeCAD.AppImage"
    ( cd "$REPO/.freecad" && ./FreeCAD.AppImage --appimage-extract >/dev/null )
fi

# freecadcmd parses its own options first; --pass forwards the rest to the script.
exec "$CLI" "$SCRIPT" --pass "$@"
