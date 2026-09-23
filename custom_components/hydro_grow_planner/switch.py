"""Schedule control switch for Hydro Grow Planner."""

from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .entity import GrowEntity
from .manager import GrowConfigEntry, GrowManager


async def async_setup_entry(
    hass: HomeAssistant,
    entry: GrowConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the switch."""
    manager = entry.runtime_data
    async_add_entities([ScheduleControlSwitch(manager), NightLightingSwitch(manager)])


class ScheduleControlSwitch(GrowEntity, SwitchEntity):
    """When off, the plan is tracked but devices are never switched."""

    _attr_translation_key = "schedule_control"
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, manager: GrowManager) -> None:
        """Initialize."""
        super().__init__(manager, "schedule_control")

    @property
    def is_on(self) -> bool:
        """Return whether schedule control is enabled."""
        return self.manager.schedule_enabled

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Enable and immediately sync devices."""
        await self.manager.async_set_schedule_enabled(True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Disable device control."""
        await self.manager.async_set_schedule_enabled(False)


class NightLightingSwitch(GrowEntity, SwitchEntity):
    """Run the lights at night: every light's time window shifts by 12 hours."""

    _attr_translation_key = "night_lighting"

    def __init__(self, manager: GrowManager) -> None:
        """Initialize."""
        super().__init__(manager, "night_lighting")

    @property
    def is_on(self) -> bool:
        """Return whether night lighting is on."""
        return self.manager.night_lighting

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Shift light windows to the night and sync."""
        await self.manager.async_set_night_lighting(True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Return light windows to the day and sync."""
        await self.manager.async_set_night_lighting(False)
