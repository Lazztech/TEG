#!/usr/bin/env bash
# Route the board with FreeRouting (autorouter), then verify with kicad-cli DRC.
#
# KiCad has no autorouter, so this is the standard SPECCTRA round-trip:
#   board -> .dsn (KiCad python) -> .ses (FreeRouting) -> board -> DRC
# Requires: KiCad's bundled python (pcbnew), a JDK 25 (for the jar) and build/freerouting.jar.
set -uo pipefail
cd "$(dirname "$0")/.."

PY="${KICAD_PY:-$HOME/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/3.9/bin/python3.9}"
JAVA="${JAVA25:-$(brew --prefix 2>/dev/null)/opt/openjdk@25/bin/java}"
JAR="${FREEROUTING_JAR:-build/freerouting.jar}"
DSN="build/TEG.dsn"; SES="build/TEG.ses"

for f in "$PY" "$JAVA" "$JAR"; do
  [ -e "$f" ] || { echo "missing: $f (set KICAD_PY / JAVA25 / FREEROUTING_JAR)" >&2; exit 1; }
done

echo "== export DSN =="
"$PY" -c "import pcbnew; b=pcbnew.LoadBoard('hardware/TEG.kicad_pcb'); print('  nets', b.GetNetCount(), '->', pcbnew.ExportSpecctraDSN(b, '$DSN'))" 2>/dev/null

echo "== autoroute =="
"$JAVA" -jar "$JAR" -de "$DSN" -do "$SES" 2>&1 | grep -E "Auto-routing stage completed|Optimization was completed|Saved" || true

echo "== import session =="
"$PY" -c "import pcbnew; b=pcbnew.LoadBoard('hardware/TEG.kicad_pcb'); print('  import ->', pcbnew.ImportSpecctraSES(b, '$SES')); pcbnew.SaveBoard('hardware/TEG.kicad_pcb', b); print('  tracks now', len(b.GetTracks()))" 2>/dev/null

echo "== DRC =="
./scripts/validate.sh 2>&1 | grep -E "^==|Found [0-9]+ viol"
