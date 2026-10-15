#!/usr/bin/env python3
"""Build a JLCPCB assembly BOM CSV from a KiCad schematic.

Reads each symbol instance's Reference, Value, Footprint and ``LCSC Part``
property, groups identical parts, and emits JLCPCB's required columns:

    Comment,Designator,Footprint,LCSC Part #

The ``LCSC Part`` property is written for every part by scripts/gen_schematic.py
(see the part/net table there). Symbols marked ``(in_bom no)`` (PWR_FLAGs) and
symbols without an LCSC id are skipped.

``--designators-from CPL.csv`` restricts the output to the designators present in
a CPL, so a package's BOM and CPL always agree -- JLCPCB rejects a BOM that lists a
part missing from the CPL (e.g. through-hole connectors on an SMT-only build).

Usage:
    python3 scripts/jlc_bom.py hardware/TEG.kicad_sch -o build/fab/TEG-BOM-jlcpcb.csv
    python3 scripts/jlc_bom.py SCH -o OUT --designators-from build/fab/TEG-CPL-jlcpcb.csv
"""
import argparse
import csv
import re
import sys
from collections import OrderedDict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from gen_schematic import parse_sexpr, unq  # noqa: E402  (shared s-expr helpers)


def instance_symbols(root):
    """Top-level symbol instances (not the copies under ``lib_symbols``)."""
    doc = next((n for n in root if isinstance(n, list) and n and n[0] == "kicad_sch"), None)
    if doc is None:
        return
    for node in doc[1:]:
        if isinstance(node, list) and node and node[0] == "symbol":
            yield node


def child(node, key):
    for c in node:
        if isinstance(c, list) and c and c[0] == key:
            return c
    return None


def props_of(node):
    out = {}
    for c in node:
        if isinstance(c, list) and c and c[0] == "property":
            out[unq(c[1])] = unq(c[2])
    return out


def natural_key(ref):
    return [int(t) if t.isdigit() else t for t in re.split(r"(\d+)", ref)]


def collect(sch_path):
    root, _ = parse_sexpr(Path(sch_path).read_text())
    # Key on the LCSC id (what JLCPCB actually sources) + footprint, so parts that
    # share a part number collapse into one BOM line, even if their Value labels
    # differ (e.g. the two KF128 connectors J1/J3).
    rows = OrderedDict()  # (lcsc, footprint) -> {"refs": [], "comments": []}
    for sym in instance_symbols(root):
        b = child(sym, "in_bom")
        if b is not None and unq(b[1]).lower() == "no":
            continue
        p = props_of(sym)
        ref = p.get("Reference", "")
        if not ref or ref.startswith("#"):
            continue
        lcsc = (p.get("LCSC Part") or p.get("LCSC") or "").strip()
        if not lcsc:
            continue
        footprint = p.get("Footprint", "").split(":", 1)[-1]  # drop library nickname
        entry = rows.setdefault((lcsc, footprint), {"refs": [], "comments": []})
        entry["refs"].append(ref)
        comment = p.get("Value", "")
        if comment and comment not in entry["comments"]:
            entry["comments"].append(comment)
    return rows


def write_csv(rows, out_path, designators_from=None):
    keep = None
    if designators_from:
        keep = set()
        with open(designators_from, newline="") as fh:
            for row in csv.DictReader(fh):
                d = (row.get("Designator") or row.get("Ref") or "").strip()
                if d:
                    keep.add(d)
    out = []
    for (lcsc, footprint), entry in rows.items():
        refs = [r for r in entry["refs"] if keep is None or r in keep]
        if not refs:
            continue
        refs.sort(key=natural_key)
        comment = " / ".join(entry["comments"])
        out.append([comment, ",".join(refs), footprint, lcsc])
    out.sort(key=lambda r: natural_key(r[1].split(",")[0]))

    lines = ["Comment,Designator,Footprint,LCSC Part #"]
    for comment, desig, footprint, lcsc in out:
        cells = [comment, desig, footprint, lcsc]
        if any(("," in c or '"' in c) for c in cells):
            cells = ['"' + c.replace('"', '""') + '"' for c in cells]
        lines.append(",".join(cells))
    text = "\n".join(lines) + "\n"
    if out_path and out_path != "-":
        Path(out_path).parent.mkdir(parents=True, exist_ok=True)
        Path(out_path).write_text(text)
        total = sum(len(r[1].split(",")) for r in out)
        print(f"wrote {out_path}  lines={len(out)} designators={total}"
              + (f" (restricted to {designators_from})" if keep is not None else ""))
    else:
        sys.stdout.write(text)


def main():
    ap = argparse.ArgumentParser(description="KiCad schematic -> JLCPCB BOM CSV")
    ap.add_argument("schematic", help="path to .kicad_sch")
    ap.add_argument("-o", "--output", default="-", help="output CSV ('-' = stdout)")
    ap.add_argument("--designators-from", default=None,
                    help="restrict to designators listed in this CPL/BOM CSV")
    args = ap.parse_args()
    write_csv(collect(args.schematic), args.output, args.designators_from)


if __name__ == "__main__":
    main()
