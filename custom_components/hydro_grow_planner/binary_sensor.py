"""Binary sensors for Hydro Grow Planner."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .entity import GrowEntity
from .manager import GrowConfigEntry, GrowDevice, GrowManager
from .schedule import describe


@dataclass(frozen=True, kw_only=True)
class GrowBinarySensorDescription(BinarySensorEntityDescription):
    """Describes a grow binary sensor."""

    value_fn: Callable[[GrowManager], bool | None]


BINARY_SENSORS: tuple[GrowBinarySensorDescription, ...] = (
    GrowBinarySensorDescription(
        key="ph_out_of_range",
        translation_key="ph_out_of_range",
        device_class=BinarySensorDeviceClass.PROBLEM,
        value_fn=lambda m: m.ph_out_of_range,
    ),
    GrowBinarySensorDescription(
        key="ec_out_of_range",
        translation_key="ec_out_of_range",
        device_class=BinarySensorDeviceClass.PROBLEM,
        value_fn=lambda m: m.ec_out_of_range,
    ),
    GrowBinarySensorDescription(
        key="reading_overdue",
        translation_key="reading_overdue",
        device_class=BinarySensorDeviceClass.PROBLEM,
        value_fn=lambda m: m.reading_overdue,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: GrowConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up binary sensors."""
    manager = entry.runtime_data
    entities: list[BinarySensorEntity] = [
        GrowBinarySensor(manager, desc) for desc in BINARY_SENSORS
    ]
    entities.extend(ScheduledOnSensor(manager, device) for device in manager.devices)
    if manager.has_temperature_sensor:
        entities.append(ClimateRangeSensor(manager, "temperature"))
    if manager.has_humidity_sensor:
        entities.append(ClimateRangeSensor(manager, "humidity"))
    async_add_entities(entities)


class GrowBinarySensor(GrowEntity, BinarySensorEntity):
    """A grow problem sensor."""

    entity_description: GrowBinarySensorDescription

    def __init__(self, manager: GrowManager, description: GrowBinarySensorDescription) -> None:
        """Initialize."""
        super().__init__(manager, description.key)
        self.entity_description = description

    @property
    def is_on(self) -> bool | None:
        """Return the state."""
        return self.entity_description.value_fn(self.manager)


class ScheduledOnSensor(GrowEntity, BinarySensorEntity):
    """Whether the schedule wants a device on right now.

    Comparing this to the device itself shows a manual override at a glance.
    """

    _attr_translation_key = "scheduled_on"

    def __init__(self, manager: GrowManager, device: GrowDevice) -> None:
        """Initialize."""
        super().__init__(manager, f"device_{device.id}_scheduled")
        self.device = device
        self._attr_translation_placeholders = {"device": device.name}

    @property
    def is_on(self) -> bool | None:
        """Return the desired state; unknown when the device is unmanaged."""
        return self.manager.desired(self.device)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the schedule and controlled entity."""
        schedule = self.manager.schedule_for(self.device)
        return {
            "controlled_entity": self.device.entity_id,
            "schedule": describe(schedule) if schedule else None,
            "mode": schedule.mode if schedule else None,
            "light": self.device.light,
        }


class ClimateRangeSensor(GrowEntity, BinarySensorEntity):
    """Room temperature or humidity outside the plan's range."""

    _attr_device_class = BinarySensorDeviceClass.PROBLEM

    def __init__(self, manager: GrowManager, kind: str) -> None:
        """Initialize."""
        super().__init__(manager, f"{kind}_out_of_range")
        self._kind = kind
        self._attr_translation_key = f"{kind}_out_of_range"

    @property
    def is_on(self) -> bool | None:
        """Return whether the reading is out of range."""
        if self._kind == "temperature":
            return self.manager.temperature_out_of_range
        return self.manager.humidity_out_of_range

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the reading and the plan's range."""
        if self._kind == "temperature":
            low, high, unit = self.manager.temperature_range
            value = self.manager.temperature
        else:
            (low, high), unit = self.manager.humidity_range, "%"
            value = self.manager.humidity
        return {"value": value, "min": low, "max": high, "unit": unit}
