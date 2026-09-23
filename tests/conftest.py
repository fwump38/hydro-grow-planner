"""Fixtures for Hydro Grow Planner tests."""

from __future__ import annotations

from collections.abc import Generator
from datetime import datetime
from typing import Any

from freezegun.api import FrozenDateTimeFactory
from homeassistant.config_entries import ConfigSubentryData
from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component
from homeassistant.util import dt as dt_util
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.hydro_grow_planner.const import DOMAIN, SUBENTRY_TYPE_PLAN

DEVICES = [
    {"id": "dev_side", "name": "Side lights", "entity_id": "input_boolean.side_lights"},
    {"id": "dev_center", "name": "Center lights", "entity_id": "input_boolean.center_lights"},
    {"id": "dev_pump", "name": "Water pump", "entity_id": "input_boolean.water_pump"},
]

PLAN = {
    "name": "Lettuce",
    "target_ph": 6.0,
    "notes": "",
    "stages": [
        {
            "id": "s1",
            "name": "Sprouting",
            "stage_type": "sprouting",
            "days": 7,
            "outcome": "Sprouts",
            "target_ec": 0.8,
            "schedules": {
                "dev_side": {"mode": "time_window", "on_time": "11:30:00", "off_time": "16:30:00"},
                "dev_center": {"mode": "off"},
                "dev_pump": {"mode": "interval", "interval_on": 900, "interval_every": 10800},
            },
            "tasks": [
                {"id": "t1", "day": 1, "task_type": "reminder", "title": "Plant seeds", "note": ""},
                {"id": "t2", "day": 3, "task_type": "top_up", "title": "Top up", "note": "Tap"},
            ],
        },
        {
            "id": "s2",
            "name": "Seedling",
            "stage_type": "seedling",
            "days": 7,
            "outcome": "",
            "target_ec": 1.2,
            "schedules": {
                "dev_side": {"mode": "off"},
                "dev_center": {
                    "mode": "time_window",
                    "on_time": "10:00:00",
                    "off_time": "18:00:00",
                },
            },
            "tasks": [],
        },
    ],
}


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations: None) -> Generator[None]:
    """Enable custom integrations in all tests."""
    yield


@pytest.fixture
def plan_data() -> dict[str, Any]:
    """Return a plan."""
    return PLAN


@pytest.fixture
def mock_entry(plan_data: dict[str, Any]) -> MockConfigEntry:
    """Return a config entry with one plan."""
    return MockConfigEntry(
        domain=DOMAIN,
        title="Tower",
        data={"name": "Tower", "devices": DEVICES, "ph_sensor": None, "ec_sensor": None},
        options={
            "ph_tolerance": 0.3,
            "ec_tolerance": 0.3,
            "reading_interval_days": 3,
            "reminder_time": "08:00:00",
            "auto_advance": False,
        },
        subentries_data=[
            ConfigSubentryData(
                data=plan_data,
                subentry_type=SUBENTRY_TYPE_PLAN,
                title=plan_data["name"],
                unique_id=None,
            )
        ],
    )


@pytest.fixture
async def devices(hass: HomeAssistant) -> None:
    """Create the controlled input_booleans."""
    assert await async_setup_component(
        hass,
        "input_boolean",
        {"input_boolean": {"side_lights": {}, "center_lights": {}, "water_pump": {}}},
    )


@pytest.fixture
async def setup_entry(
    hass: HomeAssistant, devices: None, mock_entry: MockConfigEntry, freezer: FrozenDateTimeFactory
) -> MockConfigEntry:
    """Set up the integration at 06:00 on 2026-09-01; tests move time forward."""
    freezer.move_to(datetime(2026, 9, 1, 6, 0, tzinfo=dt_util.get_default_time_zone()))
    mock_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(mock_entry.entry_id)
    await hass.async_block_till_done()
    return mock_entry
