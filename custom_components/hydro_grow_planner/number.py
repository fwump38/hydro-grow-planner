"""Manual water readings for Hydro Grow Planner.

Only created for values that don't come from a configured sensor.
"""

from __future__ import annotations

from homeassistant.components.number import (
    NumberDeviceClass,
    NumberEntity,
    NumberEntityDescription,
    NumberMode,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import ATTR_EC, ATTR_PH
from .entity import GrowEntity
from .manager import GrowConfigEntry, GrowManager

PH = NumberEntityDescription(
    key="measured_ph",
    translation_key="measured_ph",
    device_class=NumberDeviceClass.PH,
    native_min_value=0,
    native_max_value=14,
    native_step=0.1,
    mode=NumberMode.BOX,
)
EC = NumberEntityDescription(
    key="measured_ec",
    translation_key="measured_ec",
    native_unit_of_measurement="mS/cm",
    native_min_value=0,
    native_max_value=20,
    native_step=0.1,
    mode=NumberMode.BOX,
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: GrowConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up reading inputs."""
    manager = entry.runtime_data
    entities = []
    if not manager.has_ph_sensor:
        entities.append(ReadingNumber(manager, PH, ATTR_PH))
    if not manager.has_ec_sensor:
        entities.append(ReadingNumber(manager, EC, ATTR_EC))
    async_add_entities(entities)


class ReadingNumber(GrowEntity, NumberEntity):
    """A manually logged water reading."""

    def __init__(
        self, manager: GrowManager, description: NumberEntityDescription, field: str
    ) -> None:
        """Initialize."""
        super().__init__(manager, description.key)
        self.entity_description = description
        self._field = field

    @property
    def native_value(self) -> float | None:
        """Return the last logged value."""
        if self._field == ATTR_PH:
            return self.manager.measured_ph
        return self.manager.measured_ec

    async def async_set_native_value(self, value: float) -> None:
        """Log a new reading."""
        await self.manager.async_log_reading(**{self._field: value})
