#!/usr/bin/env bash
# Validate the engineering artifacts in this repo.
#
#   scripts/validate.sh                 # CAD artifacts + KiCad ERC/DRC (needs both toolchains)
#   scripts/validate.sh --cad           # code-CAD artifacts only
#   scripts/validate.sh --hardware      # KiCad ERC + DRC only
#   scripts/validate.sh --cad --no-rebuild   # artifact checks, skip the rebuild comparison
#
# The CAD half runs scripts/validate_cad.py with the repo-local .venv (create it
# with scripts/cad-setup.sh). The hardware half needs kicad-cli on PATH (or
# KICAD_CLI set); CI installs KiCad 10 from the official PPA.
#
# Exit: 0 pass, 1 validation failure, 2 missing toolchain.
set -uo pipefail
cd "$(dirname "$0")/.."
REPO="$PWD"

MODE=all
REBUILD=1
for arg in "$@"; do
    case "$arg" in
        --all) MODE=all ;;
        --cad) MODE=cad ;;
        --hardware) MODE=hardware ;;
        --no-rebuild) REBUILD=0 ;;
        -h|--help)
            sed -n '2,13p' "$0" | sed 's/^# \{0,1\}//'
            exit 0 ;;
        *)
            echo "validate: unknown argument: $arg" >&2
            exit 2 ;;
    esac
done

STATUS=0
mark_status() {
    if [ "$1" -eq 2 ]; then
        STATUS=2
    elif [ "$1" -ne 0 ] && [ "$STATUS" -ne 2 ]; then
        STATUS=1
    fi
}

run_cad() {
    local py="$REPO/.venv/bin/python"
    if [ ! -x "$py" ]; then
        echo "validate: no .venv - run scripts/cad-setup.sh first" >&2
        return 2
    fi

    local -a args=(--require-brep --json build/cad-validation.json)
    [ "$REBUILD" -eq 1 ] && args+=(--rebuild)

    mkdir -p build
    export LD_LIBRARY_PATH="$REPO/.venv/gl-libs/usr/lib/x86_64-linux-gnu${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
    echo "== CAD artifacts =="
    "$py" "$REPO/scripts/validate_cad.py" "${args[@]}"
}

run_hardware() {
    local kicad="${KICAD_CLI:-$(command -v kicad-cli || true)}"
    if [ -z "$kicad" ] && [ -x "$HOME/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli" ]; then
        kicad="$HOME/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli"
    fi
    if [ -z "$kicad" ] || [ ! -x "$kicad" ]; then
        echo "validate: kicad-cli not found (install KiCad or set KICAD_CLI)" >&2
        return 2
    fi

    mkdir -p build
    echo "== KiCad $("$kicad" version) =="

    check() {  # check <sch|pcb> <input> <name>
        local kind=$1 input=$2 name=$3
        local -a cmd=("$kicad" "$kind")
        if [ "$kind" = sch ]; then cmd+=(erc); else cmd+=(drc); fi

        # Full report for the reviewer: warns about known cosmetic issues.
        "${cmd[@]}" --severity-all -o "build/${name}-all.rpt" "$input" >/dev/null 2>&1 || true
        cat "build/${name}-all.rpt"

        # Gate on error-level violations only; warnings are documented in README.
        local rc=0
        "${cmd[@]}" --severity-error --exit-code-violations \
            -o "build/${name}.rpt" "$input" >/dev/null 2>&1 || rc=$?
        case "$rc" in
            0) ;;
            5) echo "validate: ${name} has error-level violations" >&2
               cat "build/${name}.rpt"
               STATUS=1 ;;
            *) echo "validate: kicad-cli ${name} failed (exit $rc)" >&2
               STATUS=1 ;;
        esac
    }

    check sch "$REPO/hardware/TEG.kicad_sch" erc
    check pcb "$REPO/hardware/TEG.kicad_pcb" drc
}

if [ "$MODE" = all ] || [ "$MODE" = cad ]; then
    run_cad
    mark_status $?
fi
if [ "$MODE" = all ] || [ "$MODE" = hardware ]; then
    run_hardware
    mark_status $?
fi

if [ "$STATUS" -eq 0 ]; then
    echo "validate: all checks passed"
elif [ "$STATUS" -eq 2 ]; then
    echo "validate: a required toolchain is missing" >&2
else
    echo "validate: checks failed" >&2
fi
exit "$STATUS"
