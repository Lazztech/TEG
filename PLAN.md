# TEG Thermal Harvester — Working Plan

**Project:** KiCad design for the TEG (thermoelectric generator) thermal-harvesting prototype.
**Owner:** Lazztech · **Started:** 2026-10-08
**Companion docs:** [BOM.md](./BOM.md)

This is a living document. Update the **Changelog** and **Open questions** as work proceeds.

---

## 1. Goal

Continue the thermal-prototype work (originally drafted on Flux.ai) as a **KiCad** project,
with the power-conditioning / energy-harvesting electronics designed for **JLCPCB** fabrication
(SMT assembly + THT).

Thermal/mechanical context carried over from the Flux.ai plan:

- 2 × Coherent/Marlow **TG12-4-01LS** TEGs, electrically **series**, thermally parallel.
- Common hot collector + **Fischer SK 92 150 AL** heatsink; **Noctua NF-A8 5 V PWM** fan.
- One-module baseline first, then two-module comparison; five unassisted cold starts; 0.5 W test load.
- **This repo scope:** the electronics only (harvest front-end → 5 V rail → fan). Thermal/CAD out of scope here.

## 2. Environment & tooling

| Item | Status | Notes |
|------|--------|-------|
| KiCad app / `kicad-cli` | **not installed** | Needed to render/validate; see Open questions |
| `jlc-client` (JLCPCB parts) | **installed globally** | Friend's hosted instance; needs token for component fetch |
| `easyeda2kicad` CLI | **paused** | Superseded by `jlc-client`; left installed, source edits reverted |
| `JLC_API_TOKEN` | provided by user (session only) | Token starts with `-`; must be shell-quoted, e.g. `--token="…"` |

### jlc-client command patterns that work

```bash
# Search (public API, no token needed)
jlc-client search --query "MT3608" --limit 8

# Fetch symbol + footprint + 3D (needs token); -l appends to a .kicad_sym library
JLC_API_TOKEN="…" jlc-client --full --symbol -l ./hardware/libs/TEG.kicad_sym C157471

# Authoritative component data (name/package/symbol/footprint/3D-UUID) as JSON
JLC_API_TOKEN="…" jlc-client --json C157471
```

## 3. Findings

1. **`easyeda2kicad` tool is broken (paused by decision).** Its local passive database parser
   assumes the old `jlcpcb-components-basic-preferred.csv` column layout; the upstream CSV now
   has extra leading columns, so `category`/`value`/`package` are mis-mapped and **all** passive
   searches return "No parts found". (Confirmed by inspecting `~/.cache/jlc-parts/parts-cache.json`
   and `src/parts-db.ts`.) Source edits were made and then reverted; no changes remain.
2. **`jlc-client search` works** but the `--type` flag applies a narrow subcategory filter
   (e.g. `--type ic` → only "Embedded Peripheral ICs"), which hides power-management parts.
   **Use a plain `--query`** (or the attribute search) to find the right part.
3. **BQ25504RGTT (C157471) is stocked** and was the winning harvester front-end. Its full
   symbol/footprint were retrieved (embedded in `--json` output) — recorded in BOM.
4. **The component endpoint is intermittent.** `--json` / `--symbol` / `--footprint` / `--3d`
   intermittently return `{"error":"Component … not found on EasyEDA/LCSC"}` for *every* part,
   then recover. This is a transient outage / rate-limit on the hosted FaaS function — **not** a
   part-availability problem. Symbols and footprints were captured on a retry; **3D WRL models are
   still pending a clean window** (retry `--3d` later).

## 4. Design decisions

| ID | Decision | Rationale |
|----|----------|-----------|
| D1 | Front-end = **BQ25504RGTT** | Only sub-1 V, MPPT-capable harvester found in catalog; cold-starts from ≈330 mV |
| D2 | Post-boost to 5 V = **MT3608** | Cheap, high stock, adequate for a single 5 V fan + test load |
| D3 | Fan switching = **AO3400A** low-side N-MOSFET | Basic part; PWM the fan return |
| D4 | Prefer JLCPCB **basic** passives | Avoids extended-part fees |
| D5 | Input connector = **screw terminal** | Field-flexible TEG wiring during trials |
| D6 | **Two-stage** topology (BQ25504 → storage → MT3608) | Decouples harvester MPPT from load; buffers cold starts & fan inrush |

## 5. KiCad project layout

```
hardware/
├─ TEG.kicad_pro                       # project file (valid JSON)
├─ TEG.kicad_sch                       # root schematic — GENERATED draft (scripts/gen_schematic.py)
├─ TEG.kicad_pcb                       # board — GENERATED draft: 30 footprints placed, 81/82 pads netted, no copper yet
├─ sym-lib-table                       # maps library name "TEG" -> libs/TEG.kicad_sym
├─ fp-lib-table                        # maps library name "TEG" -> footprints/TEG.pretty
├─ libs/TEG.kicad_sym                  # 12 symbols (populated via jlc-client)
├─ footprints/TEG.pretty/              # 10 footprints (populated via jlc-client)
└─ easyeda2kicad.3dshapes/             # 12 WRL 3D models, named as footprints reference them
../scripts/gen_schematic.py            # schematic generator — edit the part/net table here
../scripts/gen_board.py                # board generator — placement map here, netlist shared with gen_schematic
../BOM.md, ../PLAN.md, ../README.md, ../.gitignore
```

### Symbol / footprint mapping (generated)

| Ref | Symbol (`TEG:`) | Footprint (`TEG:`) | LCSC |
|-----|-----------------|--------------------|------|
| U1 | `BQ25504RGTT` | `VQFN-16_L3.0-W3.0-P0.50-TL-EP` | C157471 |
| U2 | `MT3608` | `SOT-23-6_L2.9-W1.6-P0.95-LS2.8-BL` | C84817 |
| Q1 | `AO3400A` | `SOT-23-3_L2.9-W1.3-P1.90-LS2.4-BR` | C20917 |
| D1 | `1N5819WS` | `SOD-323_L1.8-W1.3-LS2.5-RD` | C191023 |
| L1/L2 | `FTC252010S4R7MBCA` | `IND-SMD_L2.5-W2.0-VLS252012CX-150M` | C5832360 |
| R | `0603WAF1002T5E` (10 k) | `R0603` | C25804 |
| R | `0603WAF1003T5E` (100 k) | `R0603` | C25803 |
| C | `CL21A106KAYNNNE` (10 µF) | `C0805` | C15850 |
| C | `CL10A105KB8NNNC` (1 µF) | `C0603` | C15849 |
| C | `CL10B104KA8NNNC` (100 nF) | `C0603` | C1590 |
| J1 | `KF128-5.08-2P` | `CONN-TH_P5.08_KF128-5.08-2P` | C474952 |
| J2 | `PZ254V-11-04P_C2691448` | `HDR-TH_4P-P2.54-V-M` | C2691448 |

### Schematic sheets (planned)

Draft currently uses a **single root sheet** with block annotations; to be split later:

- `power-input` — J1, D1, input caps
- `energy-harvest` — U1 BQ25504 + L1, C_in, programming resistor network
- `rail-5v` — U2 MT3608 + L2, output caps, feedback divider
- `fan-drive` — Q1, gate resistor, J2
- `test` — storage element + 0.5 W load interface

## 6. Open questions

- [ ] **KiCad not installed.** Install KiCad (for `kicad-cli` ERC/netlist/plot) or proceed
      hand-authored and validate on your machine?
- [ ] **Storage element:** supercapacitor vs. Li-ion cell? Sets VBAT-OV/UV programming and
      whether a ~330 mV cold start is meaningful in practice.
- [ ] **Fan inrush vs. 5 V rail:** MT3608 sizing + output bulk to survive NF-A8 startup.
- [ ] **Test-load interface:** fixed 0.5 W resistor, electronic load, or connector only?
- [ ] **MPPT sampling network** (VOC-SAMP / VREF-SAMP) values from BQ25504 datasheet.

## 7. Next steps

1. ~~Populate `hardware/libs` and `hardware/footprints`~~ **done** (symbols + footprints + 3D WRL captured).
2. Install KiCad, open `hardware/TEG.kicad_pro`, run ERC on the generated schematic and DRC on the
   generated board; convert the label-per-pin schematic into routed wires / hierarchical sheets.
3. Compute the BQ25504 programming resistor network (R1–R7) and the MT3608 5 V divider (R8/R9);
   finalize values.
4. Select storage element (supercap vs Li-ion) and the 0.5 W test-load element; add to BOM and netlist.
5. Route the board (GND pour first, then power), add a GND zone, and re-check DRC.
6. Export Gerbers/drill + JLCPCB `BOM.csv` / `CPL.csv`; produce a fabrication checklist
   (stackup, assembly side, part rotations).

## 8. Changelog

| Date | Change |
|------|--------|
| 2026-10-08 | Tooling set up; `jlc-client` verified; BQ25504RGTT confirmed; BOM.md + PLAN.md created; draft KiCad project authored |
| 2026-10-09 | 3D WRL models fetched (12) and renamed to the filenames the footprints reference; README.md added; schematic regenerated by `scripts/gen_schematic.py` — 30 parts placed, every mapped pin labeled with its net (label-per-pin draft); BOM.md synced to the draft netlist (added D2 catch diode, J3 test-load terminal, R1–R12 programming/control resistors) |
| 2026-10-09 | Board draft started: `scripts/gen_board.py` generates `TEG.kicad_pcb` from the **same** part/net table (30 footprints placed in a block layout, 82 pads / 81 netted, ratsnest-only, ~104×84 mm outline). Board is legacy-format (KiCad 5 `20171130`) because the fetched footprints are legacy-style; modern KiCad migrates on open |
| 2026-10-09 | **KiCad 10.0.6 installed** (~/Applications, no sudo — Homebrew cask needs admin). Real validation now runs: ERC reduced 174 → 1 warning by (a) snapping placements to the 1.27 mm connection grid, (b) mapping the fetched symbols' `unspecified` pin types to power_in/output/passive by pin name, (c) adding PWR_FLAGs on GND/+5V/VBAT/VSTOR/TEG+ (def pulled from the installed KiCad power lib), (d) no-connect marker on MT3608 pin 6. Remaining ERC warning: `VBAT_OK` isolated label — intentional, reserved for status LED/test point. **DRC: 0 violations** (59 unconnected = unrouted ratsnest, expected). PDF renders in `build/` |
