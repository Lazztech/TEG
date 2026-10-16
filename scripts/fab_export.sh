#!/usr/bin/env bash
# Produce a review-ready JLCPCB fabrication + assembly package for a KiCad board in
# one command:
#
#   * Gerbers + Excellon drill (+ .gbrjob)  -> build/fab/<BASE>-gerbers.zip  (PCB upload)
#   * JLCPCB BOM  -> build/fab/<BASE>-BOM-jlcpcb.csv   (assembly step)
#   * JLCPCB CPL  -> build/fab/<BASE>-CPL-jlcpcb.csv   (assembly step)
#
# It does NOT place an order. Ordering is a separate, human-approved step; see
# docs/jlcpcb-fabrication.md and keep any spend behind the approval gate.
#
# Usage:
#   scripts/fab_export.sh [BOARD] [OUTDIR] [--tht]
#     BOARD    KiCad .kicad_pcb (default: hardware/TEG.kicad_pcb)
#     OUTDIR   output directory (default: build/fab)
#     --tht    include through-hole parts in the BOM+CPL. Default is SMT-only
#              assembly: THT parts are dropped from BOTH files so they agree
#              (JLCPCB rejects a BOM listing a part that is not in the CPL).
#
# Env:
#   KICAD_CLI   path to kicad-cli (default: found on PATH, else the macOS app bundle)
set -euo pipefail
cd "$(dirname "$0")/.."

THT=0
POS=()
for a in "$@"; do
  case "$a" in
    --tht) THT=1 ;;
    -h|--help)
      cat <<'EOF'
Produce a review-ready JLCPCB fabrication + assembly package for a KiCad board.

Usage: scripts/fab_export.sh [BOARD] [OUTDIR] [--tht]
  BOARD    KiCad .kicad_pcb (default: hardware/TEG.kicad_pcb)
  OUTDIR   output directory (default: build/fab)
  --tht    include through-hole parts in the BOM+CPL. Default is SMT-only
           assembly: THT parts are dropped from BOTH files so they agree
           (JLCPCB rejects a BOM listing a part that is not in the CPL).

Outputs (in OUTDIR): <BASE>-gerbers.zip, <BASE>-BOM-jlcpcb.csv,
<BASE>-CPL-jlcpcb.csv. It never uploads or orders -- see
docs/jlcpcb-fabrication.md.

Env: KICAD_CLI  path to kicad-cli (default: PATH, else the macOS app bundle).
EOF
      exit 0 ;;
    *) POS+=("$a") ;;
  esac
done
BOARD="${POS[0]:-hardware/TEG.kicad_pcb}"
OUTDIR="${POS[1]:-build/fab}"

KICAD_CLI="${KICAD_CLI:-$(command -v kicad-cli || true)}"
if [ -z "${KICAD_CLI}" ] && [ -x "$HOME/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli" ]; then
  KICAD_CLI="$HOME/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli"
fi
if [ -z "${KICAD_CLI}" ] || [ ! -x "${KICAD_CLI}" ]; then
  echo "error: kicad-cli not found. Install KiCad or set KICAD_CLI=/path/to/kicad-cli" >&2
  exit 1
fi
[ -f "$BOARD" ] || { echo "error: board not found: $BOARD" >&2; exit 1; }
SCH="${BOARD%.kicad_pcb}.kicad_sch"
[ -f "$SCH" ] || { echo "error: schematic not found: $SCH" >&2; exit 1; }
BASE="$(basename "$BOARD" .kicad_pcb)"

mkdir -p "$OUTDIR"
echo "== JLCPCB fab export =="
echo "board : $BOARD"
echo "out   : $OUTDIR"
echo "using : $KICAD_CLI"
"$KICAD_CLI" version
echo

# 1. Gerbers. Protel filename extensions (the default) are what JLCPCB expects.
echo "-- gerbers"
"$KICAD_CLI" pcb export gerbers -o "$OUTDIR/" "$BOARD"

# 2. Excellon drill, millimetres.
echo "-- drill"
"$KICAD_CLI" pcb export drill --format excellon --excellon-units mm -o "$OUTDIR/" "$BOARD"

# 3. Pick & place. SMT-only by default (drops through-hole parts like connectors).
echo "-- pick & place"
if [ "$THT" -eq 1 ]; then
  "$KICAD_CLI" pcb export pos --format csv --units mm -o "$OUTDIR/$BASE-pos.csv" "$BOARD"
else
  "$KICAD_CLI" pcb export pos --format csv --units mm --smd-only -o "$OUTDIR/$BASE-pos.csv" "$BOARD"
fi

# 4. Convert the KiCad position file to JLCPCB's CPL format.
echo "-- CPL (JLCPCB)"
CPL="$OUTDIR/$BASE-CPL-jlcpcb.csv"
python3 scripts/jlc_cpl.py "$OUTDIR/$BASE-pos.csv" -o "$CPL"

# 5. JLCPCB BOM from the schematic, restricted to the CPL designators so the two
#    assembly files always agree.
echo "-- BOM (JLCPCB)"
BOM="$OUTDIR/$BASE-BOM-jlcpcb.csv"
python3 scripts/jlc_bom.py "$SCH" -o "$BOM" --designators-from "$CPL"

# 6. Zip the PCB manufacturing files for the JLCPCB "add gerber" upload.
echo "-- package"
ZIP="$OUTDIR/$BASE-gerbers.zip"
rm -f "$ZIP"
python3 - "$ZIP" "$OUTDIR" "$BASE" <<'PY'
import glob, os, sys, zipfile
zip_path, outdir, base = sys.argv[1], sys.argv[2], sys.argv[3]
names = sorted(
    glob.glob(os.path.join(outdir, base + ".g*"))
    + glob.glob(os.path.join(outdir, base + "*.drl"))
    + glob.glob(os.path.join(outdir, base + "*.gbrjob"))
)
if not any(n.endswith((".gbl", ".gtl", ".gbr")) for n in names):
    sys.exit("error: no gerber files were produced")
with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
    for n in names:
        z.write(n, os.path.basename(n))
print(f"zipped {len(names)} files -> {zip_path}")
PY

echo
echo "== done =="
echo "PCB fab package : $ZIP"
echo "assembly BOM    : $BOM"
echo "assembly CPL    : $CPL"
echo
echo "Next: review the package, then order manually from JLCPCB (see"
echo "docs/jlcpcb-fabrication.md). Never place an order without approval."
