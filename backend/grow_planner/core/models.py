"""Data model for grow plans.

A plan is a plain JSON structure (stored in the app's state file):

    {
      "name": "Lettuce",
      "ph_min": 6.0, "ph_max": 7.0,        # optional
      "temp_min": 60, "temp_max": 65, "temp_unit": "°F",   # optional
      "humidity_min": 50, "humidity_max": 70,              # optional, %
      "notes": "",
      "harvest_style": "continuous",       # or "once" (the default)
      "stages": [
        {
          "id": "a1b2c3",
          "name": "Sprouting",
          "stage_type": "sprouting",
          "days": 7,
          "outcome": "",
          "ec_min": 0.3, "ec_max": 0.5,    # optional, mS/cm
          "schedules": {"<device id>": {"mode": "time_window", ...}},
          "tasks": [
            {"id": "...", "task_type": "reminder", "title": "...", "note": "...",
             "method": "", "days": [1], "every": 2, "until": null}
          ]
        }
      ]
    }

A task is due on each of its `days` (stage days, 1-based). With `every`, it is also a
recurring task: the first instance is due on its first day, and each completion
schedules the next one `every` days later. It repeats until the stage changes, or
until stage day `until` when set (see tasks.py).

Stage and task ids are stable, so reordering stages never loses track of the
stage a running grow is in.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
import uuid

from .const import HARVEST_CONTINUOUS, HARVEST_ONCE, MODE_MANUAL

# Plans saved before ranges existed stored one target; widen it into a range.
LEGACY_TARGET_MARGIN = 0.3


def new_id() -> str:
    """Return a short random id for stages and tasks."""
    return uuid.uuid4().hex[:8]


def _range(data: dict[str, Any], low: str, high: str, legacy: str) -> tuple[Any, Any]:
    """Return (min, max), converting a legacy single target."""
    if low in data or high in data:
        return data.get(low), data.get(high)
    target = data.get(legacy)
    if target is None:
        return None, None
    return round(target - LEGACY_TARGET_MARGIN, 2), round(target + LEGACY_TARGET_MARGIN, 2)


def format_range(low: float | None, high: float | None) -> str | None:
    """Return "6–7", "≥ 6", "≤ 7" or None."""
    if low is not None and high is not None:
        return f"{low:g}–{high:g}"
    if low is not None:
        return f"≥ {low:g}"
    if high is not None:
        return f"≤ {high:g}"
    return None


def out_of_range(value: float | None, low: float | None, high: float | None) -> bool | None:
    """Return whether value is outside [low, high]; None when unknown."""
    if value is None or (low is None and high is None):
        return None
    return (low is not None and value < low) or (high is not None and value > high)


@dataclass(frozen=True, slots=True)
class DeviceSchedule:
    """How one device behaves during a stage."""

    mode: str = MODE_MANUAL
    on_time: str = "06:00:00"
    off_time: str = "22:00:00"
    interval_on: int = 900  # seconds
    interval_every: int = 10800  # seconds

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> DeviceSchedule:
        """Build from stored data."""
        if not data:
            return cls()
        return cls(
            mode=data.get("mode", MODE_MANUAL),
            on_time=data.get("on_time", "06:00:00"),
            off_time=data.get("off_time", "22:00:00"),
            interval_on=int(data.get("interval_on", 900)),
            interval_every=int(data.get("interval_every", 10800)),
        )


@dataclass(frozen=True, slots=True)
class Task:
    """A task on one or more days of a stage."""

    id: str
    task_type: str
    title: str
    days: tuple[int, ...]
    every: int = 0
    until: int | None = None
    note: str = ""
    method: str = ""

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Task:
        """Build from stored data."""
        task_type = data.get("task_type", "reminder")
        # Tasks saved before recurrence existed had a single "day".
        days = data.get("days") or [data.get("day", 1)]
        return cls(
            id=data["id"],
            # "top_up" was renamed to match Elfsys' "refill" task.
            task_type="refill" if task_type == "top_up" else task_type,
            title=data.get("title", ""),
            days=tuple(sorted({int(d) for d in days})),
            every=int(data.get("every") or 0),
            until=int(data["until"]) if data.get("until") else None,
            note=data.get("note", ""),
            method=data.get("method", ""),
        )

    @property
    def first_day(self) -> int:
        """Return the first day the task happens."""
        return self.days[0]

    @property
    def recurring(self) -> bool:
        """Return whether completing the task schedules another instance."""
        return self.every > 0

    @property
    def fixed_days(self) -> list[int]:
        """Return the stage days of the non-recurring instances.

        For a recurring task only the first day is fixed; the rest follow from
        completions.
        """
        return [self.first_day] if self.recurring else list(self.days)

    @property
    def description(self) -> str:
        """Return the method and note as one text."""
        method = f"Method: {self.method}" if self.method else ""
        return "\n\n".join(part for part in (method, self.note) if part)


def describe_days(
    days: list[int] | tuple[int, ...], every: int = 0, until: int | None = None
) -> str:
    """Return e.g. "Day 3", "Days 1, 4, 7" or "Every 2 days from day 1 until day 13"."""
    listed = ", ".join(str(d) for d in days)
    if every > 0:
        text = f"Every {'day' if every == 1 else f'{every} days'} from day {days[0]}"
        if until:
            text += f" until day {until}"
        if len(days) > 1:
            text += (
                f" (also day{'s' if len(days) > 2 else ''} {', '.join(str(d) for d in days[1:])})"
            )
        return text
    return f"Day {listed}" if len(days) == 1 else f"Days {listed}"


@dataclass(frozen=True, slots=True)
class Stage:
    """One stage of a plan."""

    id: str
    name: str
    stage_type: str
    days: int
    outcome: str = ""
    ec_min: float | None = None
    ec_max: float | None = None
    schedules: dict[str, DeviceSchedule] = field(default_factory=dict)
    tasks: tuple[Task, ...] = ()

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Stage:
        """Build from stored data."""
        ec_min, ec_max = _range(data, "ec_min", "ec_max", "target_ec")
        return cls(
            id=data["id"],
            name=data["name"],
            stage_type=data.get("stage_type", "other"),
            days=int(data.get("days", 1)),
            outcome=data.get("outcome", ""),
            ec_min=ec_min,
            ec_max=ec_max,
            schedules={
                device_id: DeviceSchedule.from_dict(sched)
                for device_id, sched in data.get("schedules", {}).items()
            },
            tasks=tuple(
                sorted(
                    (Task.from_dict(t) for t in data.get("tasks", [])),
                    key=lambda t: t.first_day,
                )
            ),
        )

    def schedule_for(self, device_id: str) -> DeviceSchedule:
        """Return the schedule for a device; unlisted devices are left alone."""
        return self.schedules.get(device_id, DeviceSchedule())


@dataclass(frozen=True, slots=True)
class Plan:
    """A grow plan: an ordered list of stages."""

    id: str
    name: str
    stages: tuple[Stage, ...]
    ph_min: float | None = None
    ph_max: float | None = None
    # Room temperature range, in temp_unit ("°C" or "°F").
    temp_min: float | None = None
    temp_max: float | None = None
    temp_unit: str = "°C"
    # Relative humidity range, in %.
    humidity_min: float | None = None
    humidity_max: float | None = None
    notes: str = ""
    # "once": harvest everything and start over. "continuous": keep the plants growing
    # and harvest a little at a time (cut-and-come-again, picking ripe fruit).
    harvest_style: str = HARVEST_ONCE

    @classmethod
    def from_dict(cls, plan_id: str, data: dict[str, Any]) -> Plan:
        """Build from subentry data."""
        ph_min, ph_max = _range(data, "ph_min", "ph_max", "target_ph")
        return cls(
            id=plan_id,
            name=data.get("name", ""),
            stages=tuple(Stage.from_dict(s) for s in data.get("stages", [])),
            ph_min=ph_min,
            ph_max=ph_max,
            temp_min=data.get("temp_min"),
            temp_max=data.get("temp_max"),
            temp_unit=data.get("temp_unit") or "°C",
            humidity_min=data.get("humidity_min"),
            humidity_max=data.get("humidity_max"),
            notes=data.get("notes", ""),
            harvest_style=(
                HARVEST_CONTINUOUS
                if data.get("harvest_style") == HARVEST_CONTINUOUS
                else HARVEST_ONCE
            ),
        )

    @property
    def continuous(self) -> bool:
        """Return whether the plants keep growing while they are harvested a little at a time."""
        return self.harvest_style == HARVEST_CONTINUOUS

    def stage_index(self, stage_id: str | None) -> int | None:
        """Return the index of a stage id, or None."""
        for index, stage in enumerate(self.stages):
            if stage.id == stage_id:
                return index
        return None

    @property
    def total_days(self) -> int:
        """Return the sum of all stage durations."""
        return sum(stage.days for stage in self.stages)
