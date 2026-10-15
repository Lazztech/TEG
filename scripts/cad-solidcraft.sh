#!/usr/bin/env bash
# Build the wedge enclosure with SolidCraft (bake-off contender #3) and export.
#
#   scripts/cad-solidcraft.sh                 # build -> STEP + STL + iso PNG
#   scripts/cad-solidcraft.sh --no-export     # build + report only
#
# Downloads the pinned SolidCraft CLI release into .solidcraft/ (gitignored) on
# first run - no root, nothing installed system-wide. The model is the text
# command script cad/bakeoff/solidcraft/wedge.json.
set -euo pipefail
cd "$(dirname "$0")/.."
REPO="$PWD"
VER="0.13.1"
ARCH="linux-x86_64"
DIR="$REPO/.solidcraft/solidcraft-$VER-$ARCH"
CLI="$DIR/bin/solidcraft-cli"
SCRIPT="$REPO/cad/bakeoff/solidcraft/wedge.json"
OUT="$REPO/cad/bakeoff/solidcraft/exports"

if [ ! -x "$CLI" ]; then
    echo "cad-solidcraft: downloading SolidCraft $VER -> .solidcraft/ (gitignored)"
    mkdir -p "$REPO/.solidcraft"
    url="https://github.com/bherbruck/solidcraft/releases/download/v$VER/solidcraft-$VER-$ARCH.tar.gz"
    curl -fLsS -o "$REPO/.solidcraft/solidcraft-$VER-$ARCH.tar.gz" "$url"
    tar xzf "$REPO/.solidcraft/solidcraft-$VER-$ARCH.tar.gz" -C "$REPO/.solidcraft"
fi

if [ "${1:-}" = "--no-export" ]; then
    exec "$CLI" eval "$SCRIPT"
fi

mkdir -p "$OUT"
"$CLI" run "$SCRIPT" \
    --out "$OUT/wedge_enclosure.step" \
    --out "$OUT/wedge_enclosure.stl" \
    --save "$OUT/wedge_enclosure.solidcraft"
"$CLI" snapshot "$SCRIPT" --out "$OUT/wedge_enclosure.png" --view iso
echo "cad-solidcraft: wrote $OUT/wedge_enclosure.{step,stl,png,solidcraft}"
