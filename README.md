# TEG — Thermal Energy Harvesting Prototype

Electronics for a thermal energy harvesting prototype: a small TEG array feeds a
sub-1 V energy-harvesting front-end (BQ25504), which charges a storage element and
backs up a regulated 5 V rail for a Noctua 5 V PWM fan and a test load.

Originally drafted on **Flux.ai**; this repo is the **KiCad** continuation, prepared
for **JLCPCB** fabrication (SMT + THT).

> Status: **draft, KiCad-validated**. All 30 parts placed in schematic and board with nets
> assigned; ERC passes with 1 intentional warning, board DRC passes with 0 violations
> (copper not routed yet — ratsnest only). See [PLAN.md](PLAN.md).

## Repo layout

| Path | What it is |
|------|------------|
| [BOM.md](BOM.md) | Bill of materials with LCSC part numbers, stock, and selection notes |
| [PLAN.md](PLAN.md) | Living plan: findings, design decisions, open questions, next steps, changelog |
| `hardware/TEG.kicad_pro` | KiCad project |
| `hardware/TEG.kicad_sch` | Root schematic (draft, auto-generated — nets defined by pin labels) |
| `hardware/TEG.kicad_pcb` | Board draft (auto-generated — footprints placed and netted, no copper routed yet) |
| `hardware/libs/TEG.kicad_sym` | Project symbol library (`TEG:`) — 12 symbols |
| `hardware/footprints/TEG.pretty/` | Project footprint library (`TEG:`) — 10 footprints |
| `hardware/easyeda2kicad.3dshapes/` | 3D WRL models, named as the footprints reference them |
| `scripts/gen_schematic.py` | Regenerates `TEG.kicad_sch` from the part/net table inside it |
| `scripts/gen_board.py` | Regenerates `TEG.kicad_pcb` (shares the netlist with `gen_schematic.py`) |

## Opening the project

Open `hardware/TEG.kicad_pro` in **KiCad 7 or 8**. The local library tables
(`sym-lib-table`, `fp-lib-table`) are already set up, so all parts are available
under the `TEG:` nickname.

The root schematic is **generated** — edit `scripts/gen_schematic.py` (part list +
pin→net map) and re-run it rather than hand-editing the `.kicad_sch`:

```bash
python3 scripts/gen_schematic.py
```

## Tooling — JLCPCB parts (`jlc-client`)

`jlc-client` is installed globally and talks to a hosted JLCPCB/EasyEDA service.
Component fetches need a token; it starts with `-`, so it must be **quoted**:

```bash
# Search the catalog (public, no token)
jlc-client search --query "MT3608" --limit 8

# Fetch symbol + footprint + 3D model and append the symbol to the project library
JLC_API_TOKEN='<token>' jlc-client --symbol -l ./hardware/libs/TEG.kicad_sym \
    --footprint -o ./hardware/footprints C157471 C84817

# Authoritative part data (name/package/symbol/footprint/3D UUID) as JSON
JLC_API_TOKEN='<token>' jlc-client --json C157471
```

Notes learned the hard way (see [PLAN.md](PLAN.md) §3):

- `jlc-client search --type ic` filters to one subcategory and hides power ICs —
  search with a plain `--query` instead.
- The fetch endpoint is **intermittent** (`Component … not found on EasyEDA/LCSC`
  for everything, then recovers) — it is rate-limiting/outage, not missing parts.
  Retry.

## Design in one paragraph

Two Marlow TG12-4-01LS TEG modules in series feed the BQ25504 boost charger through a
screw terminal. The BQ25504 does **MPPT in hardware** (no extra IC): R13/R14 sample a
fraction of the harvester's open-circuit voltage onto a hold cap, and the chip regulates
its input to that fraction. That ratio is set to **≈50 % of Voc** (R13 = R14 = 10 MΩ) —
matched-load MPP for a TEG, *not* the datasheet's 78 % solar figure. The charger fills a
**supercapacitor** on `VBAT` (safer than a battery in a heated device) and exposes `VSTOR`;
an MT3608 boost then regulates a 5 V rail for the Noctua NF-A8 4-pin PWM fan (Tach pull-up,
PWM from a test header) and a switchable 0.5 W test load (AO3400A low-side MOSFET).
Two-stage on purpose: it keeps the harvester's MPPT decoupled from load transients and
lets a cold-start charge the storage before the 5 V boost is asked to run.

Open questions and thermal/mechanical context: [PLAN.md](PLAN.md).
