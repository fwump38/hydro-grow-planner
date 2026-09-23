"""Buttons for Hydro Grow Planner."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from homeassistant.components.button import ButtonEntity, ButtonEntityDescription
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .entity import GrowEntity
from .manager import GrowConfigEntry, GrowManager


@dataclass(frozen=True, kw_only=True)
class GrowButtonDescription(ButtonEntityDescription):
    """Describes a grow button."""

    press_fn: Callable[[GrowManager], Awaitable[None]]
    available_fn: Callable[[GrowManager], bool] = lambda m: m.is_active


BUTTONS: tuple[GrowButtonDescription, ...] = (
    GrowButtonDescription(
        key="advance_stage",
        translation_key="advance_stage",
        press_fn=lambda m: m.async_advance_stage(),
    ),
    GrowButtonDescription(
        key="previous_stage",
        translation_key="previous_stage",
        press_fn=lambda m: m.async_previous_stage(),
    ),
    GrowButtonDescription(
        key="restart_stage",
        translation_key="restart_stage",
        press_fn=lambda m: m.async_restart_stage(),
    ),
    GrowButtonDescription(
        key="sync_devices",
        translation_key="sync_devices",
        press_fn=lambda m: m.async_sync(force=True),
    ),
    GrowButtonDescription(
        key="log_reading",
        translation_key="log_reading",
        press_fn=lambda m: m.async_log_reading(),
        available_fn=lambda m: not (m.has_ph_sensor and m.has_ec_sensor),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: GrowConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up buttons."""
    manager = entry.runtime_data
    async_add_entities(
        GrowButton(manager, desc)
        for desc in BUTTONS
        if desc.key != "log_reading" or desc.available_fn(manager)
    )


class GrowButton(GrowEntity, ButtonEntity):
    """A grow action button."""

    entity_description: GrowButtonDescription

    def __init__(self, manager: GrowManager, description: GrowButtonDescription) -> None:
        """Initialize."""
        super().__init__(manager, description.key)
        self.entity_description = description

    @property
    def available(self) -> bool:
        """Only offer stage actions while a grow is running."""
        return self.entity_description.available_fn(self.manager)

    async def async_press(self) -> None:
        """Handle a press."""
        await self.entity_description.press_fn(self.manager)
