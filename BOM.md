# Bill of Materials — TEG Thermal Harvester

**Project:** Thermal Energy Harvesting Prototype (TEG power-conditioning board)
**Target assembly:** **JLCPCB — made and assembled** (SMT + THT)
**Revision:** Draft D — 2026-10-10
**Status:** Every part below is **verified present in the JLCPCB catalogue** via
[scripts/jlc_lookup.py](scripts/jlc_lookup.py). Draft netlist = 33 parts / 86 labelled pins.
**Storage decided: electrolytic buffer, 100 % JLCPCB-assembled.** ERC clean apart from 3
cosmetic warnings; board DRC clean apart from 1 cosmetic silkscreen warning. Remaining work:
**routing**. See [PLAN.md](./PLAN.md).

> **How parts were verified.** `jlc-client`'s *search* goes through a public index that is
> currently degraded (it returns high-stock parts regardless of query). This BOM was therefore
> built with `scripts/jlc_lookup.py`, which queries **JLCPCB's own parts API** and reports the
> LCSC id, library type (`base` = no setup fee / `expand` = extended) and stock. Every id below
> was read back from that API. Re-check stock before ordering — it drifts.

---

## ✅ Storage decision — electrolytic buffer only (100 % JLCPCB)

**Chosen: option D.** JLCPCB stocks **no supercapacitors and no batteries** (verified against
their own API — `supercapacitor`, `EDLC`, `5.5V 1F`, `0.1F 5.5V` all return 0 results), so those
cannot be machine-assembled. Option D keeps the board **100 % JLCPCB-assembled** by using a
**1000 µF 6.3 V SMD electrolytic** (`C970711`) as the storage/buffer element.

**What this means, honestly:**

- The BQ25504 needs *some* storage on VBAT — the datasheet's own reference shows ">100 µF" — and
  1000 µF satisfies that and holds the rail steady.
- But it stores only **≈5 mJ**, versus ≈1.2 J for a supercap. So **the fan cannot run from
  storage**: it turns only while the TEG array is supplying enough power directly (i.e. at high ΔT).
- That is arguably the *most informative* configuration for a first prototype — you will see
  exactly when the harvest can drive the fan — but it does mean "fan runs for a few seconds from
  storage" is **not** a capability of this build.
- `VBAT_OK` is therefore left unconnected (no-connect marker). Wiring it to gate the MT3608 `EN`
  is the natural upgrade if a real store is added later.
- ⚠️ **The electrolytic is polarised**: pin 1 = +. **Verify against the footprint silkscreen
  before assembly.**

Cycling it to a real energy store later is a one-part change (see the tradeoff table in
[PLAN.md](PLAN.md) §6).

## Functional blocks

```
 TEG array (2 x Marlow TG12-4-01LS, series)
        |
   J1 --+-- TEG input        D1 = reverse-polarity clamp (parallel, NOT series)
        |
        +--> U1 BQ25504RGTT   (boost charger + built-in MPPT, cold start ~330 mV)
        |        L1 22uH VIN-DC<->LBST, C1 input bulk
        |        MPPT: R13/R14 (10M/10M -> ~50% of Voc) + C3 (CREF 10nF)
        |        thresholds: R1-R4 (OV/UV), R15/R7/R6 (OK), R5 (OT_PROG -> GND, 65C)
        v
   VBAT / VSTOR --> STORAGE (see decision above)
        |
   U2 MT3608 (boost -> 5 V)  L2 22uH, D2 catch diode, R8/R9 feedback, C8 (CBYP)
        |
      +5V --> J2 fan (Noctua NF-A8 4-pin; R11 Tach pull-up)
         +--> J3 test load (0.5 W) switched by Q1 (R10/R12 gate)
```

## MPPT — how it is implemented

Built into **U1 (BQ25504)**; no extra IC, no firmware. The chip periodically lets the harvester's
open-circuit voltage appear, samples a fraction onto a hold capacitor, then regulates its boost
input to that fraction.

- Sampling network: `R13`/`R14` divide VIN_DC to the `VOC_SAMP` pin; `C3` (`CREF` 10 nF, low
  leakage) holds the reference on `VREF_SAMP`.
- **MPP ratio = R13/(R13+R14) = ≈50 %** — matched-load MPP for a TEG. The datasheet's 78 %
  default targets *solar*; copying it would waste real power.
- R13+R14 = 20 MΩ matches the datasheet's recommended sum.

## BOM (all JLCPCB-verified)

| Ref | Qty | Value / Part | LCSC | Package | Lib | Stock | Notes |
|-----|-----|--------------|------|---------|-----|-------|-------|
| U1 | 1 | **BQ25504RGTT** | C157471 | VQFN-16 3x3 | expand | **7** ⚠ | Harvester + MPPT. **Low stock** — fallback `C2876746` (BQ25504RGTR, 21) is the same part |
| U2 | 1 | **MT3608** | C84817 | SOT-23-6 | expand | 129 k | Boost → 5 V |
| Q1 | 1 | **AO3400A** | C20917 | SOT-23 | **base** | 813 k | Test-load low-side switch |
| D1, D2 | 2 | **1N5819WS** | C191023 | SOD-323 | **base** | 4.7 M | Input clamp (D1) + MT3608 catch (D2) |
| L1, L2 | 2 | **22 µH** `SWPA4020S220MT` | C82401 | SMD 4x4 mm | expand | 6 k | Datasheet-recommended value; 1.05 A, shielded |
| R13, R14 | 2 | 10 MΩ | C114606 | 0603 1 % | expand | 857 k | MPPT divider (≈50 %) |
| C3, C8 | 2 | 10 nF | C1589 | 0603 X7R | expand | 1.7 M | `CREF` (MPPT hold) + `CBYP` |
| R1 | 1 | 5.90 MΩ | C2076902 | 0603 1 % | expand | 4 498 | VBAT_OV chain ROV1 |
| R2 | 1 | 4.02 MΩ | C137708 | 0603 1 % | expand | 9 069 | ROV2 |
| R3 | 1 | 5.60 MΩ | C23190 | 0603 1 % | expand | 11 977 | VBAT_UV chain RUV1 |
| R4, R15 | 2 | 4.42 MΩ | C166806 | 0603 1 % | expand | 57 777 | RUV2 + OK chain ROK1 |
| R7 | 1 | 4.22 MΩ | C166807 | 0603 1 % | expand | 3 753 | OK chain ROK2 |
| R6 | 1 | 1.43 MΩ | C166898 | 0603 1 % | expand | 775 | OK chain ROK3 |
| R5 | 1 | 0 Ω | C21189 | 0603 | **base** | 25 M | `OT_PROG` → GND = 65 °C cutoff |
| R8 | 1 | 73.2 kΩ | C2933257 | 0603 1 % | expand | 250 k | MT3608 FB top → **5.0 V** (0.6 V × (1 + 73.2 k/10 k)) |
| R9, R11 | 2 | 10 kΩ | C25804 | 0603 1 % | **base** | 26 M | MT3608 FB bottom + fan Tach pull-up |
| R10 | 1 | 1 kΩ | C21190 | 0603 1 % | **base** | 19 M | Q1 gate series |
| R12 | 1 | 100 kΩ | C25803 | 0603 1 % | **base** | 21 M | Q1 gate pull-down |
| C1, C4, C5, C6 | 4 | 10 µF | C15850 | 0805 X5R | **base** | 4.3 M | Input bulk / VSTOR / VBAT / +5 V |
| C7 | 1 | 1 µF | C15849 | 0603 X5R | **base** | 8.6 M | +5 V HF decoupling |
| J1, J3 | 2 | **KF128-5.08-2P** | C474952 | THT P=5.08 mm | expand | 33 k | TEG input + test-load output |
| J2 | 1 | **PZ254V-11-04P** | C2691448 | THT P=2.54 mm | expand | 933 k | Fan header (GND/+5V/Tach/PWM) |
| C2 | 1 | **1000 µF 6.3 V electrolytic** | C970711 | SMD D8×L10.2 mm | expand | 1 888 | Storage/buffer on VBAT (option D). **Polarised — check pin 1** |

### Threshold values (datasheet worked example, SLUSAH0G §9.2.1)

VBAT_OV 3.15 V · VBAT_UV 2.20 V · VBAT_OK 2.44 V · VBAT_OK_HYST 2.80 V

Conservative and datasheet-verified. Usable energy 3.15→2.2 V is limited (≈2–4 s of fan on
0.47 F); raising OV toward ~5.0 V roughly triples it but needs the equations recomputed
(TI's own equations are images in the PDF — hand-derivation is unreliable). Tracked in PLAN.md.

## Verification status

- [x] **All 31 machine-placed parts verified in the JLCPCB catalogue** (id, library type, stock)
- [x] Draft netlist generated ([scripts/gen_schematic.py](scripts/gen_schematic.py)) — 32 parts, 85 labelled pins
- [x] **Board DRC: 0 violations** (63 unconnected = unrouted ratsnest)
- [x] MT3608 feedback divider computed → 73.2 k / 10 k = 5.0 V
- [x] Storage decided (option D) and added to the netlist/board
- [ ] **Route copper + GND pour** ← the remaining work
- [x] Export Gerbers/drill + JLCPCB `BOM.csv` / `CPL.csv` — scripted as
  [scripts/fab_export.sh](scripts/fab_export.sh); see
  [docs/jlcpcb-fabrication.md](docs/jlcpcb-fabrication.md)
