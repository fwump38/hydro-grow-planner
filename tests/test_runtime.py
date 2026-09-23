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
    assert state(hass, "sensor.tower_ec_max") == "1.4"
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


async def test_stages_never_advance_on_their_own(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory, setup_entry: MockConfigEntry
) -> None:
    """Past its estimated days a stage stays put; a check task prompts the decision."""
    await move(hass, freezer, local(1, 12, 30))
    await start(hass)
    for day in range(2, 31):
        await move(hass, freezer, local(day, 0, 1))
    assert state(hass, "sensor.tower_current_stage") == "Sprouting"
    assert state(hass, "sensor.tower_stage_day") == "30"
    assert state(hass, "sensor.tower_stage_days_remaining") == "0"

    result = await hass.services.async_call(
        "todo", "get_items", {"entity_id": "todo.tower_tasks"}, blocking=True, return_response=True
    )
    check = next(
        i for i in result["todo.tower_tasks"]["items"] if i["summary"].startswith("Check if")
    )
    assert check["summary"] == "Check if ready for Seedling"
    assert check["due"] == "2026-09-07"  # the stage's last estimated day
    assert check["description"].startswith("Expected by now: Sprouts")

    # Checking it off doesn't change the stage.
    await hass.services.async_call(
        "todo",
        "update_item",
        {"entity_id": "todo.tower_tasks", "item": check["uid"], "status": "completed"},
        blocking=True,
    )
    assert state(hass, "sensor.tower_current_stage") == "Sprouting"


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
        # Recurring: every 2 days from day 3 to the end of the 7-day stage.
        ("Top up", "2026-09-03"),
        ("Top up", "2026-09-05"),
        ("Top up", "2026-09-07"),
        ("Check if ready for Seedling", "2026-09-07"),
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
    assert state(hass, "todo.tower_tasks") == "4"

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
    # Removing hides one occurrence; the other days stay.
    assert [(i["summary"], i.get("due")) for i in result["todo.tower_tasks"]["items"]] == [
        ("Plant seeds", "2026-09-01"),
        ("Top up", "2026-09-05"),
        ("Top up", "2026-09-07"),
        ("Check if ready for Seedling", "2026-09-07"),
        ("Buy nutrients", None),
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


async def test_previous_stage_undoes_advance(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory, setup_entry: MockConfigEntry
) -> None:
    """Going back right after advancing restores the stage as it was."""
    await move(hass, freezer, local(1, 12, 30))
    await start(hass)
    await hass.services.async_call(
        "todo",
        "update_item",
        {"entity_id": "todo.tower_tasks", "item": "Plant seeds", "status": "completed"},
        blocking=True,
    )
    await move(hass, freezer, local(4, 12, 30))
    await hass.services.async_call(
        "button", "press", {"entity_id": "button.tower_next_stage"}, blocking=True
    )
    assert state(hass, "sensor.tower_current_stage") == "Seedling"

    await hass.services.async_call(DOMAIN, "previous_stage", {}, blocking=True)
    assert state(hass, "sensor.tower_current_stage") == "Sprouting"
    # Original start date and checked-off tasks are back.
    assert state(hass, "sensor.tower_stage_day") == "4"
    result = await hass.services.async_call(
        "todo", "get_items", {"entity_id": "todo.tower_tasks"}, blocking=True, return_response=True
    )
    done = [i["summary"] for i in result["todo.tower_tasks"]["items"] if i["status"] == "completed"]
    assert done == ["Plant seeds"]

    await move(hass, freezer, local(9, 0, 1))
    assert state(hass, "sensor.tower_current_stage") == "Sprouting"

    # With no history left, going back from the first stage is refused.
    with pytest.raises(ServiceValidationError):
        await hass.services.async_call(DOMAIN, "previous_stage", {}, blocking=True)

    # Advancing manually, then picking the stage again in the select also undoes.
    await hass.services.async_call(
        "button", "press", {"entity_id": "button.tower_next_stage"}, blocking=True
    )
    await hass.services.async_call(
        "select",
        "select_option",
        {"entity_id": "select.tower_stage", "option": "1. Sprouting"},
        blocking=True,
    )
    assert state(hass, "sensor.tower_stage_day") == "9"


async def test_previous_stage_without_history_starts_today(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory, setup_entry: MockConfigEntry
) -> None:
    await move(hass, freezer, local(5, 12, 0))
    await hass.services.async_call(
        DOMAIN, "start_grow", {"plan": "Lettuce", "stage": "2"}, blocking=True
    )
    await hass.services.async_call(DOMAIN, "previous_stage", {}, blocking=True)
    assert state(hass, "sensor.tower_current_stage") == "Sprouting"
    assert state(hass, "sensor.tower_stage_day") == "1"


async def test_night_lighting(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory, setup_entry: MockConfigEntry
) -> None:
    """Night lighting shifts light windows 12 h; the pump is untouched."""
    await move(hass, freezer, local(1, 12, 30))
    await start(hass)
    assert state(hass, "input_boolean.side_lights") == "on"

    await hass.services.async_call(
        "switch", "turn_on", {"entity_id": "switch.tower_night_lighting"}, blocking=True
    )
    assert state(hass, "input_boolean.side_lights") == "off"
    side = hass.states.get("binary_sensor.tower_side_lights_scheduled")
    assert side.attributes["schedule"] == "23:30–04:30"
    pump = hass.states.get("binary_sensor.tower_water_pump_scheduled")
    assert pump.attributes["schedule"] == "15 min every 3 h"

    await move(hass, freezer, local(1, 23, 30))
    assert state(hass, "input_boolean.side_lights") == "on"
    await move(hass, freezer, local(2, 4, 30))
    assert state(hass, "input_boolean.side_lights") == "off"


@pytest.mark.parametrize(
    "plan_data",
    [
        {
            # Format saved by v0.1.0: single targets and single-day tasks.
            "name": "Lettuce",
            "target_ph": 6.0,
            "notes": "",
            "stages": [
                {
                    "id": "s1",
                    "name": "Sprouting",
                    "stage_type": "sprouting",
                    "days": 7,
                    "target_ec": 0.8,
                    "schedules": {},
                    "tasks": [
                        {"id": "t1", "day": 2, "task_type": "top_up", "title": "Top up", "note": ""}
                    ],
                }
            ],
        }
    ],
)
async def test_legacy_plan_format(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory, setup_entry: MockConfigEntry
) -> None:
    await move(hass, freezer, local(1, 12, 0))
    await start(hass)
    assert state(hass, "sensor.tower_ph_min") == "5.7"
    assert state(hass, "sensor.tower_ph_max") == "6.3"
    assert state(hass, "sensor.tower_ec_min") == "0.5"
    result = await hass.services.async_call(
        "todo", "get_items", {"entity_id": "todo.tower_tasks"}, blocking=True, return_response=True
    )
    assert [(i["summary"], i["due"]) for i in result["todo.tower_tasks"]["items"]] == [
        ("Top up", "2026-09-02"),
        ("Check if ready to finish the grow", "2026-09-07"),
    ]


async def test_climate_ranges(
    hass: HomeAssistant,
    freezer: FrozenDateTimeFactory,
    devices: None,
    mock_entry: MockConfigEntry,
    plan_data: dict,
) -> None:
    """Room temperature/humidity are checked against the plan, across units."""
    hass.states.async_set(
        "sensor.room_temp", "75", {"unit_of_measurement": "°F", "device_class": "temperature"}
    )
    hass.states.async_set("sensor.room_humidity", "55", {"unit_of_measurement": "%"})
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Tower",
        data={
            **mock_entry.data,
            "temperature_sensor": "sensor.room_temp",
            "humidity_sensor": "sensor.room_humidity",
        },
        options=mock_entry.options,
        subentries_data=[
            {
                "data": {
                    **plan_data,
                    "temp_min": 16,
                    "temp_max": 24,
                    "temp_unit": "°C",
                    "humidity_min": 50,
                    "humidity_max": 70,
                },
                "subentry_type": "plan",
                "title": "Lettuce",
                "unique_id": None,
            }
        ],
    )
    freezer.move_to(local(1, 12, 0))
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    # No grow running: no range to compare against.
    assert state(hass, "binary_sensor.tower_temperature_out_of_range") == "unknown"
    await start(hass)
    # 75 °F is 23.9 °C: inside 16–24 °C.
    temp = hass.states.get("binary_sensor.tower_temperature_out_of_range")
    assert temp.state == "off"
    assert temp.attributes["value"] == 23.9
    assert state(hass, "binary_sensor.tower_humidity_out_of_range") == "off"

    hass.states.async_set(
        "sensor.room_temp", "80", {"unit_of_measurement": "°F", "device_class": "temperature"}
    )
    hass.states.async_set("sensor.room_humidity", "82", {"unit_of_measurement": "%"})
    await hass.async_block_till_done()
    assert state(hass, "binary_sensor.tower_temperature_out_of_range") == "on"
    assert state(hass, "binary_sensor.tower_humidity_out_of_range") == "on"


async def test_no_climate_entities_without_sensors(
    hass: HomeAssistant, setup_entry: MockConfigEntry
) -> None:
    assert hass.states.get("binary_sensor.tower_temperature_out_of_range") is None
    assert hass.states.get("binary_sensor.tower_humidity_out_of_range") is None
