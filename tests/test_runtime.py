"""End-to-end runtime tests: grows, device sync, overrides, stages, tasks, readings."""

from __future__ import annotations

from datetime import datetime

from freezegun.api import FrozenDateTimeFactory
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ServiceValidationError
from homeassistant.util import dt as dt_util
import pytest
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_fire_time_changed,
)

from custom_components.hydro_grow_planner.const import DOMAIN, EVENT_STAGE_CHANGED


def local(day: int, hour: int, minute: int = 0) -> datetime:
    return datetime(2026, 9, day, hour, minute, tzinfo=dt_util.get_default_time_zone())


async def move(hass: HomeAssistant, freezer: FrozenDateTimeFactory, when: datetime) -> None:
    freezer.move_to(when)
    async_fire_time_changed(hass, when)
    await hass.async_block_till_done()


def state(hass: HomeAssistant, entity_id: str) -> str:
    s = hass.states.get(entity_id)
    assert s is not None, entity_id
    return s.state


async def start(hass: HomeAssistant, plan: str = "Lettuce") -> None:
    await hass.services.async_call(
        "select",
        "select_option",
        {"entity_id": "select.tower_plan", "option": plan},
        blocking=True,
    )
    await hass.async_block_till_done()


async def test_idle_after_setup(hass: HomeAssistant, setup_entry: MockConfigEntry) -> None:
    """Nothing runs until a plan is chosen."""
    assert state(hass, "select.tower_plan") == "none"
    assert state(hass, "select.tower_stage") == "unavailable"
    assert state(hass, "sensor.tower_current_stage") == "unknown"
    assert state(hass, "input_boolean.side_lights") == "off"


async def test_start_grow_syncs_devices(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory, setup_entry: MockConfigEntry
) -> None:
    await move(hass, freezer, local(1, 12, 30))
    events = []
    hass.bus.async_listen(EVENT_STAGE_CHANGED, events.append)
    await start(hass)

    assert state(hass, "select.tower_stage") == "1. Sprouting"
    assert state(hass, "sensor.tower_stage_day") == "1"
    assert state(hass, "sensor.tower_expected_end") == "2026-09-15"
    assert state(hass, "input_boolean.side_lights") == "on"
    assert state(hass, "input_boolean.center_lights") == "off"
    assert state(hass, "input_boolean.water_pump") == "off"
    assert state(hass, "binary_sensor.tower_side_lights_scheduled") == "on"
    assert len(events) == 1
    assert events[0].data["stage"] == "Sprouting"

    # Interval pump: on at 15:00 for 15 minutes.
    await move(hass, freezer, local(1, 15, 0))
    assert state(hass, "input_boolean.water_pump") == "on"
    await move(hass, freezer, local(1, 15, 15))
    assert state(hass, "input_boolean.water_pump") == "off"


async def test_manual_override_persists_until_next_change(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory, setup_entry: MockConfigEntry
) -> None:
    await move(hass, freezer, local(1, 12, 30))
    await start(hass)
    assert state(hass, "input_boolean.side_lights") == "on"

    await hass.services.async_call(
        "input_boolean", "turn_off", {"entity_id": "input_boolean.side_lights"}, blocking=True
    )
    # Safety ticks and other devices' transitions don't re-assert.
    await move(hass, freezer, local(1, 13, 0))
    await move(hass, freezer, local(1, 15, 0))
    assert state(hass, "input_boolean.side_lights") == "off"

    # Manually on during the off window stays on until the next window opens... then closes.
    await move(hass, freezer, local(1, 16, 30))
    await hass.services.async_call(
        "input_boolean", "turn_on", {"entity_id": "input_boolean.side_lights"}, blocking=True
    )
    await move(hass, freezer, local(1, 20, 0))
    assert state(hass, "input_boolean.side_lights") == "on"

    # Next scheduled change (on at 11:30) is honored; then off at 16:30.
    await move(hass, freezer, local(2, 11, 30))
    assert state(hass, "input_boolean.side_lights") == "on"
    await move(hass, freezer, local(2, 16, 30))
    assert state(hass, "input_boolean.side_lights") == "off"


async def test_sync_button_reasserts(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory, setup_entry: MockConfigEntry
) -> None:
    await move(hass, freezer, local(1, 12, 30))
    await start(hass)
    await hass.services.async_call(
        "input_boolean", "turn_off", {"entity_id": "input_boolean.side_lights"}, blocking=True
    )
    await hass.services.async_call(
        "button", "press", {"entity_id": "button.tower_sync_devices"}, blocking=True
    )
    assert state(hass, "input_boolean.side_lights") == "on"


async def test_schedule_control_off_leaves_devices_alone(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory, setup_entry: MockConfigEntry
) -> None:
    await move(hass, freezer, local(1, 10, 0))
    await hass.services.async_call(
        "switch", "turn_off", {"entity_id": "switch.tower_schedule_control"}, blocking=True
    )
    await start(hass)
    await move(hass, freezer, local(1, 11, 30))
    assert state(hass, "input_boolean.side_lights") == "off"
    assert state(hass, "binary_sensor.tower_side_lights_scheduled") == "on"

    await hass.services.async_call(
        "switch", "turn_on", {"entity_id": "switch.tower_schedule_control"}, blocking=True
    )
    assert state(hass, "input_boolean.side_lights") == "on"


async def test_stage_navigation(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory, setup_entry: MockConfigEntry
) -> None:
    await move(hass, freezer, local(1, 12, 30))
    await start(hass)
    await move(hass, freezer, local(4, 12, 30))
    assert state(hass, "sensor.tower_stage_day") == "4"

    await hass.services.async_call(
        "button", "press", {"entity_id": "button.tower_next_stage"}, blocking=True
    )
    await hass.async_block_till_done()
    assert state(hass, "select.tower_stage") == "2. Seedling"
    assert state(hass, "sensor.tower_stage_day") == "1"
    assert state(hass, "sensor.tower_grow_day") == "4"
    assert state(hass, "sensor.tower_target_ec") == "1.2"
    assert state(hass, "input_boolean.center_lights") == "on"
    assert state(hass, "input_boolean.side_lights") == "off"
    # Pump is unmanaged in stage 2.
    assert state(hass, "binary_sensor.tower_water_pump_scheduled") == "unknown"

    with pytest.raises(ServiceValidationError):
        await hass.services.async_call(
            "button", "press", {"entity_id": "button.tower_next_stage"}, blocking=True
        )

    await hass.services.async_call(
        "select",
        "select_option",
        {"entity_id": "select.tower_stage", "option": "1. Sprouting"},
        blocking=True,
    )
    assert state(hass, "sensor.tower_current_stage") == "Sprouting"


async def test_auto_advance(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory, setup_entry: MockConfigEntry
) -> None:
    hass.config_entries.async_update_entry(
        setup_entry, options={**setup_entry.options, "auto_advance": True}
    )
    await hass.async_block_till_done()
    await move(hass, freezer, local(1, 12, 30))
    await start(hass)
    await move(hass, freezer, local(7, 23, 0))
    assert state(hass, "sensor.tower_current_stage") == "Sprouting"
    await move(hass, freezer, local(8, 0, 1))
    assert state(hass, "sensor.tower_current_stage") == "Seedling"
    # The new stage starts on the day the previous one was due to end.
    assert state(hass, "sensor.tower_stage_day") == "1"


async def test_services(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory, setup_entry: MockConfigEntry
) -> None:
    await move(hass, freezer, local(10, 12, 30))
    await hass.services.async_call(
        DOMAIN,
        "start_grow",
        {"plan": "lettuce", "stage": "2", "start_date": "2026-09-08"},
        blocking=True,
    )
    assert state(hass, "sensor.tower_current_stage") == "Seedling"
    assert state(hass, "sensor.tower_stage_day") == "3"

    with pytest.raises(ServiceValidationError):
        await hass.services.async_call(DOMAIN, "start_grow", {"plan": "Tomato"}, blocking=True)

    await hass.services.async_call(DOMAIN, "end_grow", {}, blocking=True)
    assert state(hass, "select.tower_plan") == "none"


async def test_tasks(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory, setup_entry: MockConfigEntry
) -> None:
    await move(hass, freezer, local(1, 7, 0))
    await start(hass)
    result = await hass.services.async_call(
        "todo", "get_items", {"entity_id": "todo.tower_tasks"}, blocking=True, return_response=True
    )
    items = result["todo.tower_tasks"]["items"]
    assert [(i["summary"], i["due"]) for i in items] == [
        ("Plant seeds", "2026-09-01"),
        ("Top up", "2026-09-03"),
    ]
    assert state(hass, "sensor.tower_tasks_due") == "1"

    fired = []
    hass.bus.async_listen(f"{DOMAIN}_tasks_due", fired.append)
    await move(hass, freezer, local(1, 8, 0))
    assert fired[0].data["tasks"][0]["title"] == "Plant seeds"

    await hass.services.async_call(
        "todo",
        "update_item",
        {"entity_id": "todo.tower_tasks", "item": "Plant seeds", "status": "completed"},
        blocking=True,
    )
    assert state(hass, "sensor.tower_tasks_due") == "0"
    assert state(hass, "todo.tower_tasks") == "1"

    with pytest.raises(ServiceValidationError):
        await hass.services.async_call(
            "todo",
            "update_item",
            {"entity_id": "todo.tower_tasks", "item": "Top up", "rename": "Other"},
            blocking=True,
        )

    await hass.services.async_call(
        "todo",
        "add_item",
        {"entity_id": "todo.tower_tasks", "item": "Buy nutrients"},
        blocking=True,
    )
    await hass.services.async_call(
        "todo", "remove_item", {"entity_id": "todo.tower_tasks", "item": ["Top up"]}, blocking=True
    )
    result = await hass.services.async_call(
        "todo", "get_items", {"entity_id": "todo.tower_tasks"}, blocking=True, return_response=True
    )
    assert [i["summary"] for i in result["todo.tower_tasks"]["items"]] == [
        "Plant seeds",
        "Buy nutrients",
    ]


async def test_readings(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory, setup_entry: MockConfigEntry
) -> None:
    await move(hass, freezer, local(1, 12, 0))
    await start(hass)
    assert state(hass, "binary_sensor.tower_ph_out_of_range") == "unknown"
    assert state(hass, "binary_sensor.tower_water_reading_overdue") == "off"

    await hass.services.async_call(
        "number",
        "set_value",
        {"entity_id": "number.tower_measured_ph", "value": 6.5},
        blocking=True,
    )
    assert state(hass, "binary_sensor.tower_ph_out_of_range") == "on"
    await hass.services.async_call(DOMAIN, "log_reading", {"ph": 6.1, "ec": 0.9}, blocking=True)
    assert state(hass, "binary_sensor.tower_ph_out_of_range") == "off"
    assert state(hass, "binary_sensor.tower_ec_out_of_range") == "off"

    await move(hass, freezer, local(4, 12, 5))
    assert state(hass, "binary_sensor.tower_water_reading_overdue") == "on"


async def test_state_survives_reload(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory, setup_entry: MockConfigEntry
) -> None:
    await move(hass, freezer, local(1, 12, 30))
    await start(hass)
    assert await hass.config_entries.async_reload(setup_entry.entry_id)
    await hass.async_block_till_done()
    assert state(hass, "sensor.tower_current_stage") == "Sprouting"


async def test_removing_active_plan_ends_grow(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory, setup_entry: MockConfigEntry
) -> None:
    await move(hass, freezer, local(1, 12, 30))
    await start(hass)
    subentry_id = next(iter(setup_entry.subentries))
    hass.config_entries.async_remove_subentry(setup_entry, subentry_id)
    await hass.async_block_till_done()
    assert state(hass, "select.tower_plan") == "none"
    assert state(hass, "sensor.tower_current_stage") == "unknown"
