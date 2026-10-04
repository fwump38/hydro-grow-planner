"""EC unit conversion. Everything is stored and compared in mS/cm."""

from __future__ import annotations

import re

from .const import EC_CF, EC_MS_CM, EC_PPM_500, EC_PPM_700, EC_UNITS, EC_US_CM

# value in unit = mS/cm * factor
_FACTOR: dict[str, float] = {
    EC_MS_CM: 1.0,
    EC_US_CM: 1000.0,
    EC_CF: 10.0,
    EC_PPM_500: 500.0,
    EC_PPM_700: 700.0,
}
_DECIMALS: dict[str, int] = {EC_MS_CM: 2, EC_US_CM: 0, EC_CF: 1, EC_PPM_500: 0, EC_PPM_700: 0}
_STEP: dict[str, float] = {EC_MS_CM: 0.01, EC_US_CM: 10, EC_CF: 0.1, EC_PPM_500: 10, EC_PPM_700: 10}


def to_canonical(value: float, unit: str) -> float:
    """Convert a reading in `unit` to mS/cm."""
    return value / _FACTOR[unit]


def from_canonical(value: float, unit: str) -> float:
    """Convert mS/cm to `unit`, rounded the way that unit is usually shown."""
    return round(value * _FACTOR[unit], _DECIMALS[unit])


def step(unit: str) -> float:
    """Return a sensible input step for a unit."""
    return _STEP[unit]


def detect_unit(unit_of_measurement: str | None) -> str | None:
    """Map a sensor's unit_of_measurement to an EC unit.

    A bare "ppm" is ambiguous (500 vs 700 scale), so it returns None and the user
    has to choose.
    """
    if not unit_of_measurement:
        return None
    text = unit_of_measurement.strip().lower().replace("μ", "µ")
    if text in ("ms/cm", "ms cm-1", "ms·cm⁻¹"):
        return EC_MS_CM
    if text in ("µs/cm", "us/cm", "µs cm-1"):
        return EC_US_CM
    if text == "cf":
        return EC_CF
    match = re.fullmatch(r"ppm\s*(500|700)", text)
    if match:
        return EC_PPM_500 if match.group(1) == "500" else EC_PPM_700
    return None


def is_valid_unit(unit: str) -> bool:
    """Return whether `unit` is a supported EC unit."""
    return unit in EC_UNITS
