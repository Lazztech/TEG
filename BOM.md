# Bill of Materials — TEG Thermal Harvester

**Project:** Thermal Energy Harvesting Prototype (TEG power-conditioning board)
**Target assembly:** JLCPCB SMT + THT
**Revision:** Draft B — 2026-10-09
**Status:** Storage = supercapacitor (decided). Draft netlist = 32 parts / 85 labeled pins;
ERC 1 intentional warning, board DRC 0 violations (copper unrouted). See [PLAN.md](./PLAN.md).

> Source of part data: `jlc-client` against the JLCPCB catalog / EasyEDA. Stock and
> `basic`/`extended` flags were read at the time of writing and will drift — re-verify
> before ordering. `TBD` = value fixed but the JLCPCB part number still to be selected.

---

## Functional blocks

```
 TEG array (2 x Marlow TG12-4-01LS, series)
        |
   J1 --+-- TEG input        D1 = reverse-polarity clamp (parallel, NOT series)
        |
        +--> U1 BQ25504RGTT   (boost charger + built-in MPPT, cold start ~330 mV)
        |        L1 22uH in VIN-DC<->LBST, C1 input bulk
        |        MPPT: R13/R14 (10M/10M -> ~50% of Voc) + C3 (CREF 10nF)
        |        thresholds: R1-R4 (OV/UV), R15/R7/R6 (OK), R5 (OT_PROG -> GND, 65C)
        v
   VBAT / VSTOR --> SC1 supercapacitor (0.22-0.47 F, 5.5 V)
        |
   U2 MT3608 (boost -> 5 V)  L2 22uH, D2 catch diode, R8/R9 feedback, C8 (CBYP)
        |
      +5V --> J2 fan (Noctua NF-A8 4-pin; R11 Tach pull-up)
         +--> J3 test load (0.5 W) switched by Q1 (R10/R12 gate)
```

## MPPT — how it is implemented

MPPT is **built into U1 (BQ25504)**: no separate MPPT IC and no firmware. The IC
periodically lets the harvester's open-circuit voltage (Voc) appear, samples a fraction
of it onto a hold capacitor, then regulates its boost input to that fraction.

- **Sampling network (required):** `R13`/`R14` divide VIN_DC down to the `VOC_SAMP` pin;
  `C3` (`CREF`, 10 nF low-leakage) holds the reference on `VREF_SAMP`.
- **MPP ratio = R13/(R13+R14).** The datasheet's worked example uses **78 %** because it
  targets *solar*. A TEG delivers maximum power near a **matched load, ≈50 % of Voc**, so
  this design uses **R13 = R14 = 10 MΩ → ≈50 %**. (Datasheet also recommends
  R13+R14 = 20 MΩ, which 10+10 satisfies.)
- The ratio is a **first estimate** — TEG MPP shifts with ΔT and module; the plan's
  measurement phase should confirm it (and it may be worth making R13/R14 selectable).

## BOM

| Ref | Qty | Value / Part | LCSC | Package | Basic? | Function | Notes |
|-----|-----|--------------|------|---------|--------|----------|-------|
| U1 | 1 | **BQ25504RGTT** | C157471 | VQFN-16 3x3 | ext | Boost charger + **built-in MPPT**, cold start ≈330 mV | Key part. Alt: BQ25504RGTR `C2876746` |
| U2 | 1 | **MT3608** | C84817 | SOT-23-6 | ext | Boost → regulated 5 V rail | Asynchronous — needs D2 |
| Q1 | 1 | **AO3400A** | C20917 | SOT-23 | **basic** | Low-side switch for the 0.5 W test load | |
| D1 | 1 | **1N5819WS** | C191023 | SOD-323 | **basic** | Reverse-polarity clamp across the TEG input | Parallel, not series (series drop kills cold start) |
| D2 | 1 | **1N5819WS** | C191023 | SOD-323 | **basic** | MT3608 catch diode | Same part as D1 — order qty 2 |
| L1 | 1 | 22 uH | **TBD** | 1008 (2.5x2.0 mm) | ext | BQ25504 boost inductor | **Datasheet-recommended value**; verify the chosen 22 uH part fits the 1008 land |
| L2 | 1 | 22 uH | **TBD** | 1008 | ext | MT3608 boost inductor | Same part as L1 — qty 2 |
| R13 | 1 | 10 MΩ | **TBD** | 0603 1 % | ext | MPPT sampling divider, top (ROC1) | Sets MPP ≈50 % with R14 |
| R14 | 1 | 10 MΩ | **TBD** | 0603 1 % | ext | MPPT sampling divider, bottom (ROC2) | |
| C3 | 1 | 10 nF | **C1589** | 0603 X7R | **basic** | `CREF` — MPPT hold cap, low leakage | `CL10B103KB8NNNC` |
| C8 | 1 | 10 nF | **C1589** | 0603 X7R | **basic** | `CBYP` — VSTOR/VSS bypass | |
| R1 | 1 | 5.90 MΩ | **TBD** | 0603 1 % | ext | VBAT_OV chain ROV1 | Datasheet worked example |
| R2 | 1 | 4.02 MΩ | **TBD** | 0603 1 % | ext | VBAT_OV chain ROV2 | |
| R3 | 1 | 5.60 MΩ | **TBD** | 0603 1 % | ext | VBAT_UV chain RUV1 | |
| R4 | 1 | 4.42 MΩ | **TBD** | 0603 1 % | ext | VBAT_UV chain RUV2 | |
| R15 | 1 | 4.42 MΩ | **TBD** | 0603 1 % | ext | OK chain ROK1 | |
| R7 | 1 | 4.22 MΩ | **TBD** | 0603 1 % | ext | OK chain ROK2 | |
| R6 | 1 | 1.43 MΩ | **TBD** | 0603 1 % | ext | OK chain ROK3 | |
| R5 | 1 | 0 Ω | **C21189** | 0603 | **basic** | `OT_PROG` → GND = 65 °C charge cutoff | Datasheet choice |
| R8, R9 | 2 | TBD | **TBD** | 0603 1 % | ext | MT3608 +5 V feedback divider (Vref 0.6 V) | Value TBD |
| R10 | 1 | 1 k | **TBD** | 0603 | ext | Q1 gate series resistor | Value provisional |
| R11 | 1 | 10 k | **C25804** | 0603 1 % | **basic** | Fan Tach pull-up to +5 V | |
| R12 | 1 | 100 k | **C25803** | 0603 1 % | **basic** | Q1 gate pull-down (load off by default) | |
| C1 | 1 | 10 µF | **C15850** | 0805 X5R | **basic** | TEG input bulk (CIN, ≥4.7 µF) | |
| C4 | 1 | 10 µF | **C15850** | 0805 X5R | **basic** | VSTOR bulk (CSTOR, ≥4.7 µF) | |
| C5 | 1 | 10 µF | **C15850** | 0805 X5R | **basic** | VBAT bulk | |
| C6 | 1 | 10 µF | **C15850** | 0805 X5R | **basic** | +5 V output bulk | |
| C7 | 1 | 1 µF | **C15849** | 0603 X5R | **basic** | +5 V HF decoupling | |
| J1 | 1 | **KF128-5.08-2P** | C474952 | THT P=5.08 mm | ext | TEG array input | Alt: DB142R-5.08-2P `C2898709` |
| J2 | 1 | **PZ254V-11-04P** | C2691448 | THT P=2.54 mm | ext | Fan header (GND/+5V/Tach/PWM) | Noctua 4-pin PWM |
| J3 | 1 | **KF128-5.08-2P** | C474952 | THT P=5.08 mm | ext | Test-load output | |
| **SC1** | 1 | **supercapacitor 0.22–0.47 F, 5.5 V** | **TBD** | THT/large SMD | — | Storage on VBAT | **Hand-solder** — JLCPCB does not stock/place supercaps. Choose low-leakage; measure it (leakage can exceed harvest current) |

### Threshold values (datasheet worked example, SLUSAH0G §9.2.1)

VBAT_OV 3.15 V · VBAT_UV 2.20 V · VBAT_OK 2.44 V · VBAT_OK_HYST 2.80 V

These are the datasheet's *verified* values, and 3.15 V OV is conservative for a 5.5 V cell
(good margin, less stress). It also leaves usable energy only between 3.15 V and ~2.2 V:
in 0.47 F that is ≈1.2 J ≈ **2–4 s of fan**. **Raising OV toward ~5.0 V would roughly
triple that** (≈4.4 J) but requires recomputing R1–R7 with TI's equations/design tool —
tracked as an open item in [PLAN.md](./PLAN.md). Conservative first, measured later.

## Not stocked / alternatives

| Candidate | Note |
|-----------|------|
| LTC3105 (C107818) | **Actually in catalog** (earlier "not found" was the category-filter bug). Ultra-low 225 mV input, but no MPPT — BQ25504 is the better fit |
| BQ25570 (C506250) | BQ25504 + integrated regulated output — possible simplification |
| LTC4041 / MAX38888 | Supercap backup chargers (not harvest front-ends) |
| Li-ion / LiFePO4 storage | Rejected for the prototype: fire/cold-plating risk in a thermal device. See [PLAN.md](./PLAN.md) §6 |

## Verification status

- [x] All 32 parts: symbol + footprint (+ 3D where available) captured into project libraries
- [x] Draft netlist generated ([scripts/gen_schematic.py](scripts/gen_schematic.py)) — 32 parts, 85 labeled pins
- [x] **ERC: 1 warning** (`VBAT_OK` isolated label — intentional, reserved for status LED/test point)
- [x] **Board DRC: 0 violations** (63 unconnected = unrouted ratsnest, expected)
- [ ] Select JLCPCB parts for the 8 high-ohm 1 % resistors + 22 uH inductor (all extended)
- [ ] Select the supercapacitor (low leakage) and add to the board
- [ ] Compute MT3608 feedback divider (R8/R9) for 5.0 V
- [ ] Decide voltage window (3.15 V conservative vs ~5.0 V wide) and recompute R1–R7
- [ ] Route copper + GND pour, re-run DRC
