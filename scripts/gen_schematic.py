#!/usr/bin/env python3
"""Generate hardware/TEG.kicad_sch: place every BOM part and define each net with a
label at the pin tip (label-per-pin draft; no routed wires yet).

The part/net table below IS the draft netlist — edit it and re-run to update the sheet.
Requires the symbols fetched into hardware/libs/TEG.kicad_sym (see README).
"""
import os
import uuid as uuidlib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LIB = ROOT / "hardware" / "libs" / "TEG.kicad_sym"
OUT = ROOT / "hardware" / "TEG.kicad_sch"
ROOT_UUID = "dadd86a9-5a8e-438a-b7fc-4a009aac7ff2"
PROJECT = "TEG"

# ---------------------------------------------------------------- part/net table
# sym = lib symbol name in libs/TEG.kicad_sym, fp = footprint in TEG.pretty (no ext),
# nets maps pin NUMBER -> net (None = leave unconnected).
TBD = "TBD"
PARTS = [
    dict(ref="J1", sym="KF128-5.08-2P", fp="CONN-TH_P5.08_KF128-5.08-2P", value="TEG_IN", lcsc="C474952",
         nets={"1": "TEG+", "2": "TEG-"}),
    dict(ref="D1", sym="1N5819WS", fp="SOD-323_L1.8-W1.3-LS2.5-RD", value="1N5819WS", lcsc="C191023",
         nets={"1": "TEG+", "2": "TEG-"}),  # reverse-polarity clamp across the input
    dict(ref="C1", sym="CL21A106KAYNNNE", fp="C0805", value="10uF", lcsc="C15850",
         nets={"1": "TEG+", "2": "GND"}),
    dict(ref="U1", sym="BQ25504RGTT", fp="VQFN-16_L3.0-W3.0-P0.50-TL-EP", value="BQ25504RGTT", lcsc="C157471",
         nets={"1": "GND", "2": "TEG+", "3": "VOC_SAMP", "4": "VREF_SAMP", "5": "OT_PROG",
               "6": "VBAT_OV", "7": "VRDIV", "8": "VBAT_UV", "9": "OK_HYST", "10": "OK_PROG",
               "11": None, "12": "GND", "13": "GND", "14": "VBAT", "15": "VSTOR",
               "16": "SW_HV", "17": "GND"}),
    dict(ref="L1", sym="SWPA4020S220MT", fp="IND-SMD_L4.0-W4.0", value="22uH", lcsc="C82401",
         nets={"1": "SW_HV", "2": "TEG+"}),  # datasheet recommends 22 uH; part TBD, verify it fits the 1008 land
    # MPPT sample-and-hold network: ROC1/ROC2 set the harvesting voltage to a fraction of Voc.
    # ratio = ROC1/(ROC1+ROC2) -> 10M/10M = ~50% of Voc, matched-load MPP for a TEG (solar uses 78%).
    dict(ref="R13", sym="0603WAF1002T5E", fp="R0603", value="10M", lcsc="C114606", nets={"1": "TEG+", "2": "VOC_SAMP"}),
    dict(ref="R14", sym="0603WAF1002T5E", fp="R0603", value="10M", lcsc="C114606", nets={"1": "VOC_SAMP", "2": "GND"}),
    dict(ref="C3", sym="CL10B103KB8NNNC", fp="C0603", value="10nF", lcsc="C1589",
         nets={"1": "VREF_SAMP", "2": "GND"}),  # CREF, low-leakage per datasheet
    # Option D storage: electrolytic buffer on VBAT (JLCPCB-assembled). Polarity matters:
    # pin 1 = +. Verify against the footprint silkscreen before assembly.
    dict(ref="C2", sym="RVT0J102M08101000UF6.3V", fp="CAP-SMD_BD8.0-L8.3-W8.3-LS9.3-FD-1",
         value="1000uF", lcsc="C970711", nets={"1": "VBAT", "2": "GND"}),
    dict(ref="C4", sym="CL21A106KAYNNNE", fp="C0805", value="10uF", lcsc="C15850",
         nets={"1": "VSTOR", "2": "GND"}),
    dict(ref="C5", sym="CL21A106KAYNNNE", fp="C0805", value="10uF", lcsc="C15850",
         nets={"1": "VBAT", "2": "GND"}),
    dict(ref="U2", sym="MT3608", fp="SOT-23-6_L2.9-W1.6-P0.95-LS2.8-BL", value="MT3608", lcsc="C84817",
         nets={"1": "SW_5V", "2": "GND", "3": "FB_5V", "4": "VSTOR", "5": "VSTOR", "6": None}),
    dict(ref="C8", sym="CL10B103KB8NNNC", fp="C0603", value="10nF", lcsc="C1589",
         nets={"1": "VSTOR", "2": "GND"}),  # CBYP, near VSTOR/VSS per datasheet
    dict(ref="L2", sym="SWPA4020S220MT", fp="IND-SMD_L4.0-W4.0", value="22uH", lcsc="C82401",
         nets={"1": "VSTOR", "2": "SW_5V"}),
    dict(ref="D2", sym="1N5819WS", fp="SOD-323_L1.8-W1.3-LS2.5-RD", value="1N5819WS", lcsc="C191023",
         nets={"1": "+5V", "2": "SW_5V"}),  # MT3608 catch diode (asynchronous boost)
    dict(ref="C6", sym="CL21A106KAYNNNE", fp="C0805", value="10uF", lcsc="C15850",
         nets={"1": "+5V", "2": "GND"}),
    dict(ref="C7", sym="CL10A105KB8NNNC", fp="C0603", value="1uF", lcsc="C15849",
         nets={"1": "+5V", "2": "GND"}),
    dict(ref="R8", sym="0603WAF1002T5E", fp="R0603", value="73.2k", lcsc="C2933257", nets={"1": "+5V", "2": "FB_5V"}),
    dict(ref="R9", sym="0603WAF1002T5E", fp="R0603", value="10k", lcsc="C25804", nets={"1": "FB_5V", "2": "GND"}),
    # BQ25504 threshold network, datasheet worked example (SLUSAH0G s9.2.1):
    # VBAT_OV 3.15 V, VBAT_UV 2.20 V, VBAT_OK 2.44 V, VBAT_OK_HYST 2.80 V.
    # Chain: VBAT -ROV1- VBAT_OV -ROV2- VRDIV -RUV1- VBAT_UV -RUV2- GND
    dict(ref="R1", sym="0603WAF1003T5E", fp="R0603", value="5.90M", lcsc="C2076902", nets={"1": "VBAT", "2": "VBAT_OV"}),
    dict(ref="R2", sym="0603WAF1003T5E", fp="R0603", value="4.02M", lcsc="C137708", nets={"1": "VBAT_OV", "2": "VRDIV"}),
    dict(ref="R3", sym="0603WAF1003T5E", fp="R0603", value="5.60M", lcsc="C23190", nets={"1": "VRDIV", "2": "VBAT_UV"}),
    dict(ref="R4", sym="0603WAF1003T5E", fp="R0603", value="4.42M", lcsc="C166806", nets={"1": "VBAT_UV", "2": "GND"}),
    dict(ref="R5", sym="0603WAF1002T5E", fp="R0603", value="0R", lcsc="C21189", nets={"1": "OT_PROG", "2": "GND"}),
    # OK chain: VBAT -ROK1- OK_HYST -ROK2- OK_PROG -ROK3- GND
    dict(ref="R15", sym="0603WAF1003T5E", fp="R0603", value="4.42M", lcsc="C166806", nets={"1": "VBAT", "2": "OK_HYST"}),
    dict(ref="R7", sym="0603WAF1003T5E", fp="R0603", value="4.22M", lcsc="C166807", nets={"1": "OK_HYST", "2": "OK_PROG"}),
    dict(ref="R6", sym="0603WAF1003T5E", fp="R0603", value="1.43M", lcsc="C166898", nets={"1": "OK_PROG", "2": "GND"}),
    dict(ref="Q1", sym="AO3400A", fp="SOT-23-3_L2.9-W1.3-P1.90-LS2.4-BR", value="AO3400A", lcsc="C20917",
         nets={"1": "PWM_LOAD", "2": "GND", "3": "LOAD_SW"}),
    dict(ref="R10", sym="0603WAF1002T5E", fp="R0603", value="1k", lcsc="C21190", nets={"1": "FAN_PWM", "2": "PWM_LOAD"}),
    dict(ref="R12", sym="0603WAF1003T5E", fp="R0603", value="100k", lcsc="C25803", nets={"1": "PWM_LOAD", "2": "GND"}),
    dict(ref="J2", sym="PZ254V-11-04P_C2691448", fp="HDR-TH_4P-P2.54-V-M", value="FAN_4PIN", lcsc="C2691448",
         nets={"1": "GND", "2": "+5V", "3": "FAN_TACH", "4": "FAN_PWM"}),
    dict(ref="R11", sym="0603WAF1002T5E", fp="R0603", value="10k", lcsc="C25804", nets={"1": "FAN_TACH", "2": "+5V"}),
    dict(ref="J3", sym="KF128-5.08-2P", fp="CONN-TH_P5.08_KF128-5.08-2P", value="TEST_LOAD", lcsc="C474952",
         nets={"1": "LOAD_SW", "2": "+5V"}),
]

NOTES = (
    "DRAFT — nets defined by labels at each pin; no routed wires yet.\\n"
    "Storage: 1000uF electrolytic buffer on VBAT (JLCPCB-assembled, polarised - check pin 1).\\n"
    "There is no energy store beyond this buffer, so the fan runs only while the TEGs\\n"
    "supply power; VBAT_OK is left unconnected (available later for load gating)."
)

# ---------------------------------------------------------------- s-expr helpers
def parse_sexpr(s, i=0):
    items, buf = [], ""
    while i < len(s):
        c = s[i]
        if c == "(":
            if buf.strip():
                items.append(buf.strip()); buf = ""
            sub, i = parse_sexpr(s, i + 1); items.append(sub)
        elif c == ")":
            if buf.strip():
                items.append(buf.strip())
            return items, i + 1
        elif c == '"':
            j = i + 1; buf += c
            while s[j] != '"':
                buf += s[j]; j += 1
            buf += '"'; i = j + 1
        elif c.isspace():
            if buf.strip():
                items.append(buf.strip()); buf = ""
            i += 1
        else:
            buf += c; i += 1
    return items, i

def unq(x):
    return x[1:-1] if isinstance(x, str) and len(x) >= 2 and x[0] == '"' and x[-1] == '"' else x

def walk(node, key):
    if isinstance(node, list):
        if node and node[0] == key:
            yield node
        for c in node:
            if isinstance(c, list):
                yield from walk(c, key)

def new_uuid():
    return str(uuidlib.uuid4())

# ---------------------------------------------------------------- ERC support
# The fetched EasyEDA symbols declare every pin "unspecified", which trips ERC
# pin_to_pin / pin_not_driven. Map electrical types by pin name.
POWER_IN = {"vss", "gnd", "avss", "ep", "vbat", "vstor", "in", "vin-dc"}
OUTPUT = {"vbat-ok", "sw", "lbst"}

def patch_pin_types(sym_node):
    for p in walk(sym_node, "pin"):
        nm = None
        for sub in p[4:]:
            if isinstance(sub, list) and sub[0] == "name":
                nm = unq(sub[1])
        p[1] = pin_type_for(nm)
    return sym_node


def pin_type_for(name):
    key = (name or "").strip().lower()
    return ("power_in" if key in POWER_IN
            else "output" if key in OUTPUT
            else "passive")


def normalize_library_pin_types():
    """Rewrite pin electrical types in the project library in place.

    The easyeda2kicad exports mark every pin `unspecified`, which trips ERC and also
    makes the embedded schematic copy differ from the library (lib_symbol_mismatch).
    Normalising the library once keeps the two identical and makes the library
    electrically meaningful on its own.
    """
    import re
    text = LIB.read_text()
    pin_re = re.compile(r'\(pin\s+(\w+)\s+(\w+)\s+((?:[^()]|\([^()]*\))*?)\(name\s+"([^"]*)"',
                        re.S)

    def repl(m):
        current, style, mid, name = m.group(1), m.group(2), m.group(3), m.group(4)
        # never clobber a power type (e.g. PWR_FLAG's power_out drives nets);
        # everything else is normalised from the pin name
        if current in ("power_in", "power_out"):
            return m.group(0)
        want = pin_type_for(name)
        return f'(pin {want} {style} {mid}(name "{name}"'

    new, n = pin_re.subn(repl, text)
    if new != text:
        LIB.write_text(new)
        print(f"  normalized {n} pin types in {LIB.name}")

# Nets that source power; each gets a PWR_FLAG so power_in pins are "driven"
POWER_FLAGS = ["GND", "+5V", "VBAT", "VSTOR", "TEG+"]

# PWR_FLAG symbol definition. Prefer the real one from the installed KiCad power
# library (token syntax changes between KiCad versions); fall back to a minimal
# pin-only def that ERC accepts.
_PWR_FLAG_FALLBACK = (
    '(symbol "power:PWR_FLAG" (power) (pin_numbers hide) (exclude_from_sim no) '
    '(in_bom yes) (on_board yes) '
    '(property "Reference" "#FLG" (at 0 3.81 0) (effects (font (size 1.27 1.27)) hide)) '
    '(property "Value" "PWR_FLAG" (at 0 5.08 0) (effects (font (size 1.27 1.27)))) '
    '(symbol "PWR_FLAG_0_0" '
    '(pin power_out line (at 0 0 90) (length 0) '
    '(name "~" (effects (font (size 1.27 1.27)))) '
    '(number "1" (effects (font (size 1.27 1.27)))))))'
)

def _load_pwr_flag_def():
    import glob
    candidates = (
        glob.glob(os.path.expanduser("~/Applications/KiCad/KiCad.app/Contents/SharedSupport/symbols/power.kicad_sym"))
        + glob.glob("/usr/share/kicad/symbols/power.kicad_sym")
        + glob.glob("/Applications/KiCad/KiCad.app/Contents/SharedSupport/symbols/power.kicad_sym")
        + glob.glob("C:/Program Files/KiCad/*/share/kicad/symbols/power.kicad_sym")
    )
    for path in candidates:
        try:
            root, _ = parse_sexpr(Path(path).read_text())
            lib = root[0]
            flag = next(s for s in lib if isinstance(s, list) and s[0] == "symbol" and unq(s[1]) == "PWR_FLAG")
            return dump(flag)
        except Exception:
            continue
    return _PWR_FLAG_FALLBACK

PWR_FLAG_DEF = None  # resolved lazily in main() (dump() must exist first)

def emit_pwr_flag(net, x, y):
    return (
        f'\t(symbol\n\t\t(lib_id "TEG:PWR_FLAG")\n\t\t(at {fmt(x)} {fmt(y)} 0)\n\t\t(unit 1)\n'
        f'\t\t(exclude_from_sim no) (in_bom no) (on_board yes) (dnp no)\n'
        f'\t\t(uuid "{new_uuid()}")\n'
        f'\t\t(property "Reference" "#FLG{net}" (at {fmt(x)} {fmt(y + 3.81)} 0) '
        f'(effects (font (size 1.27 1.27)) hide))\n'
        f'\t\t(property "Value" "PWR_FLAG" (at {fmt(x)} {fmt(y + 5.08)} 0) '
        f'(effects (font (size 1.27 1.27))))\n'
        f'\t\t(pin "1" (uuid "{new_uuid()}"))\n'
        f'\t\t(instances\n\t\t\t(project "{PROJECT}"\n\t\t\t\t(path "/{ROOT_UUID}"'
        f'\n\t\t\t\t\t(reference "#FLG{net}")\n\t\t\t\t\t(unit 1)\n\t\t\t\t)\n\t\t\t)\n\t\t)\n\t)'
    )

# ---------------------------------------------------------------- geometry
def symbol_info(sym_node):
    pins = []
    for p in walk(sym_node, "pin"):
        at = next(c for c in p if isinstance(c, list) and c[0] == "at")
        nm = no = None
        for sub in p[4:]:
            if isinstance(sub, list) and sub[0] == "name":
                nm = unq(sub[1])
            elif isinstance(sub, list) and sub[0] == "number":
                no = unq(sub[1])
        pins.append(dict(num=no, name=nm, x=float(at[1]), y=float(at[2]), ang=float(at[3])))
    xs, ys = [], []
    for r in walk(sym_node, "rectangle"):
        st = next(c for c in r if isinstance(c, list) and c[0] == "start")
        en = next(c for c in r if isinstance(c, list) and c[0] == "end")
        xs += [float(st[1]), float(en[1])]; ys += [float(st[2]), float(en[2])]
    if not xs and pins:
        xs = [min(p["x"] for p in pins), max(p["x"] for p in pins)]
        ys = [min(p["y"] for p in pins), max(p["y"] for p in pins)]
    bbox = (min(xs), max(xs), min(ys), max(ys)) if xs else None
    return pins, bbox

def load_library():
    root, _ = parse_sexpr(LIB.read_text())
    lib = next(it for it in root if isinstance(it, list) and it[0] == "kicad_symbol_lib")
    return {unq(it[1]): it for it in lib if isinstance(it, list) and it[0] == "symbol"}

def raw_symbol_block(text, name):
    """Return the exact source text of a top-level symbol block (preserves formatting,
    so the copy embedded in the schematic matches the library byte-for-byte)."""
    i = text.index(f'(symbol "{name}"')
    depth = 0
    for j in range(i, len(text)):
        if text[j] == "(":
            depth += 1
        elif text[j] == ")":
            depth -= 1
            if depth == 0:
                return text[i:j + 1]
    raise ValueError(f"unbalanced symbol block for {name}")

def ensure_pwr_flag_in_lib():
    """Add PWR_FLAG to the project library so lib-linked lookups succeed."""
    syms = load_library()
    if any(unq(k).endswith("PWR_FLAG") for k in syms):
        return
    text = LIB.read_text().rstrip()
    assert text.endswith(")")
    LIB.write_text(text[:-1].rstrip() + "\n" + PWR_FLAG_DEF + "\n)\n")

# ---------------------------------------------------------------- emit
def fmt(x):
    return f"{x:.4f}".rstrip("0").rstrip(".")

def dump(node):
    if isinstance(node, str):
        return node
    return "(" + " ".join(dump(c) if isinstance(c, list) else c for c in node) + ")"

def emit_instance(part, pins, pos):
    x, y = pos
    bbox = part["_bbox"]
    body_h = (bbox[3] - bbox[2]) if bbox else 10
    out = [f'\t(symbol\n\t\t(lib_id "TEG:{part["sym"]}")\n\t\t(at {fmt(x)} {fmt(y)} 0)\n\t\t(unit 1)\n'
           f'\t\t(exclude_from_sim no) (in_bom yes) (on_board yes) (dnp no)\n'
           f'\t\t(uuid "{new_uuid()}")']
    out.append(f'\t\t(property "Reference" "{part["ref"]}" (at {fmt(x)} {fmt(y - body_h / 2 - 3)} 0) '
               f'(effects (font (size 1.27 1.27))))')
    out.append(f'\t\t(property "Value" "{part["value"]}" (at {fmt(x)} {fmt(y + body_h / 2 + 3)} 0) '
               f'(effects (font (size 1.27 1.27))))')
    out.append(f'\t\t(property "Footprint" "TEG:{part["fp"]}" (at 0 0 0) (effects (font (size 1.27 1.27)) hide))')
    out.append(f'\t\t(property "Datasheet" "~" (at 0 0 0) (effects (font (size 1.27 1.27)) hide))')
    out.append(f'\t\t(property "LCSC Part" "{part["lcsc"]}" (at 0 0 0) (effects (font (size 1.27 1.27)) hide))')
    for p in pins:
        out.append(f'\t\t(pin "{p["num"]}" (uuid "{new_uuid()}"))')
    out.append(f'\t\t(instances\n\t\t\t(project "{PROJECT}"\n\t\t\t\t(path "/{ROOT_UUID}"'
               f'\n\t\t\t\t\t(reference "{part["ref"]}")\n\t\t\t\t\t(unit 1)\n\t\t\t\t)\n\t\t\t)\n\t\t)')
    out.append("\t)")
    return "\n".join(out)

def emit_pin_net(pins, part, pos):
    """Stub wire from each mapped pin + label with the net name at the stub end."""
    x, y = pos
    cx, cy = part["_center"]
    out = []
    for p in pins:
        net = part["nets"].get(p["num"])
        if not net:
            continue
        ax, ay = x + p["x"], y - p["y"]          # symbol Y is inverted on placement
        ddx = ax - (x + cx)
        ddy = ay - (y - cy)
        # axis-aligned stub: use the dominant axis so wires stay orthogonal
        if abs(ddx) >= abs(ddy) and ddx != 0:
            dx, dy = (1 if ddx > 0 else -1), 0
        elif ddy != 0:
            dx, dy = 0, (1 if ddy > 0 else -1)
        else:
            dx, dy = 1, 0
        ex, ey = ax + dx * 2.54, ay + dy * 2.54
        just = "left" if dx > 0 else ("right" if dx < 0 else "left bottom")
        out.append(f'\t(wire (pts (xy {fmt(ax)} {fmt(ay)}) (xy {fmt(ex)} {fmt(ey)})) '
                   f'(stroke (width 0) (type default)) (uuid "{new_uuid()}"))')
        out.append(f'\t(label "{net}" (at {fmt(ex)} {fmt(ey)} 0) (fields_autoplaced yes) '
                   f'(effects (font (size 1.27 1.27)) (justify {just})) (uuid "{new_uuid()}"))')
    return out

def main():
    global PWR_FLAG_DEF
    PWR_FLAG_DEF = _load_pwr_flag_def()
    ensure_pwr_flag_in_lib()
    syms = load_library()
    missing = [p["sym"] for p in PARTS if p["sym"] not in syms]
    if missing:
        raise SystemExit(f"symbols missing from library: {missing}")

    normalize_library_pin_types()
    syms = load_library()   # reload after normalising

    used = {p["sym"] for p in PARTS}
    lib_text = LIB.read_text()
    # embed the library's own text (renamed with the nickname) so the schematic copy
    # is byte-identical to the library and KiCad reports no lib_symbol_mismatch
    lib_symbols = [raw_symbol_block(lib_text, "PWR_FLAG").replace(
        '(symbol "PWR_FLAG"', '(symbol "TEG:PWR_FLAG"', 1)]
    for name in sorted(used):
        lib_symbols.append(raw_symbol_block(lib_text, name).replace(
            f'(symbol "{name}"', f'(symbol "TEG:{name}"', 1))

    # auto-flow placement (columns wrap when tall enough); snapped to the 1.27 mm
    # connection grid so pin/wire endpoints stay on-grid for ERC
    col_x, y, col_maxw, placed = 30.48, 30.48, 0.0, []
    for part in PARTS:
        pins, bbox = symbol_info(syms[part["sym"]])
        part["_bbox"] = bbox
        part["_center"] = ((bbox[0] + bbox[1]) / 2, (bbox[2] + bbox[3]) / 2) if bbox else (0, 0)
        span_x = max(abs(p["x"]) for p in pins) if pins else 5
        span_y = max(abs(p["y"]) for p in pins) if pins else 5
        rh, w = 2 * span_y + 14, 2 * span_x + 16
        if y + rh > 195:
            col_x += col_maxw + 20
            y, col_maxw = 30.48, 0.0
        # snap to the 1.27 mm connection grid (pin offsets are grid multiples)
        pos = (round(col_x / 1.27) * 1.27, round(y / 1.27) * 1.27)
        placed.append((part, pins, pos))
        col_maxw = max(col_maxw, w)
        y += rh

    pins_out, insts = [], []
    for part, pins, pos in placed:
        insts.append(emit_instance(part, pins, pos))
        pins_out += emit_pin_net(pins, part, pos)
        # explicit no-connect markers for pins left unnetted (e.g. MT3608 pin 6)
        for p in pins:
            if part["nets"].get(p["num"]) is None and p["num"] is not None:
                ax, ay = pos[0] + p["x"], pos[1] - p["y"]
                pins_out.append(f'\t(no_connect (at {fmt(ax)} {fmt(ay)}) (uuid "{new_uuid()}"))')

    # PWR_FLAG on every net that sources power, so power-input pins are "driven"
    flag_x = 12.7
    for i, net in enumerate(POWER_FLAGS):
        fy = 30.48 + i * 10.16
        insts.append(emit_pwr_flag(net, flag_x, fy))
        pins_out.append(f'\t(wire (pts (xy {fmt(flag_x)} {fmt(fy)}) (xy {fmt(flag_x + 2.54)} {fmt(fy)})) '
                        f'(stroke (width 0) (type default)) (uuid "{new_uuid()}"))')
        pins_out.append(f'\t(label "{net}" (at {fmt(flag_x + 2.54)} {fmt(fy)} 0) (fields_autoplaced yes) '
                        f'(effects (font (size 1.27 1.27)) (justify left)) (uuid "{new_uuid()}"))')

    lines = ["(kicad_sch",
             "\t(version 20231120)",
             '\t(generator "gen_schematic.py")',
             '\t(generator_version "8.0")',
             f'\t(uuid "{ROOT_UUID}")',
             '\t(paper "A3")',
             "\t(title_block",
             '\t\t(title "TEG Thermal Harvester — Power Conditioning")',
             '\t\t(date "2026-10-09")',
             '\t\t(rev "Draft A")',
             '\t\t(comment 1 "Two Marlow TG12-4-01LS in series -> BQ25504 -> storage -> MT3608 5V -> Noctua NF-A8")',
             "\t)",
             "\t(lib_symbols",
             "\n".join("\t\t" + s for s in lib_symbols),
             "\t)",
             "\n".join(pins_out),
             "\n".join(insts),
             f'\t(text "{NOTES}" (exclude_from_sim no) (at 25.4 270 0) '
             f'(effects (font (size 2 2)) (justify left bottom)) (uuid "{new_uuid()}"))',
             '\t(sheet_instances\n\t\t(path "/" (page "1"))\n\t)',
             ")",
             ""]
    OUT.write_text("\n".join(lines))

    n_nets = sum(1 for p in PARTS for n in p["nets"].values() if n)
    print(f"wrote {OUT.relative_to(ROOT)}  parts={len(PARTS)} pin-labels={n_nets} lib_symbols={len(used)}")

if __name__ == "__main__":
    main()
