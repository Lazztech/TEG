# Requirements — Fireplace TEG Harvester

**Status:** draft, agreed 2026-10-10. Numbers marked *(estimate)* are not yet verified against a
TEG module datasheet — see [Open items](#open-items).

This document covers the **whole device**, not just the electronics. It supersedes the earlier
sub-watt concept, which is kept as a validated reference design in `hardware/`.

---

## 1. Purpose and concept

A thermoelectric harvester that sits on the metal face of a fireplace, uses the temperature
difference between that hot surface and the surrounding room air to generate electricity, and makes
it available as **standard USB power**.

```
   fireplace metal face (hot, clamped to ~120 C)
            |
        [ TEG array ]  2-3 modules
            |
   fan-forced heatsink (cold side, room air)   <-- 80-120 mm fan
            |
      [ power board ]  MPPT/buck -> 5 V
            |
      USB-A  +  USB-C  ->  small USB devices / battery bank
```

A printed **wedge enclosure** carries the assembly and holds it to the fireplace with magnets.

## 2. Electrical requirements

| ID | Requirement | Target |
|----|-------------|--------|
| E1 | Total output power | **~3–4 W** continuous at a strong temperature difference |
| E2 | Output voltage | **5 V** |
| E3 | Output ports | **1 × USB-A and 1 × USB-C**, sharing the available power |
| E4 | MPPT | Operate the array near its maximum power point |
| E5 | Indication | Built-in **voltmeter** so the operating point is visible |
| E6 | Cold start | Must start from a comparably weak temperature difference; no external power needed to begin |

**Reality note:** output is *shared* between the ports — 3–4 W total, so roughly 2 W per port when
both are loaded. It is not 3 W per port. Selection of the power electronics follows from this.
*(estimate)*

## 3. Physical and mechanical requirements

| ID | Requirement | Value |
|----|-------------|-------|
| P1 | Whole device fits the printer bed | **Bambu Lab A1 mini — 180 × 180 × 180 mm** |
| P2 | Shape | **Wedge**, so it presents a flat hot face to the fireplace and tapers back to the heatsink |
| P3 | Mounting | **Magnets** hold it to the metal fireplace face |
| P4 | Enclosure | 3D-printed, in a material rated for the temperatures involved (see T2) |
| P5 | Cooling | Fan-forced heatsink on the cold side; the fan is the only moving part |

Layout budget inside the 180 mm bed *(estimate)*: TEG array ~60 × 60 mm, heatsink ~80 × 80 mm,
power board ~80 × 60 mm, fan 80–120 mm. These stack vertically inside the wedge.

## 4. Thermal and safety requirements

These are **hard limits**, not targets. A fireplace's outer metal runs **100–400 °C**, and every
part of this device has a much lower limit. *(Limits marked ✔ are from datasheets.)*

| ID | Requirement | Limit |
|----|-------------|-------|
| T1 | Hot side is **clamped/regulated to ~120 °C** | Never rely on the fireplace to self-limit |
| T2 | Printed enclosure stays cool | PLA softens ~60 °C, PETG ~80 °C — keep the plastic off the hot path |
| T3 | Electronics stay cool | BQ25504-class junction 105 °C ✔, electrolytics 105 °C ✔, MT3608-class ~85 °C |
| T4 | **Magnets must survive** | Common NdFeB fails below ~80 °C — use **SmCo** and/or put magnets on the cold side |
| T5 | Thermal break between hot face and enclosure/electronics | Mandatory |
| S1 | No direct flame contact with any part | — |
| S2 | Device must not fall if a magnet weakens | Mechanical retention as well as magnets |
| S3 | Do not operate unattended | — |
| S4 | Water must not enter the electronics (if a wet heat source is used nearby) | — |

**Why T4 and S2 matter most:** the failure mode of a magnet-attached device on a hot surface is that
it heats, the magnets weaken, and the whole unit drops onto the hearth. SmCo magnets (good to
~300 °C) plus a mechanical backup are the mitigation.

## 5. Manufacturing requirements

| ID | Requirement |
|----|-------------|
| M1 | **One JLCPCB order** covers the PCB and its assembly |
| M2 | **As many parts as possible on the board**, pre-assembled by JLCPCB |
| M3 | Every board part must be a **JLCPCB catalogue part** (verified via their parts API) |
| M4 | Favour **SMD** over through-hole so JLCPCB's standard assembly line can place everything |
| M5 | Minimise the number of **unique extended parts** (JLCPCB charges ~$3 each) |
| M6 | **Total BOM ≤ $200**, assembled |

**Not achievable on the board:** the TEG modules, the fan and the heatsink. JLCPCB does not stock or
ship those, and they are mechanical/thermal parts. See the system BOM below.

## 6. Verification

| ID | Requirement | How |
|----|-------------|-----|
| V1 | Output power at temperature | Bench test into a load bank across a range of ΔT |
| V2 | MPPT operating point | Measure array voltage/current vs open-circuit voltage |
| V3 | Thermal safety | Thermocouples on hot face, enclosure and electronics with the fire lit |
| V4 | USB behaviour | Each port into a known load; a real phone and a real battery bank |
| V5 | Magnet retention | Heat-soak with an attached load; confirm no weakening or slippage |
| V6 | Electronics | `kicad-cli` ERC/DRC clean; gerbers and assembly files regenerated |

## 7. System BOM

The two tables below are the answer to "what does ordering actually get me?".

### 7a. Ordered from JLCPCB (PCB + assembly)

The board's own BOM is generated from `scripts/gen_schematic.py` and exported as
`build/fab/TEG-BOM-jlcpcb.csv` (`Comment,Designator,Footprint,LCSC Part #`). It currently covers the
**existing sub-watt reference board**; it will be regenerated when the new power path is designed.

| Item | Status |
|------|--------|
| PCB (5 pcs minimum order) | ✔ |
| SMD components (23 unique parts, all JLCPCB catalogue) | ✔ |
| Through-hole connectors (J1–J3) | Either JLCPCB's THT add-on, or hand-soldered |

**IMPORTANT:** there is currently **no USB-A or USB-C connector in the BOM** — the existing board
predates requirement E3. The new power board will add them.

### 7b. Bought separately (not available from JLCPCB)

| Item | Notes |
|------|-------|
| **TEG modules — 2–3** | Mid-range generator modules, hot-side rated ≥150 °C. **Source and datasheet still open** |
| **Fan — 1** | 80–120 mm, 5 V; the cold-side airflow |
| **Heatsink — 1** | Sized for ~40–80 W of heat rejection |
| Hot-side metal interface plate | Spreads and clamps the hot face; part of T1/T5 |
| **SmCo magnets** | High-temperature grade, per T4 |
| Fasteners | Mechanical retention, per S2 |
| Thermal interface material | Between modules, plate and heatsink |
| Voltmeter | If not integrated on the board |
| Enclosure | Printed in-house; see P4 |

## Open items

1. **TEG module datasheet — the gating unknown.** Module output at ΔT ≈ 70 °C, hot-side maximum
   temperature, Vmp/Imp. Sets the module count and array topology, and therefore the converter
   design and whether E1 is met.
2. **USB role** — is the target charging a battery bank, powering USB loads, or both? This decides
   whether USB-C **PD** negotiation is needed, or whether basic CC resistors suffice (E3).
3. **Fireplace surface temperature** — how hot, and is the device left mounted while burning?
   Decides the hot-side clamp design and the magnet grade (T1, T4).
4. **Whether the existing sub-watt board is discarded or kept** as a low-power variant.
