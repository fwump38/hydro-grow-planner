"""Data model for grow plans.

A plan is stored as a config subentry. Its data is a plain JSON structure:

    {
      "name": "Lettuce",
      "target_ph": 6.0,          # optional
      "notes": "",
      "stages": [
        {
          "id": "a1b2c3",
          "name": "Sprouting",
          "stage_type": "sprouting",
          "days": 7,
          "outcome": "",
          "target_ec": 0.8,      # optional
          "schedules": {"<device id>": {"mode": "time_window", ...}},
          "tasks": [{"id": "...", "day": 3, "task_type": "top_up", ...}]
        }
      ]
    }

Stage and task ids are stable, so reordering stages never loses track of the
stage a running grow is in.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
import uuid

from .const import MODE_MANUAL


def new_id() -> str:
    """Return a short random id for stages and tasks."""
    return uuid.uuid4().hex[:8]


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
    """A task scheduled on a given day of a stage."""

    id: str
    day: int
    task_type: str
    title: str
    note: str = ""

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Task:
        """Build from stored data."""
        return cls(
            id=data["id"],
            day=int(data["day"]),
            task_type=data.get("task_type", "reminder"),
            title=data.get("title", ""),
            note=data.get("note", ""),
        )


@dataclass(frozen=True, slots=True)
class Stage:
    """One stage of a plan."""

    id: str
    name: str
    stage_type: str
    days: int
    outcome: str = ""
    target_ec: float | None = None
    schedules: dict[str, DeviceSchedule] = field(default_factory=dict)
    tasks: tuple[Task, ...] = ()

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Stage:
        """Build from stored data."""
        return cls(
            id=data["id"],
            name=data["name"],
            stage_type=data.get("stage_type", "other"),
            days=int(data.get("days", 1)),
            outcome=data.get("outcome", ""),
            target_ec=data.get("target_ec"),
            schedules={
                device_id: DeviceSchedule.from_dict(sched)
                for device_id, sched in data.get("schedules", {}).items()
            },
            tasks=tuple(
                sorted(
                    (Task.from_dict(t) for t in data.get("tasks", [])),
                    key=lambda t: t.day,
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
    target_ph: float | None = None
    notes: str = ""

    @classmethod
    def from_dict(cls, plan_id: str, data: dict[str, Any]) -> Plan:
        """Build from subentry data."""
        return cls(
            id=plan_id,
            name=data.get("name", ""),
            stages=tuple(Stage.from_dict(s) for s in data.get("stages", [])),
            target_ph=data.get("target_ph"),
            notes=data.get("notes", ""),
        )

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
