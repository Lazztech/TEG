# TEG — Thermal Energy Harvesting Prototype

Electronics for a thermal energy harvesting prototype: a small TEG array feeds a
sub-1 V energy-harvesting front-end (BQ25504), which charges a storage element and
backs up a regulated 5 V rail for a Noctua 5 V PWM fan and a test load.

Originally drafted on **Flux.ai**; this repo is the **KiCad** continuation, prepared
for **JLCPCB** fabrication (SMT + THT).

> **Status: design complete, KiCad-validated, and every part sourced from the JLCPCB
> catalogue.** 32 parts placed in both schematic and board with nets assigned; board DRC
> passes with **0 violations**. Two things remain before ordering: **one decision** (the
> storage element — see below) and **routing the copper**.

## Decisions made (and why)

These are settled — no further choices needed for a first prototype.

| Question | Decision | Why |
|----------|----------|-----|
| **Storage: battery or supercap?** | **Supercapacitor** (0.22–0.47 F, 5.5 V) | Much safer in a *thermal* device: no fire/thermal-runaway risk, tolerant of heat and cold (Li-ion must not be charged below 0 °C). Simpler — no protection circuitry. Also matches the load: the fan is a short burst, not a continuous draw. Trade-off accepted: supercap leakage must be measured, as it can exceed what the TEGs harvest |
| **MPPT?** | **Yes — built into the BQ25504** | The chip does sample-and-hold MPPT in hardware; no extra IC, no firmware |
| **MPPT ratio** | **≈50 % of Voc** (`R13` = `R14` = 10 MΩ) | A TEG makes maximum power at a matched load, ≈50 % of its open-circuit voltage. The datasheet's 78 % default is tuned for *solar* panels — copying it would have thrown away real power |
| **Storage voltage window** | **VBAT_OV 3.15 V** (datasheet-verified) | Conservative and tested. Less runtime than a ~5.0 V window, but it protects the cap and is known-good. Tune later once real behaviour is measured |
| **Charge cutoff** | `OT_PROG` → GND = **65 °C** cutoff | Sensible protection for a device that is warm by design |

## Remaining tasks — from here to a working prototype

| # | Task | Notes |
|---|------|-------|
| 1 | **Decide the storage element** | The one open design question — options A–D above |
| 2 | **Route the copper** | The main remaining work. Board is placed and netted but unrouted (ratsnest only). Ground pour first, then power, then signals |
| 3 | **Export fab files** | Gerbers + drill, plus JLCPCB `BOM.csv` / `CPL.csv` (no script yet) |
| 4 | **Order the PCB** | JLCPCB SMT assembly can place the SMD parts; the supercap is hand-soldered |
| 5 | **Bench-verify before trusting the TEGs** | Drive the input from a bench supply that emulates the TEG (start ~1 V, low current limit) and confirm the rail comes up and the fan starts |
| 6 | **Then the thermal tests** | One-module baseline, two-module comparison, five cold starts, 0.5 W load — per [PLAN.md](PLAN.md) |

### The one open decision: storage

**JLCPCB stocks no supercapacitors** (verified against their own API — `supercapacitor`,
`EDLC`, `5.5V 1F` all return 0 results; no batteries either). So that single part cannot be
machine-assembled. Four options, detailed with stored energy and effort in
[BOM.md](BOM.md#️-open-decision--the-storage-element):

- **A — hand-solder one supercap** (2 joints): keeps the design, ≈2–4 s of fan. *Recommended.*
- **B — plug-in supercap** via a 2-pin header: no soldering, slightly bulkier.
- **C — coin-cell holder** (JLCPCB-assembled) + user-inserted LiFePO₄ cell: hours of runtime,
  needs the threshold network recomputed.
- **D — electrolytic buffer only**: 100 % JLCPCB, but **cannot run the fan** from storage.

Everything else is sourced:

| Ref | Part | LCSC | Stock |
|-----|------|------|-------|
| `L1`, `L2` | 22 µH `SWPA4020S220MT` | C82401 | 6 007 |
| `R1`/`R2`/`R3`/`R4`+`R15`/`R7`/`R6` | 5.90 / 4.02 / 5.60 / 4.42 / 4.22 / 1.43 MΩ | C2076902 / C137708 / C23190 / C166806 / C166807 / C166898 | 775 – 58 k |
| `R8` / `R9` | 73.2 kΩ / 10 kΩ (MT3608 → **5.0 V**) | C2933257 / C25804 | ok |
| `R10` / `R13`,`R14` | 1 kΩ / 10 MΩ | C21190 / C114606 | ok |

⚠️ `U1` `BQ25504RGTT` (C157471) is **low stock (7)** — `C2876746` (BQ25504RGTR, 21) is the
same part if it runs out.

## What to expect (read this before testing)

**Two TG12-4 modules produce only a few hundred mW at useful ΔT, while the fan draws
~0.5 W.** So the fan will run in **bursts**, or only when ΔT is high — it will not run
continuously from the TEGs alone. That is the expected behaviour, not a fault; the plan
already scopes the test load as "0.5 W *where sufficient power exists*".

## Repo layout

| Path | What it is |
|------|------------|
| [BOM.md](BOM.md) | Bill of materials: 32 parts, LCSC numbers, MPPT explanation, sourcing notes |
| [PLAN.md](PLAN.md) | Living plan: findings, decisions, open questions, next steps, changelog |
| `hardware/TEG.kicad_pro` | KiCad project |
| `hardware/TEG.kicad_sch` | Root schematic (auto-generated — nets defined by pin labels) |
| `hardware/TEG.kicad_pcb` | Board (auto-generated — 32 footprints placed and netted, **no copper routed yet**) |
| `hardware/libs/TEG.kicad_sym` | Project symbol library (`TEG:`) — 14 symbols |
| `hardware/footprints/TEG.pretty/` | Project footprint library (`TEG:`) — 10 footprints |
| `hardware/easyeda2kicad.3dshapes/` | 3D WRL models, named as the footprints reference them |
| `scripts/gen_schematic.py` | Regenerates `TEG.kicad_sch` from the part/net table inside it |
| `scripts/gen_board.py` | Regenerates `TEG.kicad_pcb` (shares the netlist with `gen_schematic.py`) |
| `scripts/validate.sh` | Runs KiCad ERC (schematic) and DRC (board); needs `kicad-cli` |
| `scripts/jlc_lookup.py` | Queries **JLCPCB's own parts API** — id, library type, stock |

## Opening the project

Open `hardware/TEG.kicad_pro` in **KiCad 7 or 8** (validated with KiCad 10). The local
library tables (`sym-lib-table`, `fp-lib-table`) are already set up, so all parts are
available under the `TEG:` nickname.

The schematic and board are **generated** — edit the part/net table in
`scripts/gen_schematic.py` (and placements in `scripts/gen_board.py`) and re-run them
rather than hand-editing the `.kicad_sch` / `.kicad_pcb`:

```bash
python3 scripts/gen_schematic.py   # -> hardware/TEG.kicad_sch
python3 scripts/gen_board.py       # -> hardware/TEG.kicad_pcb
./scripts/validate.sh              # ERC + DRC (needs kicad-cli)
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
- The public search API also **degrades** (returning generic results for any query) — as of
  2026-10-10 it returns the same high-stock list for *every* query, so it cannot source parts.
  Use `scripts/jlc_lookup.py` (JLCPCB's own API) to find parts, and `jlc-client --json <id>`
  to fetch a part's symbol/footprint once you have its id.

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
