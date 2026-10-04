"""Tests for EC unit conversion."""

from __future__ import annotations

import pytest

from grow_planner.core.const import EC_UNITS
from grow_planner.core.models import out_of_range
from grow_planner.core.units import detect_unit, from_canonical, to_canonical


@pytest.mark.parametrize("unit", EC_UNITS)
def test_round_trip(unit: str) -> None:
    shown = from_canonical(1.4, unit)
    # Entering what the display shows converts back to (about) the same mS/cm.
    assert to_canonical(shown, unit) == pytest.approx(1.4, abs=0.05)
    assert from_canonical(to_canonical(shown, unit), unit) == shown


@pytest.mark.parametrize(
    ("unit", "shown"),
    [("mS/cm", 1.4), ("µS/cm", 1400), ("CF", 14.0), ("ppm 500", 700), ("ppm 700", 980)],
)
def test_from_canonical(unit: str, shown: float) -> None:
    assert from_canonical(1.4, unit) == shown


def test_ppm500_reading_is_checked_in_ms_cm() -> None:
    reading = to_canonical(700, "ppm 500")
    assert reading == pytest.approx(1.4)
    assert out_of_range(reading, 1.2, 2.0) is False
    assert out_of_range(to_canonical(500, "ppm 500"), 1.2, 2.0) is True


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("mS/cm", "mS/cm"),
        ("µS/cm", "µS/cm"),
        ("uS/cm", "µS/cm"),
        ("ppm 500", "ppm 500"),
        ("ppm700", "ppm 700"),
        ("CF", "CF"),
        ("ppm", None),
        (None, None),
        ("V", None),
    ],
)
def test_detect_unit(raw: str | None, expected: str | None) -> None:
    assert detect_unit(raw) == expected
