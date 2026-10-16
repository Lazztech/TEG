"""Source-of-truth parameters for the printed TEG wedge enclosure.

This module is the single place to edit dimensions. ``wedge.py`` reads a
``WedgeParams`` instance (defaults here, or overridden from a JSON file / CLI)
and turns it into a solid, so a change to a number here is the whole diff.

Values are millimetres, newtons, megapascals and degrees. Every default that
comes from a datasheet or a requirement cites it inline; estimates are marked
``(estimate)`` exactly as in REQUIREMENTS.md.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class WedgeParams:
    """Geometry + design inputs for the wedge enclosure.

    Coordinate system (see ``wedge.py``):
      * X = width  (left/right)
      * Y = depth  (0 at the hot face, ``depth`` at the cold-side back face)
      * Z = height (0 at the bed/base, ``front_height`` at the top of the hot face)
    """

    # --- printer / envelope -------------------------------------------------
    # P1: Bambu Lab A1 mini build volume.
    bed_x: float = 180.0
    bed_y: float = 180.0
    bed_z: float = 180.0

    # --- wedge envelope -----------------------------------------------------
    width: float = 150.0          # across the hot face
    front_height: float = 150.0   # hot-face height (against the fireplace)
    back_height: float = 100.0    # cold-side height after the taper
    depth: float = 55.0           # hot face -> back face
    wall: float = 5.0             # printed wall thickness (holds 3 mm magnet pockets
                                  # with a floor, + a rebate for the metal plate)
    fillet: float = 6.0           # outer vertical edge rounding (estimate)
    base_thickness: float = 3.0   # floor of the open bottom

    # --- hot-side metal interface plate (NOT printed; T1/T5) ----------------
    # The metal plate spreads the fireplace heat and clamps the TEG stack. The
    # printed pocket is a rebate so the plastic never sits in the hot path (T2);
    # ``thermal_break_gap`` is the air gap between plate and printed pocket.
    plate_w: float = 96.0
    plate_h: float = 96.0
    plate_pocket_depth: float = 2.0
    thermal_break_gap: float = 0.8

    # --- TEG stack (Coherent TG12-4-01LS datasheet) -------------------------
    teg_len: float = 34.01        # Base ceramic length
    teg_wid: float = 30.0         # Base ceramic width
    teg_thk: float = 3.33         # Height
    teg_count: int = 2            # 2 modules meet E1 (~3.2 W)
    teg_stack_gap: float = 0.5    # locating clearance around the modules
    clamp_pressure_mpa: float = 1.4   # REQUIREMENTS.md section 8 (200 psi)

    # --- clamping hardware (REQUIREMENTS.md section 8) ----------------------
    clamp_screw_dia: float = 4.3      # M4 clearance
    clamp_boss_dia: float = 12.0
    clamp_boss_len: float = 12.0      # into the cavity from the inner front wall
    clamp_screw_count: int = 4

    # --- magnets + mechanical retention (T4/S2) -----------------------------
    magnet_dia: float = 10.0          # SmCo disc (estimate; grade TBD, see T4)
    magnet_thk: float = 3.0
    magnet_clearance: float = 0.15    # per side, for glue/adhesive
    magnet_inset: float = 14.0        # edge distance to magnet centre
    retention_screw_dia: float = 3.4  # M3 clearance, S2 mechanical backup
    retention_inset: float = 14.0

    # --- fan + heatsink on the cold side (P5) -------------------------------
    fan_size: float = 80.0            # Noctua NF-A8 (80 mm)
    fan_hole_dia: float = 76.0        # through opening
    fan_mount_pitch: float = 71.5     # NF-A8 mounting-hole pitch
    fan_mount_dia: float = 4.4        # M4 fan screw clearance

    # --- derived / cosmetic ------------------------------------------------
    export_stem: str = "wedge_enclosure"

    # ------------------------------------------------------------------ utils
    def teg_array_size(self) -> tuple[float, float]:
        """Bounding footprint (width, height) of the vertical TEG stack."""
        if self.teg_count <= 1:
            return (self.teg_len, self.teg_wid)
        return (self.teg_len, self.teg_count * self.teg_wid)
    
    def clamp_force_n(self) -> float:
        """Total normal force the clamp must apply (F = P * A * count)."""
        area_mm2 = self.teg_len * self.teg_wid * self.teg_count
        return self.clamp_pressure_mpa * area_mm2

    def clamp_force_per_screw_n(self) -> float:
        return self.clamp_force_n() / self.clamp_screw_count

    def bounding_box(self) -> tuple[float, float, float]:
        """Overall envelope (X, Y, Z) of the finished part."""
        return (self.width, self.depth, self.front_height)

    def fits_bed(self) -> tuple[bool, str]:
        bx, by, bz = self.bounding_box()
        ok = bx <= self.bed_x and by <= self.bed_y and bz <= self.bed_z
        msg = (f"{bx:g} x {by:g} x {bz:g} mm vs bed "
               f"{self.bed_x:g} x {self.bed_y:g} x {self.bed_z:g} mm")
        return ok, msg

    def validate(self) -> None:
        if self.front_height <= self.back_height:
            raise ValueError("front_height must exceed back_height for a wedge")
        if self.wall <= 0 or self.depth <= 2 * self.wall:
            raise ValueError("depth must be greater than two walls")
        if self.plate_w > self.width or self.plate_h > self.front_height:
            raise ValueError("interface plate larger than the hot face")

    # ---------------------------------------------------------------- io
    def to_json(self) -> str:
        return json.dumps(asdict(self), indent=2, sort_keys=True)

    @classmethod
    def from_json_file(cls, path: str | Path) -> "WedgeParams":
        data = json.loads(Path(path).read_text())
        allowed = {f for f in cls.__dataclass_fields__}
        unknown = set(data) - allowed
        if unknown:
            raise ValueError(f"unknown parameter(s): {sorted(unknown)}")
        return cls(**data)


DEFAULTS = WedgeParams()
