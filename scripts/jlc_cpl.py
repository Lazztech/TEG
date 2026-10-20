#!/usr/bin/env python3
"""Convert a KiCad ``kicad-cli pcb export pos`` CSV into JLCPCB's CPL format.

JLCPCB's assembly uploader wants a placement file with these exact columns:

    Designator,Val,Package,Mid X,Mid Y,Rotation,Layer

KiCad's position export writes:

    Ref,Val,Package,PosX,PosY,Rot,Side

so this only renames columns and normalises the side (top/bottom -> Top/Bottom)
and rotation. Coordinates are passed through unchanged, so the Gerbers and the
CPL must be exported with the same origin (see docs/jlcpcb-fabrication.md).

This does NOT correct part rotations. JLCPCB's rotation convention differs from
KiCad's for some packages; always eyeball the assembly preview before paying.

Usage:
    python3 scripts/jlc_cpl.py build/fab/TEG-pos.csv -o build/fab/TEG-CPL-jlcpcb.csv
"""
import argparse
import csv
import re
import sys
from pathlib import Path

# KiCad header -> JLCPCB header
HEADER = {
    "Ref": "Designator",
    "Designator": "Designator",
    "Val": "Val",
    "Package": "Package",
    "PosX": "Mid X",
    "PosY": "Mid Y",
    "Rot": "Rotation",
    "Rotation": "Rotation",
    "Side": "Layer",
    "Layer": "Layer",
}
OUT_COLS = ["Designator", "Val", "Package", "Mid X", "Mid Y", "Rotation", "Layer"]


def natural_key(ref):
    return [int(t) if t.isdigit() else t for t in re.split(r"(\d+)", ref)]


def num(x):
    try:
        f = float(x)
    except (TypeError, ValueError):
        return x
    s = f"{f:.6f}".rstrip("0").rstrip(".")
    return s if s not in ("", "-0") else "0"


def convert(rows):
    out = []
    for row in rows:
        rec = {}
        for k, v in row.items():
            k = (k or "").strip()
            if k in HEADER:
                rec[HEADER[k]] = (v or "").strip()
        if not rec.get("Designator"):
            continue
        layer = rec.get("Layer", "").strip().lower()
        rec["Layer"] = {"top": "Top", "bottom": "Bottom", "t": "Top", "b": "Bottom"}.get(layer, rec.get("Layer", ""))
        rec["Mid X"] = num(rec.get("Mid X", ""))
        rec["Mid Y"] = num(rec.get("Mid Y", ""))
        rec["Rotation"] = num(rec.get("Rotation", ""))
        out.append(rec)
    out.sort(key=lambda r: natural_key(r["Designator"]))
    return out


def main():
    ap = argparse.ArgumentParser(description="KiCad pos CSV -> JLCPCB CPL CSV")
    ap.add_argument("pos_csv", help="KiCad position CSV (from 'pcb export pos')")
    ap.add_argument("-o", "--output", default="-", help="output CSV ('-' = stdout)")
    args = ap.parse_args()

    with open(args.pos_csv, newline="") as fh:
        rows = list(csv.DictReader(fh))
    out = convert(rows)

    import io
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=OUT_COLS, lineterminator="\n")
    w.writeheader()
    w.writerows(out)
    text = buf.getvalue()

    if args.output and args.output != "-":
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(text)
        print(f"wrote {args.output}  components={len(out)}")
    else:
        sys.stdout.write(text)


if __name__ == "__main__":
    main()
