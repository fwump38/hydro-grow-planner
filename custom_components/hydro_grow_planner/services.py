"""Service actions for Hydro Grow Planner."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant, ServiceCall, callback
from homeassistant.exceptions import ServiceValidationError
import homeassistant.helpers.config_validation as cv
import voluptuous as vol

from .const import (
    ATTR_CONFIG_ENTRY_ID,
    ATTR_EC,
    ATTR_PH,
    ATTR_PLAN,
    ATTR_STAGE,
    ATTR_START_DATE,
    DOMAIN,
    SERVICE_ADVANCE_STAGE,
    SERVICE_END_GROW,
    SERVICE_LOG_READING,
    SERVICE_SET_STAGE,
    SERVICE_START_GROW,
    SERVICE_SYNC_DEVICES,
)
from .manager import GrowManager

_ENTRY = {vol.Optional(ATTR_CONFIG_ENTRY_ID): cv.string}

SCHEMA_BASE = vol.Schema(_ENTRY)
SCHEMA_START = vol.Schema(
    {
        **_ENTRY,
        vol.Required(ATTR_PLAN): cv.string,
        vol.Optional(ATTR_STAGE): cv.string,
        vol.Optional(ATTR_START_DATE): cv.date,
    }
)
SCHEMA_SET_STAGE = vol.Schema(
    {
        **_ENTRY,
        vol.Required(ATTR_STAGE): cv.string,
        vol.Optional(ATTR_START_DATE): cv.date,
    }
)
SCHEMA_LOG = vol.All(
    vol.Schema(
        {
            **_ENTRY,
            vol.Optional(ATTR_PH): vol.All(vol.Coerce(float), vol.Range(0, 14)),
            vol.Optional(ATTR_EC): vol.All(vol.Coerce(float), vol.Range(0, 20)),
        }
    ),
    cv.has_at_least_one_key(ATTR_PH, ATTR_EC),
)


def _manager(hass: HomeAssistant, call: ServiceCall) -> GrowManager:
    """Resolve the target grow system; optional when only one exists."""
    entries = [
        e for e in hass.config_entries.async_entries(DOMAIN) if e.state is ConfigEntryState.LOADED
    ]
    if entry_id := call.data.get(ATTR_CONFIG_ENTRY_ID):
        entries = [e for e in entries if e.entry_id == entry_id]
        if not entries:
            raise ServiceValidationError(
                translation_domain=DOMAIN, translation_key="unknown_system"
            )
    elif len(entries) != 1:
        raise ServiceValidationError(translation_domain=DOMAIN, translation_key="system_required")
    return entries[0].runtime_data


@callback
def async_setup_services(hass: HomeAssistant) -> None:
    """Register the integration's services."""

    async def start_grow(call: ServiceCall) -> None:
        await _manager(hass, call).async_start_grow(
            call.data[ATTR_PLAN], call.data.get(ATTR_STAGE), call.data.get(ATTR_START_DATE)
        )

    async def end_grow(call: ServiceCall) -> None:
        await _manager(hass, call).async_end_grow()

    async def set_stage(call: ServiceCall) -> None:
        await _manager(hass, call).async_set_stage(
            call.data[ATTR_STAGE], call.data.get(ATTR_START_DATE)
        )

    async def advance_stage(call: ServiceCall) -> None:
        await _manager(hass, call).async_advance_stage()

    async def log_reading(call: ServiceCall) -> None:
        await _manager(hass, call).async_log_reading(call.data.get(ATTR_PH), call.data.get(ATTR_EC))

    async def sync_devices(call: ServiceCall) -> None:
        await _manager(hass, call).async_sync(force=True)

    hass.services.async_register(DOMAIN, SERVICE_START_GROW, start_grow, SCHEMA_START)
    hass.services.async_register(DOMAIN, SERVICE_END_GROW, end_grow, SCHEMA_BASE)
    hass.services.async_register(DOMAIN, SERVICE_SET_STAGE, set_stage, SCHEMA_SET_STAGE)
    hass.services.async_register(DOMAIN, SERVICE_ADVANCE_STAGE, advance_stage, SCHEMA_BASE)
    hass.services.async_register(DOMAIN, SERVICE_LOG_READING, log_reading, SCHEMA_LOG)
    hass.services.async_register(DOMAIN, SERVICE_SYNC_DEVICES, sync_devices, SCHEMA_BASE)
