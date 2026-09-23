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
        return self.manager.desired(self.device.id)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the schedule and controlled entity."""
        stage = self.manager.active_stage
        return {
            "controlled_entity": self.device.entity_id,
            "schedule": describe(stage.schedule_for(self.device.id)) if stage else None,
            "mode": stage.schedule_for(self.device.id).mode if stage else None,
        }
