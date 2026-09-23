"""Pure schedule math: what state should a device be in, and when does that change.

All functions take an aware local datetime, so they are easy to test and have no
Home Assistant dependencies.
"""

from __future__ import annotations

from datetime import datetime, time, timedelta

from .const import (
    MODE_ALWAYS_ON,
    MODE_INTERVAL,
    MODE_MANUAL,
    MODE_OFF,
    MODE_TIME_WINDOW,
)
from .models import DeviceSchedule

DAY_SECONDS = 86400


def parse_time(value: str) -> time:
    """Parse HH:MM or HH:MM:SS."""
    return time.fromisoformat(value)


def _at(day_start: datetime, value: str) -> datetime:
    """Return the given wall-clock time on the day that starts at day_start."""
    t = parse_time(value)
    return day_start.replace(hour=t.hour, minute=t.minute, second=t.second)


def _day_start(now: datetime) -> datetime:
    return now.replace(hour=0, minute=0, second=0, microsecond=0)


def desired_state(schedule: DeviceSchedule, now: datetime) -> bool | None:
    """Return True/False for the desired device state, or None when unmanaged."""
    if schedule.mode == MODE_MANUAL:
        return None
    if schedule.mode == MODE_OFF:
        return False
    if schedule.mode == MODE_ALWAYS_ON:
        return True
    if schedule.mode == MODE_TIME_WINDOW:
        start = _at(_day_start(now), schedule.on_time)
        end = _at(_day_start(now), schedule.off_time)
        if start == end:
            return False
        if start < end:
            return start <= now < end
        # Window crosses midnight
        return now >= start or now < end
    if schedule.mode == MODE_INTERVAL:
        every = schedule.interval_every
        on = min(schedule.interval_on, every)
        if every <= 0 or on <= 0:
            return False
        elapsed = (now - _day_start(now)).total_seconds()
        return elapsed % every < on
    return None


def next_transition(schedule: DeviceSchedule, now: datetime) -> datetime | None:
    """Return the next moment desired_state may change, or None if it never does."""
    day_start = _day_start(now)
    if schedule.mode == MODE_TIME_WINDOW:
        if schedule.on_time == schedule.off_time:
            return None
        candidates = [
            _at(day_start + timedelta(days=offset), value)
            for offset in (0, 1)
            for value in (schedule.on_time, schedule.off_time)
        ]
        return min(c for c in candidates if c > now)
    if schedule.mode == MODE_INTERVAL:
        every = schedule.interval_every
        on = min(schedule.interval_on, every)
        if every <= 0 or on <= 0 or on == every:
            return None
        elapsed = (now - day_start).total_seconds()
        cycle_start = (elapsed // every) * every
        boundary = cycle_start + on if elapsed - cycle_start < on else cycle_start + every
        # The pattern re-anchors at midnight.
        boundary = min(boundary, DAY_SECONDS)
        return day_start + timedelta(seconds=boundary)
    return None


def _fmt_duration(seconds: int) -> str:
    hours, rem = divmod(seconds, 3600)
    minutes, secs = divmod(rem, 60)
    parts = []
    if hours:
        parts.append(f"{hours} h")
    if minutes:
        parts.append(f"{minutes} min")
    if secs or not parts:
        parts.append(f"{secs} s")
    return " ".join(parts)


def describe(schedule: DeviceSchedule) -> str:
    """Return a short human-readable description of a schedule."""
    if schedule.mode == MODE_MANUAL:
        return "Not managed"
    if schedule.mode == MODE_OFF:
        return "Off"
    if schedule.mode == MODE_ALWAYS_ON:
        return "Always on"
    if schedule.mode == MODE_TIME_WINDOW:
        return f"{schedule.on_time[:5]}–{schedule.off_time[:5]}"
    if schedule.mode == MODE_INTERVAL:
        return (
            f"{_fmt_duration(schedule.interval_on)} every {_fmt_duration(schedule.interval_every)}"
        )
    return schedule.mode
