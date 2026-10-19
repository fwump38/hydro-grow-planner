"""A JSON-friendly view of one grow system, shared by the API and MQTT publisher."""

from __future__ import annotations

from typing import Any

from .core import units
from .core.models import format_range
from .core.progress import days_remaining, expected_end, progress_percent
from .core.schedule import day_profile, describe
from .engine import METRICS, Grow, GrowSystem


def _ec(value: float | None, unit: str) -> float | None:
    return units.from_canonical(value, unit) if value is not None else None


def _grow_view(grow: Grow) -> dict[str, Any]:
    plan, stage = grow.plan, grow.stage
    started, day = grow.stage_started, grow.stage_day
    return {
        "id": grow.id,
        "name": grow.name,
        "active": grow.is_active,
        "plan": (
            {"id": plan.id, "name": plan.name, "harvest_style": plan.harvest_style}
            if plan
            else None
        ),
        "stage": (
            {
                "id": stage.id,
                "name": stage.name,
                "type": stage.stage_type,
                "number": (grow.stage_index or 0) + 1,
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
        "grow_day": grow.grow_day,
        "grow_started": grow.grow_started.isoformat() if grow.grow_started else None,
        "expected_end": (
            expected_end(plan, grow.stage_index or 0, started).isoformat()
            if plan and started
            else None
        ),
        "night_lighting": grow.night_lighting,
    }


def _merge_windows(windows: list[tuple[int, int]]) -> list[tuple[int, int]]:
    merged: list[tuple[int, int]] = []
    for start, end in sorted(windows):
        if merged and start <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))
        else:
            merged.append((start, end))
    return merged


def snapshot(system: GrowSystem, with_profiles: bool = False) -> dict[str, Any]:
    """Return everything the UI and entities need to show.

    `with_profiles` adds each device's 24-hour on-windows, which costs a minute-by-
    minute scan, so only the panel asks for it.
    """
    now = system.now
    ec_unit = system.ec_unit

    devices = []
    for device in system.devices:
        drivers = system.drivers(device)
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
            # More than one grow schedules this device: it is on if any of them wants it on.
            "drivers": [
                {"grow_id": g.id, "grow": g.name, "schedule": describe(s), "mode": s.mode}
                for g, s in drivers
            ],
        }
        if with_profiles and schedule is not None:
            entry["profile"] = _merge_windows([w for _, s in drivers for w in day_profile(s, now)])
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
            "conflict": system.range_conflict(metric),
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
        "grows": [_grow_view(g) for g in system.grows],
        "system_day": system.system_day,
        "system_started": system.system_started.isoformat() if system.system_started else None,
        "maintenance": system.maintenance_view(),
        "plans": [{"id": p.id, "name": p.name} for p in system.plans.values()],
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
