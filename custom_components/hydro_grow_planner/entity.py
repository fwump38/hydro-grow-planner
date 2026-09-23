"""Base entity for Hydro Grow Planner."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity import Entity

from .const import DOMAIN
from .manager import GrowManager


class GrowEntity(Entity):
    """An entity belonging to one grow system."""

    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(self, manager: GrowManager, key: str) -> None:
        """Initialize."""
        self.manager = manager
        entry = manager.entry
        self._attr_unique_id = f"{entry.entry_id}_{key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=entry.title,
            manufacturer="Hydro Grow Planner",
            entry_type=DeviceEntryType.SERVICE,
        )

    async def async_added_to_hass(self) -> None:
        """Subscribe to manager updates."""
        self.async_on_remove(self.manager.async_add_listener(self.async_write_ha_state))
