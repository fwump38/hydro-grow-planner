"""Sensors for Hydro Grow Planner."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import date
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import PERCENTAGE, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .entity import GrowEntity
from .manager import GrowConfigEntry, GrowManager
from .models import format_range
from .schedule import describe


@dataclass(frozen=True, kw_only=True)
class GrowSensorDescription(SensorEntityDescription):
    """Describes a grow sensor."""

    value_fn: Callable[[GrowManager], Any]
    attrs_fn: Callable[[GrowManager], dict[str, Any]] | None = None


def _stage_attrs(m: GrowManager) -> dict[str, Any]:
    plan, stage = m.active_plan, m.active_stage
    if plan is None or stage is None:
        return {}
    return {
        "plan": plan.name,
        "stage_number": (m.stage_index or 0) + 1,
        "stage_count": len(plan.stages),
        "stage_type": stage.stage_type,
        "estimated_days": stage.days,
        "expected_outcome": stage.outcome,
        "ec_range": format_range(stage.ec_min, stage.ec_max),
        "night_lighting": m.night_lighting,
        "stage_started": m.stage_started.isoformat() if m.stage_started else None,
        "schedules": {d.name: describe(sched) for d in m.devices if (sched := m.schedule_for(d))},
        "stages": [s.name for s in plan.stages],
    }


def _next_task(m: GrowManager) -> date | None:
    open_items = [t for t in m.task_items if not t.completed]
    return min((t.due for t in open_items), default=None)


def _next_task_attrs(m: GrowManager) -> dict[str, Any]:
    open_items = sorted((t for t in m.task_items if not t.completed), key=lambda t: t.due)
    if not open_items:
        return {}
    first = open_items[0]
    return {
        "title": first.task.title,
        "task_type": first.task.task_type,
        "note": first.task.note,
        "upcoming": [
            {"title": t.task.title, "due": t.due.isoformat(), "task_type": t.task.task_type}
            for t in open_items
        ],
    }


SENSORS: tuple[GrowSensorDescription, ...] = (
    GrowSensorDescription(
        key="plan",
        translation_key="plan",
        value_fn=lambda m: m.active_plan.name if m.is_active and m.active_plan else None,
        attrs_fn=lambda m: (
            {
                "notes": m.active_plan.notes,
                "ph_range": format_range(m.active_plan.ph_min, m.active_plan.ph_max),
            }
            if m.is_active and m.active_plan
            else {}
        ),
    ),
    GrowSensorDescription(
        key="stage",
        translation_key="stage",
        value_fn=lambda m: m.active_stage.name if m.active_stage else None,
        attrs_fn=_stage_attrs,
    ),
    GrowSensorDescription(
        key="stage_day",
        translation_key="stage_day",
        value_fn=lambda m: m.stage_day,
    ),
    GrowSensorDescription(
        key="stage_days_remaining",
        translation_key="stage_days_remaining",
        device_class=SensorDeviceClass.DURATION,
        native_unit_of_measurement=UnitOfTime.DAYS,
        value_fn=lambda m: m.stage_days_remaining,
    ),
    GrowSensorDescription(
        key="stage_progress",
        translation_key="stage_progress",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda m: m.stage_progress,
    ),
    GrowSensorDescription(
        key="grow_day",
        translation_key="grow_day",
        value_fn=lambda m: m.grow_day,
    ),
    GrowSensorDescription(
        key="grow_started",
        translation_key="grow_started",
        device_class=SensorDeviceClass.DATE,
        value_fn=lambda m: m.grow_started if m.is_active else None,
    ),
    GrowSensorDescription(
        key="expected_harvest",
        translation_key="expected_harvest",
        device_class=SensorDeviceClass.DATE,
        value_fn=lambda m: m.expected_harvest,
    ),
    GrowSensorDescription(
        key="ph_min",
        translation_key="ph_min",
        device_class=SensorDeviceClass.PH,
        value_fn=lambda m: m.ph_range[0],
    ),
    GrowSensorDescription(
        key="ph_max",
        translation_key="ph_max",
        device_class=SensorDeviceClass.PH,
        value_fn=lambda m: m.ph_range[1],
    ),
    GrowSensorDescription(
        key="ec_min",
        translation_key="ec_min",
        native_unit_of_measurement="mS/cm",
        suggested_display_precision=1,
        value_fn=lambda m: m.ec_range[0],
    ),
    GrowSensorDescription(
        key="ec_max",
        translation_key="ec_max",
        native_unit_of_measurement="mS/cm",
        suggested_display_precision=1,
        value_fn=lambda m: m.ec_range[1],
    ),
    GrowSensorDescription(
        key="tasks_due",
        translation_key="tasks_due",
        value_fn=lambda m: len(m.tasks_due()) if m.is_active else None,
        attrs_fn=lambda m: {
            "tasks": [
                {"title": t.task.title, "due": t.due.isoformat(), "task_type": t.task.task_type}
                for t in m.tasks_due()
            ]
        },
    ),
    GrowSensorDescription(
        key="next_task",
        translation_key="next_task",
        device_class=SensorDeviceClass.DATE,
        value_fn=_next_task,
        attrs_fn=_next_task_attrs,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: GrowConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up sensors."""
    manager = entry.runtime_data
    async_add_entities(GrowSensor(manager, desc) for desc in SENSORS)


class GrowSensor(GrowEntity, SensorEntity):
    """A grow status sensor."""

    entity_description: GrowSensorDescription

    def __init__(self, manager: GrowManager, description: GrowSensorDescription) -> None:
        """Initialize."""
        super().__init__(manager, description.key)
        self.entity_description = description

    @property
    def native_value(self) -> Any:
        """Return the state."""
        return self.entity_description.value_fn(self.manager)

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return extra attributes."""
        if self.entity_description.attrs_fn is None:
            return None
        return self.entity_description.attrs_fn(self.manager)
