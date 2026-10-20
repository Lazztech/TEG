"""Geometry tests for the printed wedge enclosure.

These are the model-level half of the CAD quality gate. ``ruff`` and ``mypy``
check the *code*; these tests build the solid and assert the things a print
depends on: one valid body, the envelope, wall thickness, and that each feature
(rebate, magnet pockets, retention holes, fan bore, clamp bosses) exists where
``cad/parameters.py`` says it should.

Run them with ``scripts/cad-test.sh`` (sets the headless GL library path that
OCCT needs). ``scripts/validate_cad.py`` separately checks the exported STL/STEP.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from build123d import GeomType, Shape, Vector

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "cad"))

from parameters import DEFAULTS, WedgeParams  # noqa: E402
from wedge import build_wedge  # noqa: E402

# Face radii are exact from the kernel; the tolerance only absorbs float noise
# and keeps radii 2.15/2.20 mm (clamp hole vs fan mount) from aliasing.
TOL = 0.01


@pytest.fixture(scope="module")
def part() -> Shape:
    return build_wedge(DEFAULTS)


def cylinders(part: Shape, radius: float, tol: float = TOL) -> list:
    """Cylindrical faces of ``part`` whose radius matches ``radius``."""
    found = []
    for face in part.faces():
        if face.geom_type != GeomType.CYLINDER:
            continue
        if abs(face.radius - radius) <= tol:
            found.append(face)
    return found


# --------------------------------------------------------------------------- #
# body + envelope
# --------------------------------------------------------------------------- #
def test_builds_one_valid_solid(part: Shape) -> None:
    assert len(part.solids()) == 1
    assert part.is_valid
    assert part.volume > 0


def test_envelope_matches_parameters_and_fits_the_a1_mini(part: Shape) -> None:
    size = part.bounding_box().size
    assert size.X == pytest.approx(DEFAULTS.width, abs=1e-6)
    assert size.Y == pytest.approx(DEFAULTS.depth, abs=1e-6)
    assert size.Z == pytest.approx(DEFAULTS.front_height, abs=1e-6)

    fits, message = DEFAULTS.fits_bed()
    assert fits, message


def test_volume_is_a_known_good_golden(part: Shape) -> None:
    # Golden value for the default parameters. A change here is a design change:
    # re-print and update the number deliberately, do not loosen the tolerance.
    assert part.volume / 1000.0 == pytest.approx(248.38, rel=0.005)


# --------------------------------------------------------------------------- #
# walls (P1/P2, and the plastic that keeps the heated face off the electronics)
# --------------------------------------------------------------------------- #
def test_wall_thickness_at_mid_depth(part: Shape) -> None:
    y = DEFAULTS.depth / 2
    top = (
        DEFAULTS.front_height
        + (DEFAULTS.back_height - DEFAULTS.front_height) * y / DEFAULTS.depth
    )
    mid = DEFAULTS.front_height / 2

    assert part.is_inside(Vector(0, y, top - DEFAULTS.wall / 2))
    assert not part.is_inside(Vector(0, y, top - DEFAULTS.wall * 1.5))

    assert part.is_inside(Vector(DEFAULTS.width / 2 - DEFAULTS.wall / 2, y, mid))
    assert not part.is_inside(Vector(DEFAULTS.width / 2 - DEFAULTS.wall * 1.5, y, mid))


# --------------------------------------------------------------------------- #
# hot face: metal plate rebate and the thermal break (T1/T2/T5)
# --------------------------------------------------------------------------- #
def test_hot_face_rebate_has_the_declared_floor(part: Shape) -> None:
    floor_area = DEFAULTS.plate_w * DEFAULTS.plate_h
    floors = [
        face
        for face in part.faces()
        if face.geom_type == GeomType.PLANE
        and abs(face.center().Y - DEFAULTS.plate_pocket_depth) < 1e-3
        and abs(face.area - floor_area) < 1.0
    ]
    assert len(floors) == 1

    # The rebate is a void; solid plastic sits behind its floor, outside the
    # metal plate's footprint.
    assert not part.is_inside(Vector(0, 1.0, DEFAULTS.front_height / 2))
    assert part.is_inside(
        Vector(0, DEFAULTS.plate_pocket_depth + 1.0, DEFAULTS.front_height / 2)
    )


# --------------------------------------------------------------------------- #
# magnets (T4) and retention screws (S2)
# --------------------------------------------------------------------------- #
def test_four_magnet_pockets_on_the_hot_face_rim(part: Shape) -> None:
    pocket_r = (DEFAULTS.magnet_dia + 2 * DEFAULTS.magnet_clearance) / 2
    pockets = cylinders(part, pocket_r)

    assert len(pockets) == 4
    rim = DEFAULTS.front_height / 2
    expected_z = sorted(
        [
            round(DEFAULTS.magnet_inset, 1),
            round(rim, 1),
            round(rim, 1),
            round(DEFAULTS.front_height - DEFAULTS.magnet_inset, 1),
        ]
    )
    assert sorted(round(face.center().Z, 1) for face in pockets) == expected_z
    for face in pockets:
        assert face.center().Y < DEFAULTS.magnet_thk + DEFAULTS.magnet_clearance


def test_magnet_pocket_keeps_a_floor(part: Shape) -> None:
    # Void inside the pocket, solid immediately behind it: the 3 mm disc must
    # not break through into the cavity.
    z = DEFAULTS.front_height - DEFAULTS.magnet_inset
    assert not part.is_inside(Vector(0, 1.0, z))
    assert part.is_inside(Vector(0, 4.0, z))


def test_retention_holes_are_present(part: Shape) -> None:
    holes = cylinders(part, DEFAULTS.retention_screw_dia / 2)
    assert len(holes) >= 4
    for face in holes:
        assert face.center().Y < DEFAULTS.wall + DEFAULTS.clamp_boss_len


# --------------------------------------------------------------------------- #
# cold side: fan (P5) and clamp bosses (§8)
# --------------------------------------------------------------------------- #
def test_fan_bore_and_mounting_holes(part: Shape) -> None:
    bores = cylinders(part, DEFAULTS.fan_hole_dia / 2)
    assert len(bores) == 1
    assert bores[0].center().Y > DEFAULTS.depth - 3 * DEFAULTS.wall

    mounts = cylinders(part, DEFAULTS.fan_mount_dia / 2)
    assert len(mounts) == 4
    expected_z = {
        round(DEFAULTS.back_height / 2 - DEFAULTS.fan_mount_pitch / 2, 1),
        round(DEFAULTS.back_height / 2 + DEFAULTS.fan_mount_pitch / 2, 1),
    }
    assert {round(face.center().Z, 1) for face in mounts} == expected_z


def test_clamp_bosses_and_clearance_holes(part: Shape) -> None:
    bosses = cylinders(part, DEFAULTS.clamp_boss_dia / 2)
    assert len(bosses) == DEFAULTS.clamp_screw_count

    holes = cylinders(part, DEFAULTS.clamp_screw_dia / 2)
    assert len(holes) == DEFAULTS.clamp_screw_count

    _, array_h = DEFAULTS.teg_array_size()
    offset = array_h / 2 + DEFAULTS.clamp_boss_dia / 2
    expected_z = {
        round(DEFAULTS.front_height / 2 - offset, 1),
        round(DEFAULTS.front_height / 2 + offset, 1),
    }
    assert {round(face.center().Z, 1) for face in bosses} == expected_z


# --------------------------------------------------------------------------- #
# parameter guards and the §8 clamp load
# --------------------------------------------------------------------------- #
def test_parameter_guards_reject_impossible_designs() -> None:
    with pytest.raises(ValueError):
        WedgeParams(front_height=90.0).validate()
    with pytest.raises(ValueError):
        WedgeParams(wall=0.0).validate()
    with pytest.raises(ValueError):
        WedgeParams(plate_w=200.0).validate()


def test_oversized_part_is_reported_off_bed() -> None:
    fits, message = WedgeParams(width=200.0).fits_bed()
    assert not fits
    assert "200" in message


def test_clamp_load_matches_requirements_section_8() -> None:
    assert DEFAULTS.clamp_force_n() == pytest.approx(2856.84, rel=1e-9)
    assert DEFAULTS.clamp_force_per_screw_n() == pytest.approx(714.21, rel=1e-4)
