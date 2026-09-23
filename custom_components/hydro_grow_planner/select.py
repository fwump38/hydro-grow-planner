"""Plan and stage selectors for Hydro Grow Planner."""

from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import NO_PLAN
from .entity import GrowEntity
from .manager import GrowConfigEntry, GrowManager


async def async_setup_entry(
    hass: HomeAssistant,
    entry: GrowConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up selectors."""
    manager = entry.runtime_data
    async_add_entities([PlanSelect(manager), StageSelect(manager)])


class PlanSelect(GrowEntity, SelectEntity):
    """The running plan. Choosing a plan starts a new grow at stage 1."""

    _attr_translation_key = "active_plan"

    def __init__(self, manager: GrowManager) -> None:
        """Initialize."""
        super().__init__(manager, "active_plan")
        # Plan names are the options; "none" (translated) ends the grow.
        self._attr_options = [NO_PLAN, *sorted(p.name for p in manager.plans.values())]

    @property
    def current_option(self) -> str | None:
        """Return the running plan's name."""
        plan = self.manager.active_plan
        return plan.name if plan and self.manager.is_active else NO_PLAN

    async def async_select_option(self, option: str) -> None:
        """Start or end a grow."""
        if option == NO_PLAN:
            await self.manager.async_end_grow()
        elif option != self.current_option:
            await self.manager.async_start_grow(option)


class StageSelect(GrowEntity, SelectEntity):
    """The current stage of the running plan."""

    _attr_translation_key = "current_stage"

    def __init__(self, manager: GrowManager) -> None:
        """Initialize."""
        super().__init__(manager, "current_stage")

    @property
    def available(self) -> bool:
        """Only available while a grow is running."""
        return self.manager.is_active

    @property
    def options(self) -> list[str]:
        """Return the stages of the running plan, numbered for uniqueness."""
        plan = self.manager.active_plan
        if plan is None:
            return []
        return [f"{i}. {s.name}" for i, s in enumerate(plan.stages, start=1)]

    @property
    def current_option(self) -> str | None:
        """Return the current stage."""
        stage, index = self.manager.active_stage, self.manager.stage_index
        if stage is None or index is None:
            return None
        return f"{index + 1}. {stage.name}"

    async def async_select_option(self, option: str) -> None:
        """Jump to a stage."""
        if option != self.current_option:
            await self.manager.async_set_stage(int(option.split(".", 1)[0]))
