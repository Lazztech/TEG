# Bill of Materials — TEG Thermal Harvester

**Project:** Thermal Energy Harvesting Prototype (TEG power-conditioning board)
**Target assembly:** JLCPCB SMT + THT
**Revision:** Draft A — 2026-10-09
**Status:** Part selection grounded in JLCPCB catalog lookups; draft netlist generated
(30 parts / 81 labeled pins) in [hardware/TEG.kicad_sch](hardware/TEG.kicad_sch) and a placed
board draft in [hardware/TEG.kicad_pcb](hardware/TEG.kicad_pcb) — not yet ERC/DRC-checked. See [PLAN.md](./PLAN.md).

> Source of part data: `jlc-client` against the JLCPCB catalog / EasyEDA. Stock and
> `basic`/`extended` flags were read at the time of writing and will drift — re-verify
> before ordering.

---

## Functional blocks

```
 TEG array (2 x Marlow TG12-4-01LS, series)
        |
   J1 --+-- TEG input (screw terminal)   D1 = reverse-polarity clamp (parallel, NOT series)
        |
        +--> U1 BQ25504RGTT  (ultra-low-voltage boost charger + MPPT)
                  |  L1 in VIN-DC<->LBST, C1 input bulk, C2/C3 sampling caps,
                  |  R1-R7 programming network (values TBD)
                  v
             VBAT / VSTOR --> storage element (supercap / cell) [TBD]
                  |
             U2 MT3608  (boost -> regulated 5 V)  L2, D2 catch diode, R8/R9 feedback
                  |
                +5V rail --> J2 fan (Noctua NF-A8, 4-pin PWM; R11 Tach pull-up)
                          +-> J3 test-load (0.5 W) switched by Q1 (R10/R12 gate)
```

## BOM

| Ref | Qty | Value / Part | LCSC | Package | Basic? | Function | Notes |
|-----|-----|--------------|------|---------|--------|----------|-------|
| U1 | 1 | **BQ25504RGTT** | C157471 | VQFN-16 3x3 | ext | Ultra-low-power boost charger / energy harvester (TI), MPPT, cold-start ~330 mV | **Key part — confirmed stocked** (~249). Alt: BQ25504RGTR `C2876746` |
| U2 | 1 | **MT3608** | C84817 | SOT-23-6 | ext | Boost converter -> regulated 5 V rail from VSTOR | Asynchronous — needs D2. High stock (~281 k) |
| Q1 | 1 | **AO3400A** | C20917 | SOT-23 | **basic** | Low-side N-MOSFET switch for the 0.5 W test load | Very high stock |
| D1 | 1 | **1N5819WS** | C191023 | SOD-323 | **basic** | Reverse-polarity clamp **across** the TEG input | Series diode would drop voltage and kill the ~330 mV cold start |
| D2 | 1 | **1N5819WS** | C191023 | SOD-323 | **basic** | Catch diode for the MT3608 boost stage | Same part as D1 — order qty 2 |
| L1 | 1 | 4.7 uH | C5832360 | 1008 (2.5x2.0 mm) | ext | BQ25504 boost inductor (160 mOhm, 2.6 A, 2 A sat) | Alt: `C177246` FXL0530-4R7-M (60 mOhm, 4.5 A) |
| L2 | 1 | 4.7 uH | C5832360 | 1008 | ext | MT3608 boost inductor | Same part as L1 — order qty 2 |
| C1 | 1 | 10 uF | C15850 | 0805 X5R | **basic** | TEG input bulk (`CL21A106KAYNNNE`) | |
| C4 | 1 | 10 uF | C15850 | 0805 X5R | **basic** | VSTOR bulk | |
| C5 | 1 | 10 uF | C15850 | 0805 X5R | **basic** | VBAT bulk | |
| C6 | 1 | 10 uF | C15850 | 0805 X5R | **basic** | +5 V output bulk | |
| C7 | 1 | 1 uF | C15849 | 0603 X5R | **basic** | +5 V HF decoupling (`CL10A105KB8NNNC`) | |
| C8 | 1 | 100 nF | C1590 | 0603 X7R | **basic** | VSTOR HF decoupling (`CL10B104KA8NNNC`) | |
| C2 | 1 | 100 nF | C1590 | 0603 X7R | **basic** | VOC-SAMP sampling cap | |
| C3 | 1 | 100 nF | C1590 | 0603 X7R | **basic** | VREF-SAMP sampling cap | |
| R1-R4 | 4 | TBD | TBD | 0603 1 % | **basic** | BQ25504 VBAT-OV/UV/VRDIV divider chain | Values pending datasheet math |
| R5 | 1 | TBD | TBD | 0603 1 % | **basic** | BQ25504 OT-PROG | Values pending datasheet math |
| R6, R7 | 2 | TBD | TBD | 0603 1 % | **basic** | BQ25504 OK-PROG / OK-HYST | Values pending datasheet math |
| R8, R9 | 2 | TBD | TBD | 0603 1 % | **basic** | MT3608 +5 V feedback divider (Vref 0.6 V) | R8 top / R9 bottom |
| R10 | 1 | 1 k | TBD | 0603 | **basic** | Q1 gate series resistor | Value provisional |
| R11 | 1 | 10 k | C25804 | 0603 1 % | **basic** | Fan Tach pull-up to +5 V (`0603WAF1002T5E`) | |
| R12 | 1 | 100 k | C25803 | 0603 1 % | **basic** | Q1 gate pull-down (load off by default) | `0603WAF1003T5E` |
| J1 | 1 | **KF128-5.08-2P** | C474952 | THT P=5.08 mm | ext | TEG array input (2-pos screw terminal) | Alt: DB142R-5.08-2P `C2898709` |
| J2 | 1 | **PZ254V-11-04P** | C2691448 | THT P=2.54 mm | ext | Fan header, 4-pin (GND / +5V / Tach / PWM) | Matches Noctua 4-pin PWM |
| J3 | 1 | **KF128-5.08-2P** | C474952 | THT P=5.08 mm | ext | Test-load output (same terminal as J1) | Load element itself TBD |
| SC1 | TBD | storage element | - | - | - | Supercapacitor or single Li-ion cell on VBAT | **Open — sizing pending** |

### Notes on selection

- **BQ25504 is the linchpin.** It is the only true sub-1 V energy-harvesting front-end found
  in the catalog (MPPT + programmable VBAT-OV/UV + cold start). Exact-MPN searches initially
  looked empty only because the tool's part-type filter narrows to one subcategory; a plain
  text query finds it. Authoritative symbol/footprint were fetched successfully for it.
- **D1 must be a parallel clamp, not a series diode.** A series Schottky drop (0.3-0.4 V)
  at the input would defeat the whole point of a ~330 mV cold start.
- **Fan speed is driven by an external PWM source on J2 pin 4** (the board has no MCU);
  that same signal optionally gates the test load via R10/R12. Whether to onboard an MCU
  is an open question in [PLAN.md](./PLAN.md).
- **Passives chosen are JLCPCB *basic*** where possible (10 k/100 k, 1 uF/10 uF MLCC, 100 nF)
  to avoid extended-part setup fees.

## Not stocked / ruled out

| Candidate | Why not used |
|-----------|--------------|
| LTC3105 | Not found in JLCPCB catalog |
| ADP5090 | Not found in JLCPCB catalog |
| SPV1050 | Not found in JLCPCB catalog |

## Library / KiCad status

Everything is captured under `hardware/` and wired into `sym-lib-table` / `fp-lib-table`:

| Ref | Symbol (`TEG:`) | Footprint (`TEG:`) | 3D model |
|-----|-----------------|--------------------|----------|
| U1 | `BQ25504RGTT` | `VQFN-16_L3.0-W3.0-P0.50-TL-EP` | OK |
| U2 | `MT3608` | `SOT-23-6_L2.9-W1.6-P0.95-LS2.8-BL` | OK |
| Q1 | `AO3400A` | `SOT-23-3_L2.9-W1.3-P1.90-LS2.4-BR` | OK |
| D1/D2 | `1N5819WS` | `SOD-323_L1.8-W1.3-LS2.5-RD` | OK |
| L1/L2 | `FTC252010S4R7MBCA` | `IND-SMD_L2.5-W2.0-VLS252012CX-150M` | OK |
| R | `0603WAF1002T5E` (10 k) / `0603WAF1003T5E` (100 k) | `R0603` | OK |
| C | `CL21A106KAYNNNE` (10 uF) | `C0805` | OK |
| C | `CL10A105KB8NNNC` (1 uF) / `CL10B104KA8NNNC` (100 nF) | `C0603` | OK |
| J1/J3 | `KF128-5.08-2P` | `CONN-TH_P5.08_KF128-5.08-2P` | OK |
| J2 | `PZ254V-11-04P_C2691448` | `HDR-TH_4P-P2.54-V-M` | OK |

## Verification status

- [x] U1 BQ25504RGTT — symbol + footprint + 3D fetched
- [x] All 30 draft parts: symbol + footprint + 3D captured into project libraries
- [x] Draft netlist generated ([scripts/gen_schematic.py](scripts/gen_schematic.py)) — 30 parts, 81 labeled pins
- [x] **ERC: 1 warning** (`VBAT_OK` isolated label — intentional, reserved for status LED/test point)
- [x] **Board DRC: 0 violations** (59 unconnected items = unrouted ratsnest, expected)
- [ ] BQ25504 + MT3608 programming resistor values computed from datasheets
      (datasheet downloaded; worked-example values extracted — see PLAN.md §6)
- [ ] Storage element selected and sized
- [ ] Route copper + GND pour, re-run DRC
- [ ] WRL 3D-model units/scale visually checked in KiCad
