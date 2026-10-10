#!/usr/bin/env python3
"""Generate hardware/TEG.kicad_pcb: place every BOM footprint on a board outline and
assign nets to pads from the same table gen_schematic.py uses (label-per-pin draft
there -> ratsnest-only board here; no copper routed yet).

Placement map below is manual (block layout). Edit positions / rerun to update.
Board file uses the legacy KiCad-5 board format (version 20171130) because the fetched
footprints are legacy (module ...)-style files; modern KiCad opens and migrates it.
"""
import sys
import uuid as uuidlib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from gen_schematic import PARTS, ROOT, parse_sexpr, unq, walk  # noqa: E402

FP_DIR = ROOT / "hardware" / "footprints" / "TEG.pretty"
OUT = ROOT / "hardware" / "TEG.kicad_pcb"

# ref -> (x, y) manual block placement, mm, KiCad board coords (y grows down)
PLACEMENT = {
    "J1": (14, 12), "D1": (14, 24), "C1": (14, 30),
    "U1": (30, 22),
    "L1": (30, 34), "C2": (38, 34), "C3": (42, 34),
    "C4": (38, 26), "C5": (38, 20),
    "U2": (56, 20), "C8": (63, 20), "L2": (56, 28), "D2": (63, 28),
    "C6": (70, 20), "C7": (70, 28), "R8": (70, 34), "R9": (70, 40),
    "R1": (14, 40), "R2": (14, 46), "R3": (14, 52), "R4": (14, 58),
    "R5": (14, 64), "R6": (14, 70), "R7": (14, 76), "R15": (22, 76),
    "R13": (46, 44), "R14": (46, 50),
    "Q1": (84, 40), "R10": (84, 50), "R12": (84, 56),
    "J3": (95, 48),
    "J2": (95, 14), "R11": (95, 24),
}
BOARD_MARGIN = 4.0

def load_footprint(name):
    """Parse TEG.pretty/<name>.kicad_mod into an s-expr tree."""
    path = FP_DIR / f"{name}.kicad_mod"
    root, _ = parse_sexpr(path.read_text())
    node = next(it for it in root if isinstance(it, list) and it[0] == "module")
    return node

def build_net_table():
    """Deterministic net list: GND first, then the rest alphabetically."""
    nets = set()
    for part in PARTS:
        for net in part["nets"].values():
            if net:
                nets.add(net)
    ordered = ["GND"] + sorted(n for n in nets if n != "GND")
    return {name: i for i, name in enumerate(ordered, start=1)}, ordered

def footprint_extent(fp_node):
    """Half-extents (w, h) of all pads, for outline sizing."""
    xs, ys = [], []
    for pad in walk(fp_node, "pad"):
        at = next(c for c in pad if isinstance(c, list) and c[0] == "at")
        size = next(c for c in pad if isinstance(c, list) and c[0] == "size")
        xs.append(abs(float(at[1])) + float(size[1]) / 2)
        ys.append(abs(float(at[2])) + float(size[2]) / 2)
    return (max(xs) if xs else 2, max(ys) if ys else 2)

def emit_footprint(part, net_ids):
    fp = part["fp"]
    fp_name = next(n for n in FP_DIR.glob("*.kicad_mod") if n.stem == fp).stem
    node = load_footprint(fp_name)

    # rename library prefix easyeda2kicad:<name> -> TEG:<name>
    node[1] = f"TEG:{fp_name}"
    # instance position is inserted by dump_with_at(); nothing else to move here

    # rewrite reference/value text placeholders
    for t in walk(node, "fp_text"):
        kind = t[1]
        if kind == "reference":
            t[2] = f'"{part["ref"]}"'
        elif kind == "value":
            t[2] = f'"{part["value"]}"'

    # assign nets to pads
    for pad in walk(node, "pad"):
        padnum = unq(pad[1])
        net = part["nets"].get(padnum)
        if not net:
            continue
        pad.append(f'(net {net_ids[net]} "{net}")')

    x, y = PLACEMENT[part["ref"]]
    return dump_with_at(node, x, y)

def dump_with_at(node, x, y):
    """Serialize, inserting the instance (at) right after the (layer F.Cu) token."""
    text = dump(node)
    # module's own (at ...) instance location: insert after first 'layer' token
    return text.replace("(layer F.Cu)", f"(layer F.Cu) (at {x} {y} 0)", 1)

def dump(node):
    if isinstance(node, str):
        return node
    return "(" + " ".join(dump(c) if isinstance(c, list) else c for c in node) + ")"

def main():
    net_ids, net_names = build_net_table()

    fp_blocks = []
    xs, ys = [], []
    for part in PARTS:
        if part["ref"] not in PLACEMENT:
            raise SystemExit(f"no placement for {part['ref']}")
        fp_blocks.append(emit_footprint(part, net_ids))
        half = footprint_extent(load_footprint(next(
            n.stem for n in FP_DIR.glob("*.kicad_mod") if n.stem == part["fp"])))
        x, y = PLACEMENT[part["ref"]]
        xs += [x - half[0], x + half[0]]
        ys += [y - half[1], y + half[1]]

    m = BOARD_MARGIN
    x0, y0 = min(0, min(xs)) - m, min(0, min(ys)) - m
    x1, y1 = max(xs) + m, max(ys) + m
    edge = [f'(gr_line (start {x0} {y0}) (end {x1} {y0}) (layer Edge.Cuts) (width 0.1))',
            f'(gr_line (start {x1} {y0}) (end {x1} {y1}) (layer Edge.Cuts) (width 0.1))',
            f'(gr_line (start {x1} {y1}) (end {x0} {y1}) (layer Edge.Cuts) (width 0.1))',
            f'(gr_line (start {x0} {y1}) (end {x0} {y0}) (layer Edge.Cuts) (width 0.1))']

    nets = "\n".join(f'  (net {i} "{n}")' for n, i in [(n, net_ids[n]) for n in net_names])
    net0 = '  (net 0 "")'
    setup = (
        "  (setup\n"
        "    (last_trace_width 0.25)\n"
        "    (trace_clearance 0.2)\n"
        "    (zone_clearance 0.3)\n"
        "    (trace_min 0.2)\n"
        "    (via_size 0.6)\n"
        "    (via_drill 0.3)\n"
        "    (aux_axis_origin 0 0)\n"
        "    (grid_origin 0 0)\n"
        "  )"
    )
    layers = (
        "  (layers\n"
        "    (0 F.Cu signal)\n"
        "    (31 B.Cu signal)\n"
        "    (36 B.SilkS user)\n"
        "    (37 F.SilkS user)\n"
        "    (38 B.Mask user)\n"
        "    (39 F.Mask user)\n"
        "    (44 Edge.Cuts user)\n"
        "  )"
    )
    general = (
        "  (general\n"
        f"    (links 0)\n"
        f"    (no_connects 0)\n"
        f"    (area {x0} {y0} {x1} {y1})\n"
        f"    (thickness 1.6)\n"
        f"    (drawings 4)\n"
        f"    (tracks 0)\n"
        f"    (zones 0)\n"
        f"    (modules {len(PARTS)})\n"
        f"    (nets {len(net_names) + 1})\n"
        "  )"
    )

    text = "\n".join([
        f"(kicad_pcb (version 20171130) (generator gen_board.py)",
        "",
        general,
        '  (paper "A4")',
        layers,
        setup,
        "",
        net0,
        nets,
        "",
        *fp_blocks,
        "",
        *edge,
        ")",
        ""])
    OUT.write_text(text)
    print(f"wrote {OUT.relative_to(ROOT)}  footprints={len(fp_blocks)} nets={len(net_names) + 1} "
          f"outline=({x0:.1f},{y0:.1f})-({x1:.1f},{y1:.1f})")

if __name__ == "__main__":
    main()
