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
| `scripts/jlc_lookup.py` | **added** | Queries **JLCPCB's own parts API** (id, library type, stock). Needed because `jlc-client`'s search index is degraded |
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
4. **`jlc-client`'s *search* index is degraded** (2026-10-10): it returns the same high-stock
   parts for every query (`MT3608`, `5.9MΩ`, `supercapacitor` all returned an identical list),
   so it cannot be used to source parts. Worked around with `scripts/jlc_lookup.py`, which uses
   JLCPCB's own `selectSmtComponentList` API and was reliable. Individual component *fetches*
   by LCSC id still work well.
5. **JLCPCB stocks no supercapacitors and no batteries** — confirmed (0 results for
   `supercapacitor`, `EDLC`, `5.5V 1F`, `0.1F 5.5V`). They cannot be machine-assembled; see the
   storage decision in [BOM.md](BOM.md).
6. **The component endpoint is intermittent.** `--json` / `--symbol` / `--footprint` / `--3d`
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

## 4b. v2 power-path design decisions (in progress)

Concrete choices for the ~3–4 W board. Every part number verified in the JLCPCB catalogue via
`scripts/jlc_lookup.py`.

| Element | Decision | Part |
|---------|----------|------|
| Front-end converter | **Buck**, 3 A, up to 28 V in, SOIC-8. Covers the ~6–9 V operating point and up to ~20 V open circuit. **Open:** at low ΔT the array drops below 5 V, so a **buck-boost** may be needed for cold start (E6) | **TPS54331DR — C9865** (ext, 348 k stock) |
| MPPT approach | For a *resistive* source a constant-power load naturally drags the input toward ~V_oc/2 — the maximum-power point — so a buck with sensible input **UVLO** approximates MPPT. Add explicit fractional-V_oc regulation only if bench measurement earns it | — |
| USB-C receptacle | 16-pin SMD | **TYPE-C-31-M-12 — C165948** (ext, 408 k) |
| USB-A receptacle | SMD | **AF 10.0 QT-ZB6.8 — C456016** (ext, 21 k) |
| USB-C role | **Source (DFP)**: Rp on CC1/CC2 to VBUS. **56 kΩ advertises 500 mA/port** — honest for a 3–4 W shared output (22 kΩ = 1.5 A, 10 kΩ = 3 A if one fast port is wanted later) | **56 kΩ — C23206** (base) |
| USB-A role | **DCP** (dedicated charging port): tie **D+ to D−**, no IC needed | — |
| USB-C PD | **Not included yet** — only if reliable battery-bank charging is required (open question 2) | — |
| Fan driver | Low-side N-MOSFET + gate resistor, reusing the existing part | **AO3400A — C20917** (base) |

**Still blocked on inputs:** the module datasheet (module count → array voltage → the buck's input
range and the V_oc/2 setpoint), the USB role (whether PD is needed), and the fireplace surface
temperature (hot-side clamp and magnet grade).

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
- [x] **Storage element:** **supercapacitor** (decided 2026-10-09) — safer in a thermal device
      (no fire/thermal-runaway, cold-tolerant), simpler, matches the burst nature of the fan load.
      Trade-off accepted: leakage must be measured (it can exceed the harvested current).
      Li-ion/LiFePO4 rejected for now; revisit only if multi-hour retention is needed.
- [ ] **Voltage window:** adopt the datasheet example (VBAT_OV 3.15 V) — conservative and
      1 %-verified — or recompute R1–R7 for ~5.0 V to roughly triple usable fan energy? Needs
      TI's design equations (hand-derivation from the PDF is unreliable; equations are images).
- [ ] **MPPT ratio confirmation:** draft uses R13/R14 = 10 MΩ/10 MΩ → ≈50 % of Voc
      (TEG matched load). Verify against measured TEG MPP; consider making it selectable.
- [x] **JLCPCB part selection** — all values found and verified in the catalogue, including the
      odd E96 resistors (C2076902, C137708, C23190, C166806, C166807, C166898) and the 22 µH
      inductor (C82401). `BQ25504RGTT` (C157471) is **low stock (7)**; fallback `C2876746` (21).
- [ ] **Decide the storage element** (BOM.md options A–D) — blocks board placement and routing.
- [x] MT3608 feedback divider computed: 73.2 k / 10 k → 5.0 V.
- [ ] **Fan inrush vs. 5 V rail:** MT3608 sizing + output bulk to survive NF-A8 startup.
- [ ] **Test-load interface:** fixed 0.5 W resistor, electronic load, or connector only? (J3 present.)
- [ ] **`VBAT_OK`** left unconnected (ERC warns) — wire to a status LED or test point on the storage decision?

## 7. Next steps

1. ~~Populate `hardware/libs` and `hardware/footprints`~~ **done** (symbols + footprints + 3D WRL captured).
2. ~~Install KiCad; run ERC/DRC~~ **done** (KiCad 10.0.6; ERC 1 warning, DRC 0 violations).
3. ~~Compute the BQ25504 threshold network~~ **done** (datasheet worked example; R1–R4, R15/R7/R6).
   Still open: MT3608 feedback divider (R8/R9) for an exact 5.0 V.
4. ~~Select storage element~~ **done** — supercapacitor (0.22–0.47 F, 5.5 V). Still open: pick the
   specific low-leakage part and the 0.5 W test-load element.
5. **Route the board** — GND pour first, then power, then signals; re-check DRC.
6. **Source the remaining parts** — supercap (hand-solder), 22 µH inductor, the six odd E96
   resistors, R8/R9, R10. See the parts table in [README.md](README.md).
7. **Export Gerbers/drill + JLCPCB `BOM.csv` / `CPL.csv`**; add a fabrication checklist
   (stackup, assembly side, part rotations). No script yet.
8. **Bench-verify** the board from a bench supply emulating the TEG before running the thermal tests.
9. **Thermal tests** — one-module baseline, two-module comparison, five cold starts, 0.5 W load.
10. Optional follow-ups: make the MPP ratio selectable (R13/R14) for measurement; recompute
    R1–R7 for a wider (~5.0 V) voltage window; consider an onboard MCU for fan PWM.

## 8. Changelog

| Date | Change |
|------|--------|
| 2026-10-10 | **TEG module datasheet obtained and extracted** (Coherent TG12-4, 3 pages) — closes the "datasheet verification pending" item open since day one. Verified: **200 °C continuous** rating (230 °C intermittent), AC resistance 2.76–3.41 Ω, **clamp at 1.4 MPa (200 psi)**, thermal resistance ~2.2 °C/W, and power/voltage/current tables at cold side 50 °C. **The earlier estimate was ~3× pessimistic**: at hot 170 °C a module makes **2.12 W** (not ~0.7 W), so **2 modules ≈ 3.2 W and 3 modules ≈ 4.8 W** at a 150 °C hot side — E1 is met with 2–3 modules. Also established: V_mp/V_oc ≈ 0.57 (fractional-V_oc MPPT confirmed), the **cold side is the binding constraint** (~150 W to reject for ~4.8 W electrical, so expect 3–4 W with a practical fan-cooled heatsink), and at low ΔT the array voltage falls below a 5 V buck's input so a buck-boost may be needed for cold start. Sourced via alldatasheet → Bing → Coherent's own PDF (the direct search engines were blocked from this environment; the PDF came from coherent.com) |
| 2026-10-10 | **Project re-scoped by [REQUIREMENTS.md](REQUIREMENTS.md)**: fireplace-mounted wedge harvester, **~3–4 W**, 1 × USB-A + 1 × USB-C sharing the output, **fan-cooled** (no water), total BOM ≤ $200. The BQ25504 board (≤300 mW) becomes a validated sub-watt **reference**, not the deliverable. Corrected an earlier error: the first 5–10 W analysis assumed passive cooling at ΔT ≈ 50 °C; with fan-forced cooling at ΔT ≈ 70 °C per-module output roughly doubles, so a few watts needs 2–3 modules, not 10–20. Key new parts identified and verified in the JLCPCB catalogue: buck front end **TPS54331DR (C9865)**, USB-C receptacle **TYPE-C-31-M-12 (C165948)**, SMD USB-A **AF 10.0 QT-ZB6.8 (C456016)**; fan driver reuses AO3400A (C20917) |
|------|--------|
| 2026-10-08 | Tooling set up; `jlc-client` verified; BQ25504RGTT confirmed; BOM.md + PLAN.md created; draft KiCad project authored |
| 2026-10-09 | 3D WRL models fetched (12) and renamed to the filenames the footprints reference; README.md added; schematic regenerated by `scripts/gen_schematic.py` — 30 parts placed, every mapped pin labeled with its net (label-per-pin draft); BOM.md synced to the draft netlist (added D2 catch diode, J3 test-load terminal, R1–R12 programming/control resistors) |
| 2026-10-09 | Board draft started: `scripts/gen_board.py` generates `TEG.kicad_pcb` from the **same** part/net table (30 footprints placed in a block layout, 82 pads / 81 netted, ratsnest-only, ~104×84 mm outline). Board is legacy-format (KiCad 5 `20171130`) because the fetched footprints are legacy-style; modern KiCad migrates on open |
| 2026-10-09 | **KiCad 10.0.6 installed** (~/Applications, no sudo — Homebrew cask needs admin). Real validation now runs: ERC reduced 174 → 1 warning by (a) snapping placements to the 1.27 mm connection grid, (b) mapping the fetched symbols' `unspecified` pin types to power_in/output/passive by pin name, (c) adding PWR_FLAGs on GND/+5V/VBAT/VSTOR/TEG+ (def pulled from the installed KiCad power lib), (d) no-connect marker on MT3608 pin 6. Remaining ERC warning: `VBAT_OK` isolated label — intentional, reserved for status LED/test point. **DRC: 0 violations** (59 unconnected = unrouted ratsnest, expected). PDF renders in `build/` |
| 2026-10-09 | **Storage decided: supercapacitor** (0.22–0.47 F, 5.5 V). **MPPT gap found and fixed:** the BQ25504 has MPPT built in, but the draft was *missing its sampling network* — added R13/R14 (10 MΩ/10 MΩ → ≈50 % of Voc, TEG matched-load, vs the datasheet's solar 78 %) and set CREF/CBYP = 10 nF (C1589). Also fixed the OV/UV chain order to the datasheet topology, added the missing third OK-chain resistor (R15), and corrected L1/L2 to the datasheet-recommended 22 µH. 32 parts / 85 pins; ERC 1 warning, DRC 0 violations. BOM rev B |
| 2026-10-10 | **Board routed with FreeRouting and DRC-clean.** Used the standard SPECCTRA round-trip, scripted as `scripts/freeroute.sh`: KiCad python exports `.dsn` (incl. net classes) → FreeRouting routes → `.ses` imported back → DRC verifies. FreeRouting reported 0 unrouted / 0 violations; KiCad DRC agrees (**0 violations, 0 unconnected**). Needed a JDK 25 for the jar (the bundled native CLI build crashes on GraalVM serialization) and `trace_min` lowered to 0.15 mm because FreeRouting fans out U1 at 0.15 (still above JLCPCB's 0.127 floor). Also nudged C2's reference text in the footprint to clear its own silkscreen. Fab outputs (gerbers, drill, position, JLCPCB BOM) generated into `build/fab/`. |
| 2026-10-10 | **Scripted autoroute attempted and abandoned.** Built `scripts/route_board.py` (2-layer maze router, rectangular pad obstacles, per-pad fanout for the 0.5 mm VQFN, vias, net ordering) and iterated against `kicad-cli` DRC. Bugs found and fixed along the way: occupancy map initialised to the blocked sentinel (so nothing blocked), unconnected pads not treated as obstacles, SMD terminals allowed to finish on the wrong layer, and 0.3 mm tracks physically unable to escape 0.5 mm pitch. Result: ~95 % connected but never DRC-clean — the clearance/routability trade-off needs rip-up-and-retry or push-and-shove. **Board restored to the clean unrouted state**; attempt kept in `build/TEG-routed-attempt.kicad_pcb`; interactive routing recommended. ERC 3 cosmetic / DRC 1 cosmetic + unrouted |
| 2026-10-10 | **Storage decided — option D: electrolytic buffer only, so the board stays 100 % JLCPCB-assembled.** Added `C2` = 1000 µF 6.3 V SMD electrolytic (`C970711`, polarised) on VBAT; `VBAT_OK` left unconnected with a no-connect marker (available later for load gating). Consequence documented: the fan can only run on live harvest, not from storage. Verified from the datasheet that VBAT_OK is a low-drive digital output referenced to VSTOR, so gating it would need extra parts — deferred. Board is 33 parts now. Remaining: routing. BOM rev D |
| 2026-10-10 | **All parts sourced from the JLCPCB catalogue and verified** (id + library type + stock) using a new `scripts/jlc_lookup.py` (JLCPCB's own API) because `jlc-client`'s search index had degraded to returning identical high-stock lists for every query. Confirmed **JLCPCB stocks no supercapacitors or batteries** (0 results), so the two open decisions are (a) how to add storage and (b) routing. MT3608 divider computed (73.2 k/10 k = 5.0 V); ERC has 2 cosmetic `lib_symbol_mismatch` warnings on the new inductor symbol (embedded text is byte-identical to the library — unresolved KiCad quirk) alongside the 1 intentional warning. BOM rev C |
| 2026-10-10 | R13/R14 given a real part (**C114606**, 10 MΩ 1 % 0603). Sourcing reality recorded: JLCPCB does **not stock supercapacitors** (hand-solder), and the six odd E96 resistors are standard parts but unresolvable through the degraded public search API. Removed a duplicate `PWR_FLAG` entry from the symbol library. **README expanded** with the settled decisions, a remaining-tasks checklist, the parts-to-source table, and the power-budget expectation |
