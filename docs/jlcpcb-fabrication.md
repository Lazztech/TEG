# JLCPCB fabrication & ordering — end-to-end flow

**Status:** tooling in place (2026-10-14). The v2 ~3–4 W power board does not exist
yet, so this is proven against the sub-watt reference board; the same command applies
unchanged once `hardware/TEG.kicad_pcb` becomes the v2 board.

**Goal:** any agent can turn the KiCad board into a **review-ready JLCPCB package**
(Gerbers + drill + BOM + CPL), and the **order** — which spends money — is placed
only with explicit human approval.

---

## 1. What is automated vs. manual

| Step | Automated? | How |
|------|------------|-----|
| Part sourcing / stock | ✅ | `scripts/jlc_lookup.py` (JLCPCB's own parts API) |
| Gerbers + drill export | ✅ | `scripts/fab_export.sh` → `kicad-cli` |
| Pick-and-place (CPL) | ✅ | `scripts/fab_export.sh` → `kicad-cli` + `scripts/jlc_cpl.py` |
| JLCPCB BOM | ✅ | `scripts/fab_export.sh` → `scripts/jlc_bom.py` |
| Package for upload | ✅ | `scripts/fab_export.sh` → `build/fab/<BASE>-gerbers.zip` |
| **Placing the order** | ❌ manual | jlcpcb.com, behind the approval gate (§5) |

There is **no unattended ordering**. JLCPCB has an official ordering API
(see §5), but it is application-gated and not wired here; if access is granted it
can be added *behind the same approval gate*.

## 2. Prerequisites

- `kicad-cli` (KiCad 8+) on `PATH`, or set `KICAD_CLI=/path/to/kicad-cli`.
- `python3` (standard library only).

## 3. The one command

```bash
scripts/fab_export.sh                       # hardware/TEG.kicad_pcb -> build/fab/
scripts/fab_export.sh path/to/board.kicad_pcb out/dir   # another board/dir
scripts/fab_export.sh --tht                 # include through-hole parts in BOM+CPL
```

It runs: gerbers → Excellon drill → `pcb export pos` → CPL conversion → BOM
generation → zip, and prints the output paths. It never uploads or orders.

### Outputs (`build/fab/`)

| File | For |
|------|-----|
| `<BASE>-gerbers.zip` | JLCPCB **PCB** upload ("add gerber file"): Gerbers + drill + `.gbrjob` |
| `<BASE>-BOM-jlcpcb.csv` | JLCPCB **assembly** step — `Comment,Designator,Footprint,LCSC Part #` |
| `<BASE>-CPL-jlcpcb.csv` | JLCPCB **assembly** step — `Designator,Val,Package,Mid X,Mid Y,Rotation,Layer` |
| `<BASE>-pos.csv` | Raw KiCad position file (kept for reference) |

`build/` is gitignored; regenerate any time. Package/logic-only files are produced by
`scripts/jlc_bom.py` and `scripts/jlc_cpl.py`, which can be run standalone.

### SMT-only vs. through-hole

Default is **SMT-only assembly**: `kicad-cli ... --smd-only` drops through-hole parts
(e.g. the reference board's `J1`/`J2`/`J3` connectors) from the CPL, and the BOM is
restricted to the same designators so the two files agree. JLCPCB rejects a BOM that
lists a part missing from the CPL. If a build uses JLCPCB's THT add-on, pass `--tht`
so both files include the through-hole parts.

## 4. Verify before ordering (checklist)

- [ ] `scripts/validate.sh` — schematic ERC and board DRC are clean (cosmetic
      warnings excepted, see README).
- [ ] `<BASE>-BOM-jlcpcb.csv` — every row has an LCSC id; quantities/designators match
      the board.
- [ ] `<BASE>-CPL-jlcpcb.csv` — one row per placed part; **Layer** and **Rotation** look
      right in JLCPCB's assembly preview.
- [ ] **CPL rotations.** KiCad and JLCPCB disagree on the zero-rotation convention for
      some packages. Always confirm against JLCPCB's assembly viewer (or KiCad's
      Fabrication Toolkit) before paying — this is a classic source of misplacement.
- [ ] **Shared origin.** Gerbers and CPL must use the same coordinate origin or the
      parts land off the board. The board's aux/grid origin is `0,0`; if that changes,
      export both with a matching origin.
- [ ] Re-check part stock with `python3 scripts/jlc_lookup.py "<part>"` — stock drifts;
      the reference board's `U1` (BQ25504, `C157471`) has run low before.
- [ ] BOM total ≤ $200 (REQUIREMENTS M6).

## 5. Placing the order (approval-gated)

**Default path — manual, user-approved:**

1. Agent produces and reviews the package (§3–§4).
2. Agent asks the board to approve the order (cost, quantity, shipping).
3. On approval, the **user** uploads `build/fab/*.zip` and the BOM/CPL to
   <https://jlcpcb.com>, confirms the assembly preview, and pays.
4. Order confirmation is recorded back on the task.

**Never place an order unattended.** Spend and account actions stay behind the normal
Paperclip approval gate.

**Possible automation (needs access first).** JLCPCB runs an official **Open Platform
API** (`api.jlcpcb.com`) covering Gerber upload → price quote → create order, but
**access is application-gated** (partner review based on order history/company, not
self-serve). It is **not** in the Paperclip connections catalogue. If the user obtains
credentials, we can automate the upload + quote steps and keep **order creation** behind
the same approval gate. Until then, ordering is manual.

## 6. When the v2 board is ready

1. Replace `hardware/TEG.kicad_pcb` + `.kicad_sch` with the routed v2 board.
2. Run `scripts/validate.sh`, then `scripts/fab_export.sh`.
3. Work the §4 checklist, then the §5 approval flow.

The v2 board's USB-A/C connectors are SMD catalogue parts, so it should assemble with
the default SMT-only flow.

---

*Related: [README.md](../README.md) (fabrication outputs), [PLAN.md](../PLAN.md) §7,
[REQUIREMENTS.md](../REQUIREMENTS.md) §5 (M1–M6), [BOM.md](../BOM.md).*
