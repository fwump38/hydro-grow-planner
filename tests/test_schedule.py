"""Tests for the pure schedule math."""

from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from custom_components.hydro_grow_planner.models import DeviceSchedule
from custom_components.hydro_grow_planner.schedule import (
    describe,
    desired_state,
    next_transition,
)

TZ = ZoneInfo("America/Denver")


def at(hour: int, minute: int = 0, second: int = 0, day: int = 1) -> datetime:
    return datetime(2026, 9, day, hour, minute, second, tzinfo=TZ)


WINDOW = DeviceSchedule(mode="time_window", on_time="06:00:00", off_time="21:00:00")
OVERNIGHT = DeviceSchedule(mode="time_window", on_time="22:00:00", off_time="04:00:00")
PUMP = DeviceSchedule(mode="interval", interval_on=900, interval_every=10800)


@pytest.mark.parametrize(
    ("schedule", "now", "expected"),
    [
        (DeviceSchedule(mode="manual"), at(12), None),
        (DeviceSchedule(mode="off"), at(12), False),
        (DeviceSchedule(mode="always_on"), at(12), True),
        (WINDOW, at(5, 59), False),
        (WINDOW, at(6), True),
        (WINDOW, at(20, 59, 59), True),
        (WINDOW, at(21), False),
        (OVERNIGHT, at(23), True),
        (OVERNIGHT, at(3, 59), True),
        (OVERNIGHT, at(4), False),
        (OVERNIGHT, at(12), False),
        (PUMP, at(0), True),
        (PUMP, at(0, 14, 59), True),
        (PUMP, at(0, 15), False),
        (PUMP, at(3), True),
        (PUMP, at(2, 59), False),
    ],
)
def test_desired_state(schedule: DeviceSchedule, now: datetime, expected: bool | None) -> None:
    assert desired_state(schedule, now) is expected


@pytest.mark.parametrize(
    ("schedule", "now", "expected"),
    [
        (WINDOW, at(5), at(6)),
        (WINDOW, at(6), at(21)),
        (WINDOW, at(22), at(6, day=2)),
        (OVERNIGHT, at(23), at(4, day=2)),
        (OVERNIGHT, at(1), at(4)),
        (PUMP, at(0), at(0, 15)),
        (PUMP, at(0, 15), at(3)),
        (PUMP, at(22, 30), at(0, day=2)),
        (DeviceSchedule(mode="always_on"), at(12), None),
    ],
)
def test_next_transition(
    schedule: DeviceSchedule, now: datetime, expected: datetime | None
) -> None:
    assert next_transition(schedule, now) == expected


def test_describe() -> None:
    assert describe(WINDOW) == "06:00–21:00"
    assert describe(PUMP) == "15 min every 3 h"
    assert describe(DeviceSchedule()) == "Not managed"
