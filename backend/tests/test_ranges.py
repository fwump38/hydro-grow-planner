"""Tests for debounced range alerts and progress math."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

import pytest

from grow_planner.core.models import Plan, Stage
from grow_planner.core.progress import (
    day_number,
    days_remaining,
    expected_end,
    grow_start_for,
    progress_percent,
)
from grow_planner.core.ranges import EVENT_BACK, EVENT_OUT, RangeAlert, convert_temperature

T0 = datetime(2026, 9, 1, 12, 0, tzinfo=ZoneInfo("America/Denver"))


def minutes(n: int) -> datetime:
    return T0 + timedelta(minutes=n)


def test_out_of_range_needs_to_last_the_debounce() -> None:
    alert = RangeAlert({})
    assert alert.update(minutes(0), 7.5, 5.8, 6.5) is None  # starts the timer
    assert alert.update(minutes(9), 7.5, 5.8, 6.5) is None
    assert alert.update(minutes(10), 7.5, 5.8, 6.5) == EVENT_OUT
    assert alert.update(minutes(30), 7.5, 5.8, 6.5) is None  # only once


def test_flapping_reading_never_alerts() -> None:
    alert = RangeAlert({})
    for i, value in enumerate([7.5, 6.0, 7.5, 6.0, 7.5, 6.0]):
        assert alert.update(minutes(i * 5), value, 5.8, 6.5) is None


def test_back_in_range_after_out() -> None:
    alert = RangeAlert({})
    alert.update(minutes(0), 7.5, 5.8, 6.5)
    assert alert.update(minutes(10), 7.5, 5.8, 6.5) == EVENT_OUT
    assert alert.update(minutes(11), 6.0, 5.8, 6.5) is None
    assert alert.update(minutes(21), 6.0, 5.8, 6.5) == EVENT_BACK
    assert alert.update(minutes(40), 6.0, 5.8, 6.5) is None


def test_in_range_never_alerts_and_unknown_clears_pending() -> None:
    alert = RangeAlert({})
    assert alert.update(minutes(0), 6.0, 5.8, 6.5) is None
    assert alert.update(minutes(60), 6.0, 5.8, 6.5) is None
    alert.update(minutes(61), 9.0, 5.8, 6.5)
    assert alert.update(minutes(65), None, 5.8, 6.5) is None  # sensor dropped out
    assert alert.update(minutes(70), 9.0, 5.8, 6.5) is None  # timer restarted


def test_state_survives_a_restart() -> None:
    state: dict = {}
    RangeAlert(state).update(minutes(0), 9.0, 5.8, 6.5)
    assert RangeAlert(state).update(minutes(10), 9.0, 5.8, 6.5) == EVENT_OUT


@pytest.mark.parametrize(
    ("value", "source", "target", "expected"),
    [(20, "°C", "°F", 68), (68, "°F", "°C", 20), (70, "°F", "°F", 70), (5, "K", "°F", 5)],
)
def test_convert_temperature(value: float, source: str, target: str, expected: float) -> None:
    assert convert_temperature(value, source, target) == pytest.approx(expected)


def plan_of(*days: int) -> Plan:
    stages = tuple(
        Stage(id=str(i), name=f"S{i}", stage_type="other", days=d) for i, d in enumerate(days)
    )
    return Plan(id="p", name="P", stages=stages)


def test_progress_math() -> None:
    started = date(2026, 9, 1)
    assert day_number(started, date(2026, 9, 1)) == 1
    assert day_number(started, date(2026, 9, 8)) == 8
    assert days_remaining(7, 3) == 5
    assert days_remaining(7, 12) == 0
    assert progress_percent(10, 1) == 0
    assert progress_percent(10, 6) == 50
    assert progress_percent(10, 40) == 100


def test_expected_end_and_backdated_grow_start() -> None:
    plan = plan_of(7, 7, 21)
    assert expected_end(plan, 1, date(2026, 9, 10)) == date(2026, 10, 8)
    # Starting at Vegetative on 2026-09-15 implies the grow began 14 days earlier.
    assert grow_start_for(plan, 2, date(2026, 9, 15)) == date(2026, 9, 1)
    assert grow_start_for(plan, 0, date(2026, 9, 15)) == date(2026, 9, 15)
