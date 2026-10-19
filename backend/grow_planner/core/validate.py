"""Validation and normalisation of plans and templates. Pure logic.

`normalize_plan` takes whatever the editor sends and returns clean plan data plus a
list of errors, each with a `path` like `stages[1].schedules.d_pump.interval_on` so
the UI can show the message next to the field. A plan is only saved when there are
no errors.
"""

from __future__ import annotations

from collections.abc import Callable, Collection
from datetime import time
from typing import Any

from .const import (
    HARVEST_CONTINUOUS,
    HARVEST_STYLES,
    MODE_INTERVAL,
    MODE_MANUAL,
    MODE_TIME_WINDOW,
    SCHEDULE_MODES,
    STAGE_TYPES,
    TASK_TYPES,
)

Error = dict[str, str]
TEMP_UNITS = ("°C", "°F")


def _number(value: Any) -> float | None:
    if value is None or value == "":
        return None
    return float(value)


def _range(
    data: dict[str, Any],
    low: str,
    high: str,
    path: str,
    errors: list[Error],
    hard: tuple[float, float],
) -> tuple[float | None, float | None]:
    try:
        lo, hi = _number(data.get(low)), _number(data.get(high))
    except (TypeError, ValueError):
        errors.append({"path": f"{path}{low}", "message": "Enter a number"})
        return None, None
    for key, value in ((low, lo), (high, hi)):
        if value is not None and not hard[0] <= value <= hard[1]:
            errors.append({"path": f"{path}{key}", "message": f"Must be {hard[0]:g}–{hard[1]:g}"})
    if lo is not None and hi is not None and lo > hi:
        errors.append({"path": f"{path}{low}", "message": "Minimum is above the maximum"})
    return lo, hi


def _parse_time(value: Any) -> str | None:
    """Accept H:MM, HH:MM or HH:MM:SS; return HH:MM:SS."""
    try:
        parts = [int(p) for p in str(value).strip().split(":")]
        if len(parts) not in (2, 3):
            return None
        return time(*parts).strftime("%H:%M:%S")
    except ValueError:
        return None


def _schedule(raw: dict[str, Any], path: str, errors: list[Error]) -> dict[str, Any]:
    mode = raw.get("mode", MODE_MANUAL)
    if mode not in SCHEDULE_MODES:
        errors.append({"path": f"{path}.mode", "message": "Unknown mode"})
        return {"mode": MODE_MANUAL}
    sched: dict[str, Any] = {"mode": mode}
    if mode == MODE_TIME_WINDOW:
        on, off = _parse_time(raw.get("on_time")), _parse_time(raw.get("off_time"))
        if on is None:
            errors.append({"path": f"{path}.on_time", "message": "Enter a time"})
        if off is None:
            errors.append({"path": f"{path}.off_time", "message": "Enter a time"})
        if on and off and on == off:
            errors.append({"path": f"{path}.off_time", "message": "On and off times are the same"})
        sched.update(on_time=on or "06:00:00", off_time=off or "22:00:00")
    elif mode == MODE_INTERVAL:
        try:
            on, every = int(raw.get("interval_on") or 0), int(raw.get("interval_every") or 0)
        except (TypeError, ValueError):
            on = every = 0
        if on <= 0:
            errors.append({"path": f"{path}.interval_on", "message": "Must be more than 0"})
        if every <= 0:
            errors.append({"path": f"{path}.interval_every", "message": "Must be more than 0"})
        if on > 0 and every > 0 and on >= every:
            errors.append(
                {"path": f"{path}.interval_on", "message": "Must be shorter than the cycle"}
            )
        sched.update(interval_on=on or 900, interval_every=every or 10800)
    return sched


def _task(raw: dict[str, Any], path: str, errors: list[Error], make_id: Callable[[], str]) -> dict:
    title = str(raw.get("title") or "").strip()
    if not title:
        errors.append({"path": f"{path}.title", "message": "Enter a title"})
    task_type = raw.get("task_type") or "reminder"
    if task_type not in TASK_TYPES:
        errors.append({"path": f"{path}.task_type", "message": "Unknown task type"})
        task_type = "reminder"
    try:
        days = sorted({int(d) for d in raw.get("days") or []})
    except (TypeError, ValueError):
        days = []
    if not days or days[0] < 1:
        errors.append({"path": f"{path}.days", "message": "Enter day numbers, starting at 1"})
        days = days or [1]
    try:
        every = int(raw.get("every") or 0)
        until = int(raw["until"]) if raw.get("until") else None
    except (TypeError, ValueError):
        every, until = 0, None
        errors.append({"path": f"{path}.every", "message": "Enter a whole number"})
    if every < 0:
        errors.append({"path": f"{path}.every", "message": "Cannot be negative"})
        every = 0
    if until is not None and (every <= 0 or until < days[0]):
        errors.append({"path": f"{path}.until", "message": "Must be on or after the first day"})
    return {
        "id": raw.get("id") or make_id(),
        "task_type": task_type,
        "title": title,
        "days": days,
        "every": every,
        "until": until,
        "method": str(raw.get("method") or "").strip(),
        "note": str(raw.get("note") or ""),
    }


# Added to a continuous plan that has no repeating harvest task of its own.
DEFAULT_HARVEST_TASK = {
    "task_type": "harvest",
    "title": "Harvest",
    "method": "Take a little at a time; leave the plant enough to keep growing",
    "note": "Pick only what is ripe or full size, and leave the growing point and most "
    "of the leaves or fruit on the plant so it can keep producing.",
    "days": [1],
    "every": 7,
    "until": None,
}
HARVEST_STAGE_TYPES = ("harvest", "fruiting", "ripening")


def ensure_harvest_task(
    stages: list[dict[str, Any]], make_id: Callable[[], str]
) -> dict[str, Any] | None:
    """Add a repeating harvest task to a continuous plan that lacks one; return it.

    It goes in the last harvest, fruiting or ripening stage, else the last stage.
    """
    if not stages or any(
        t["task_type"] == "harvest" and t["every"] > 0 for s in stages for t in s["tasks"]
    ):
        return None
    stage = next(
        (s for s in reversed(stages) if s["stage_type"] in HARVEST_STAGE_TYPES), stages[-1]
    )
    task = {**DEFAULT_HARVEST_TASK, "id": make_id(), "until": stage["days"]}
    stage["tasks"].append(task)
    return task


def normalize_plan(
    data: dict[str, Any],
    make_id: Callable[[], str],
    schedule_keys: Collection[str] | None = None,
) -> tuple[dict[str, Any], list[Error]]:
    """Return (clean plan data, errors).

    `schedule_keys` limits which devices (or, for templates, roles) may have
    schedules; unknown keys are an error. None allows any key.
    """
    errors: list[Error] = []
    name = str(data.get("name") or "").strip()
    if not name:
        errors.append({"path": "name", "message": "Enter a name"})

    ph_min, ph_max = _range(data, "ph_min", "ph_max", "", errors, (0, 14))
    temp_min, temp_max = _range(data, "temp_min", "temp_max", "", errors, (-50, 150))
    hum_min, hum_max = _range(data, "humidity_min", "humidity_max", "", errors, (0, 100))
    temp_unit = data.get("temp_unit") or "°C"
    if temp_unit not in TEMP_UNITS:
        errors.append({"path": "temp_unit", "message": "Use °C or °F"})
        temp_unit = "°C"

    stages = []
    raw_stages = data.get("stages") or []
    if not raw_stages:
        errors.append({"path": "stages", "message": "Add at least one stage"})
    for i, raw in enumerate(raw_stages):
        path = f"stages[{i}]"
        stage_name = str(raw.get("name") or "").strip()
        if not stage_name:
            errors.append({"path": f"{path}.name", "message": "Enter a name"})
        stage_type = raw.get("stage_type") or "other"
        if stage_type not in STAGE_TYPES:
            errors.append({"path": f"{path}.stage_type", "message": "Unknown stage type"})
            stage_type = "other"
        try:
            days = int(raw.get("days"))
        except (TypeError, ValueError):
            days = 0
        if days < 1:
            errors.append({"path": f"{path}.days", "message": "Must be at least 1 day"})
            days = 1
        ec_min, ec_max = _range(raw, "ec_min", "ec_max", f"{path}.", errors, (0, 20))
        schedules = {}
        for key, sched in (raw.get("schedules") or {}).items():
            if schedule_keys is not None and key not in schedule_keys:
                errors.append({"path": f"{path}.schedules.{key}", "message": "Unknown device"})
                continue
            schedules[key] = _schedule(sched or {}, f"{path}.schedules.{key}", errors)
        tasks = [
            _task(t, f"{path}.tasks[{j}]", errors, make_id)
            for j, t in enumerate(raw.get("tasks") or [])
        ]
        stages.append(
            {
                "id": raw.get("id") or make_id(),
                "name": stage_name,
                "stage_type": stage_type,
                "days": days,
                "outcome": str(raw.get("outcome") or ""),
                "ec_min": ec_min,
                "ec_max": ec_max,
                "schedules": schedules,
                "tasks": tasks,
            }
        )

    harvest_style = data.get("harvest_style") or "once"
    if harvest_style not in HARVEST_STYLES:
        errors.append({"path": "harvest_style", "message": "Unknown harvest style"})
        harvest_style = "once"
    if harvest_style == HARVEST_CONTINUOUS:
        ensure_harvest_task(stages, make_id)

    plan = {
        "name": name,
        "ph_min": ph_min,
        "ph_max": ph_max,
        "temp_min": temp_min,
        "temp_max": temp_max,
        "temp_unit": temp_unit,
        "humidity_min": hum_min,
        "humidity_max": hum_max,
        "notes": str(data.get("notes") or ""),
        "harvest_style": harvest_style,
        "stages": stages,
    }
    return plan, errors
