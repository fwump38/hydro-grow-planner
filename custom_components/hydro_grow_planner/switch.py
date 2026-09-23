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
    async_add_entities([ScheduleControlSwitch(entry.runtime_data)])


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
