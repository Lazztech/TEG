# SolidCraft contender — the wedge enclosure as a command script

`wedge.json` is the whole model: a list of commands (the same ones SolidCraft's
UI runs) that build the enclosure and its features. It is plain text, so it is
reviewable and diffable like the two Python contenders.

- **Tool:** [SolidCraft](https://github.com/bherbruck/solidcraft) — pure-Rust
  parametric CAD; headless CLI + MCP server.
- **Pin:** v0.13.1 (linux-x86_64), downloaded by `scripts/cad-solidcraft.sh`
  into `.solidcraft/` (gitignored).
- **Exports:** `exports/wedge_enclosure.{step,stl,png}` and the native
  `exports/wedge_enclosure.solidcraft` (a zip container — the `.json` script and
  the STEP/STL are the text/binary artifacts to keep in git).

```bash
scripts/cad-solidcraft.sh              # build -> STEP + STL + iso PNG
scripts/cad-solidcraft.sh --no-export  # measure only
```

## Conventions / gotchas found while authoring

- Coordinate system matches `cad/parameters.py`: X = width, Y = depth (0 at the
  hot face), Z = height (0 at the bed).
- **`XZ` sketch plane:** local v-axis points **−Z**, so a feature at height Z is
  drawn at `[x, -Z]`. `XY` keeps `v = +Z`.
- `solid.extrude direction: symmetric` extrudes `distance` total, split evenly
  about the sketch plane (used for the 150 mm width).
- `solid.shell` with the bottom face (`[0, 27.5, 0]`) as the opening and
  `direction: inside` hollows the part, open at the bed, exactly like the
  build123d `offset(openings=...)`.
- Feature order mirrors `cad/wedge.py`: profile → shell → plate rebate → magnet
  pockets → retention holes → fan bore + mounts → clamp bosses (join) → clamp
  holes.
