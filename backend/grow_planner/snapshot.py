"""A JSON-friendly view of one grow system, shared by the API and MQTT publisher."""

from __future__ import annotations

from typing import Any

from .core import units
from .core.models import format_range
from .core.progress import days_remaining, expected_end, progress_percent
from .core.schedule import day_profile, describe
from .engine import METRICS, GrowSystem


def _ec(value: float | None, unit: str) -> float | None:
    return units.from_canonical(value, unit) if value is not None else None


def snapshot(system: GrowSystem, with_profiles: bool = False) -> dict[str, Any]:
    """Return everything the UI and entities need to show.

    `with_profiles` adds each device's 24-hour on-windows, which costs a minute-by-
    minute scan, so only the panel asks for it.
    """
    plan, stage = system.active_plan, system.active_stage
    started = system.stage_started
    day = system.stage_day
    now = system.now
    ec_unit = system.ec_unit

    devices = []
    for device in system.devices:
        schedule = system.schedule_for(device)
        want = system.desired(device)
        actual = system.actual(device)
        change = system.next_change(device)
        entry: dict[str, Any] = {
            "id": device.id,
            "name": device.name,
            "entity_id": device.entity_id,
            "light": device.light,
            "state": actual,
            "desired": want,
            "override": want is not None and actual is not None and want != actual,
            "mode": schedule.mode if schedule else None,
            "schedule": describe(schedule) if schedule else None,
            "next_change": change.isoformat() if change else None,
        }
        if with_profiles and schedule is not None:
            entry["profile"] = day_profile(schedule, now)
        devices.append(entry)

    ec_low, ec_high = system.range_for("ec")
    ranges = {m: system.range_for(m) for m in METRICS}
    values = {
        "ph": system.ph,
        "ec": system.ec,
        "temperature": system.temperature,
        "humidity": system.humidity,
    }
    metrics = {}
    for metric in METRICS:
        low, high = ranges[metric]
        value = values[metric]
        if metric == "ec":
            value, low, high = _ec(value, ec_unit), _ec(low, ec_unit), _ec(high, ec_unit)
        metrics[metric] = {
            "value": value,
            "min": low,
            "max": high,
            "range": format_range(low, high),
            "out_of_range": system.is_out_of_range(metric),
            "from_sensor": system.has_sensor(metric),
            "unit": {
                "ph": None,
                "ec": ec_unit,
                "temperature": system.temperature_unit,
                "humidity": "%",
            }[metric],
        }

    last = system.last_reading
    tasks = system.task_items()
    return {
        "id": system.id,
        "name": system.name,
        "active": system.is_active,
        "plan": {"id": plan.id, "name": plan.name} if plan else None,
        "stage": (
            {
                "id": stage.id,
                "name": stage.name,
                "type": stage.stage_type,
                "number": (system.stage_index or 0) + 1,
                "count": len(plan.stages),
                "days": stage.days,
                "outcome": stage.outcome,
                "started": started.isoformat() if started else None,
                "day": day,
                "days_remaining": days_remaining(stage.days, day) if day else None,
                "progress": progress_percent(stage.days, day) if day else None,
            }
            if plan and stage
            else None
        ),
        "stages": (
            [
                {
                    "id": s.id,
                    "name": s.name,
                    "type": s.stage_type,
                    "days": s.days,
                    "outcome": s.outcome,
                }
                for s in plan.stages
            ]
            if plan
            else []
        ),
        "plans": [{"id": p.id, "name": p.name} for p in system.plans.values()],
        "grow_day": system.grow_day,
        "grow_started": system.grow_started.isoformat() if system.grow_started else None,
        "expected_end": (
            expected_end(plan, system.stage_index or 0, started).isoformat()
            if plan and started
            else None
        ),
        "night_lighting": system.night_lighting,
        "schedule_enabled": system.schedule_enabled,
        "devices": devices,
        "metrics": metrics,
        "ec_unit": ec_unit,
        "ec_range": [ec_low, ec_high],
        "last_reading": last.isoformat() if last else None,
        "reading_overdue": system.reading_overdue,
        "tasks": tasks,
        "tasks_due": sum(1 for t in tasks if not t["done"] and t["due"] <= now.date().isoformat()),
        "activity": system.rt["activity"][-50:][::-1],
    }
