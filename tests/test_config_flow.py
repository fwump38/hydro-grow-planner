"""Tests for the config, options and plan subentry flows."""

from __future__ import annotations

from typing import Any

from homeassistant.config_entries import SOURCE_RECONFIGURE, SOURCE_USER
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.hydro_grow_planner.const import DOMAIN, SUBENTRY_TYPE_PLAN


async def test_user_flow(hass: HomeAssistant, devices: None) -> None:
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})
    assert result["type"] is FlowResultType.FORM
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {"name": "Tower", "devices": ["input_boolean.side_lights", "input_boolean.water_pump"]},
    )
    assert result["step_id"] == "device_names"
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {"input_boolean.side_lights": "Side lights", "input_boolean.water_pump": " Pump "},
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "Tower"
    devices_ = result["data"]["devices"]
    assert [d["name"] for d in devices_] == ["Side lights", "Pump"]
    # Lights are pre-selected from the entity/name; the pump isn't.
    assert [d["light"] for d in devices_] == [True, False]
    assert all(d["id"] for d in devices_)
    assert result["options"]["reminder_time"] == "08:00:00"


async def test_user_flow_requires_devices(hass: HomeAssistant) -> None:
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"name": "Tower", "devices": []}
    )
    assert result["errors"] == {"devices": "no_devices"}


async def _plan_flow(hass: HomeAssistant, entry: MockConfigEntry) -> dict[str, Any]:
    return await hass.config_entries.subentries.async_init(
        (entry.entry_id, SUBENTRY_TYPE_PLAN), context={"source": SOURCE_USER}
    )


async def _configure(hass: HomeAssistant, flow_id: str, data: dict[str, Any]) -> dict[str, Any]:
    return await hass.config_entries.subentries.async_configure(flow_id, data)


async def test_create_plan_from_preset(hass: HomeAssistant, setup_entry: MockConfigEntry) -> None:
    result = await _plan_flow(hass, setup_entry)
    result = await _configure(hass, result["flow_id"], {"name": "Lettuce", "preset": "lettuce"})
    assert result["errors"] == {"name": "name_taken"}

    result = await _configure(hass, result["flow_id"], {"name": "Butterhead", "preset": "lettuce"})
    assert result["step_id"] == "map_roles"
    # Roles are pre-matched to devices by name.
    defaults = {
        str(key): key.default() for key in result["data_schema"].schema if hasattr(key, "default")
    }
    assert defaults == {
        "center_lights": "dev_center",
        "side_lights": "dev_side",
        "water_pump": "dev_pump",
    }
    result = await _configure(hass, result["flow_id"], defaults)
    assert result["type"] is FlowResultType.MENU
    assert "Sprouting" in result["description_placeholders"]["summary"]

    result = await _configure(hass, result["flow_id"], {"next_step_id": "save"})
    assert result["type"] is FlowResultType.CREATE_ENTRY
    await hass.async_block_till_done()

    plans = [s for s in setup_entry.subentries.values() if s.title == "Butterhead"]
    assert len(plans) == 1
    stages = plans[0].data["stages"]
    assert [s["name"] for s in stages] == ["Sprouting", "Seedling", "Vegetative"]
    # Elfsys tasks come along, with day 0 shifted to day 1.
    first = stages[0]["tasks"][0]
    assert first["days"] == [1]
    assert plans[0].data["ph_min"] == 6.0
    assert plans[0].data["ph_max"] == 7.0
    assert stages[0]["ec_min"] == 0.3
    # Recurring tasks are merged: misting every day of Sprouting.
    mist = next(t for t in stages[0]["tasks"] if t["title"] == "Spray water on the clay pebbles")
    assert (mist["days"], mist["every"], mist["until"]) == ([1], 1, 7)
    assert first["title"] == "Add water and nutrients"
    assert "6.9 gallons" in first["note"]
    assert len({t["id"] for s in stages for t in s["tasks"]}) == sum(
        len(s["tasks"]) for s in stages
    )
    assert stages[0]["schedules"]["dev_side"] == {
        "mode": "time_window",
        "on_time": "11:30:00",
        "off_time": "16:30:00",
    }
    # Plan select picks up the new plan after the reload.
    state = hass.states.get("select.tower_plan")
    assert "Butterhead" in state.attributes["options"]


async def test_create_blank_plan_with_stage(
    hass: HomeAssistant, setup_entry: MockConfigEntry
) -> None:
    result = await _plan_flow(hass, setup_entry)
    result = await _configure(hass, result["flow_id"], {"name": "Basil", "preset": "blank"})
    assert result["menu_options"] == ["details", "add_stage", "save"]

    # Saving an empty plan is refused.
    result = await _configure(hass, result["flow_id"], {"next_step_id": "save"})
    assert result["type"] is FlowResultType.MENU

    result = await _configure(hass, result["flow_id"], {"next_step_id": "add_stage"})
    result = await _configure(
        hass,
        result["flow_id"],
        {"name": "Grow", "stage_type": "vegetative", "days": 30, "ec_min": 1.2, "ec_max": 1.4},
    )
    # One schedule form per device.
    assert result["step_id"] == "stage_schedule"
    assert result["description_placeholders"]["device"] == "Side lights"
    result = await _configure(
        hass, result["flow_id"], {"mode": "time_window", "on_time": "06:00:00"}
    )
    assert result["errors"] == {"base": "window_required"}
    result = await _configure(
        hass,
        result["flow_id"],
        {"mode": "time_window", "on_time": "06:00:00", "off_time": "20:00:00"},
    )
    assert result["description_placeholders"]["device"] == "Center lights"
    result = await _configure(hass, result["flow_id"], {"mode": "manual"})
    result = await _configure(
        hass,
        result["flow_id"],
        {
            "mode": "interval",
            "interval_on": {"hours": 3},
            "interval_every": {"minutes": 30},
        },
    )
    assert result["errors"] == {"base": "interval_too_long"}
    result = await _configure(
        hass,
        result["flow_id"],
        {
            "mode": "interval",
            "interval_on": {"minutes": 10},
            "interval_every": {"hours": 2},
        },
    )
    assert result["type"] is FlowResultType.MENU
    result = await _configure(hass, result["flow_id"], {"next_step_id": "save"})
    assert result["type"] is FlowResultType.CREATE_ENTRY
    stage = result["data"]["stages"][0]
    assert stage["days"] == 30
    assert stage["schedules"] == {
        "dev_side": {"mode": "time_window", "on_time": "06:00:00", "off_time": "20:00:00"},
        "dev_center": {"mode": "manual"},
        "dev_pump": {"mode": "interval", "interval_on": 600, "interval_every": 7200},
    }


async def test_reconfigure_plan(hass: HomeAssistant, setup_entry: MockConfigEntry) -> None:
    subentry_id = next(iter(setup_entry.subentries))
    result = await hass.config_entries.subentries.async_init(
        (setup_entry.entry_id, SUBENTRY_TYPE_PLAN),
        context={"source": SOURCE_RECONFIGURE, "subentry_id": subentry_id},
    )
    assert result["type"] is FlowResultType.MENU
    flow_id = result["flow_id"]

    # Add a task to stage 2.
    result = await _configure(hass, flow_id, {"next_step_id": "tasks"})
    result = await _configure(hass, flow_id, {"next_step_id": "pick__s2"})
    assert result["step_id"] == "task_menu"
    result = await _configure(hass, flow_id, {"next_step_id": "add_task"})
    result = await _configure(
        hass,
        flow_id,
        {"days": "5, 9", "task_type": "trimming", "title": "Trim roots", "method": "Root prune"},
    )
    result = await _configure(hass, flow_id, {"next_step_id": "menu"})

    # Move stage 2 to the front, then remove the old stage 1.
    result = await _configure(hass, flow_id, {"next_step_id": "move_stage"})
    result = await _configure(hass, flow_id, {"next_step_id": "pick__s2"})
    assert result["step_id"] == "move_to"
    result = await _configure(hass, flow_id, {"next_step_id": "pick__1"})
    result = await _configure(hass, flow_id, {"next_step_id": "remove_stage"})
    result = await _configure(hass, flow_id, {"next_step_id": "pick__s1"})
    result = await _configure(hass, flow_id, {"next_step_id": "details"})
    result = await _configure(hass, flow_id, {"name": "Lettuce v2", "ph_min": 5.8, "ph_max": 6.4})
    result = await _configure(hass, flow_id, {"next_step_id": "save"})
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reconfigure_successful"
    await hass.async_block_till_done()

    subentry = setup_entry.subentries[subentry_id]
    assert subentry.title == "Lettuce v2"
    assert (subentry.data["ph_min"], subentry.data["ph_max"]) == (5.8, 6.4)
    assert [s["id"] for s in subentry.data["stages"]] == ["s2"]
    assert subentry.data["stages"][0]["tasks"][0]["title"] == "Trim roots"
    assert subentry.data["stages"][0]["tasks"][0]["method"] == "Root prune"


async def test_pickers_have_back(hass: HomeAssistant, setup_entry: MockConfigEntry) -> None:
    """Every "choose a stage/task" step is a menu that can go back."""
    subentry_id = next(iter(setup_entry.subentries))
    result = await hass.config_entries.subentries.async_init(
        (setup_entry.entry_id, SUBENTRY_TYPE_PLAN),
        context={"source": SOURCE_RECONFIGURE, "subentry_id": subentry_id},
    )
    flow_id = result["flow_id"]
    for step in ("edit_stage", "tasks", "move_stage", "remove_stage"):
        result = await _configure(hass, flow_id, {"next_step_id": step})
        assert result["type"] is FlowResultType.MENU
        assert result["menu_options"] == {
            "pick__s1": "1. Sprouting (7 d)",
            "pick__s2": "2. Seedling (7 d)",
            "menu": "↩ Back",
        }
        result = await _configure(hass, flow_id, {"next_step_id": "menu"})
        assert result["step_id"] == "menu"

    # Task pickers go back to the task menu.
    result = await _configure(hass, flow_id, {"next_step_id": "tasks"})
    result = await _configure(hass, flow_id, {"next_step_id": "pick__s1"})
    result = await _configure(hass, flow_id, {"next_step_id": "remove_task"})
    assert list(result["menu_options"]) == ["pick__t1", "pick__t2", "task_menu"]
    result = await _configure(hass, flow_id, {"next_step_id": "pick__t1"})
    assert result["step_id"] == "task_menu"
    assert "Plant seeds" not in result["description_placeholders"]["tasks"]
    result = await _configure(hass, flow_id, {"next_step_id": "edit_task"})
    result = await _configure(hass, flow_id, {"next_step_id": "task_menu"})
    assert result["step_id"] == "task_menu"


async def test_edit_stage_keeps_schedules_and_tasks(
    hass: HomeAssistant, setup_entry: MockConfigEntry
) -> None:
    subentry_id = next(iter(setup_entry.subentries))
    result = await hass.config_entries.subentries.async_init(
        (setup_entry.entry_id, SUBENTRY_TYPE_PLAN),
        context={"source": SOURCE_RECONFIGURE, "subentry_id": subentry_id},
    )
    flow_id = result["flow_id"]
    result = await _configure(hass, flow_id, {"next_step_id": "edit_stage"})
    result = await _configure(hass, flow_id, {"next_step_id": "pick__s1"})
    result = await _configure(
        hass, flow_id, {"name": "Sprouting", "stage_type": "sprouting", "days": 10}
    )
    # Existing schedule is pre-filled; accept each device's suggested values.
    for _ in range(3):
        assert result["step_id"] == "stage_schedule"
        suggested = {
            str(key): key.description["suggested_value"]
            for key in result["data_schema"].schema
            if key.description and "suggested_value" in key.description
        }
        result = await _configure(hass, flow_id, suggested)
    result = await _configure(hass, flow_id, {"next_step_id": "save"})
    await hass.async_block_till_done()

    stage = setup_entry.subentries[subentry_id].data["stages"][0]
    assert stage["days"] == 10
    assert stage["schedules"]["dev_side"]["on_time"] == "11:30:00"
    assert stage["schedules"]["dev_pump"]["interval_every"] == 10800
    assert len(stage["tasks"]) == 2


async def test_options_add_and_remove_device(
    hass: HomeAssistant, setup_entry: MockConfigEntry
) -> None:
    hass.states.async_set("switch.fan", "off", {"friendly_name": "Tower fan"})
    result = await hass.config_entries.options.async_init(setup_entry.entry_id)
    assert result["type"] is FlowResultType.MENU
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"next_step_id": "add_devices"}
    )
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"devices": ["switch.fan", "input_boolean.side_lights"]}
    )
    assert result["step_id"] == "new_device_names"
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"switch.fan": "Fan", "lights": []}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    await hass.async_block_till_done()
    assert [d["name"] for d in setup_entry.data["devices"]][-1] == "Fan"
    assert hass.states.get("binary_sensor.tower_fan_scheduled") is not None

    result = await hass.config_entries.options.async_init(setup_entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"next_step_id": "remove_device"}
    )
    fan_id = setup_entry.data["devices"][-1]["id"]
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"devices": [fan_id]}
    )
    await hass.async_block_till_done()
    assert len(setup_entry.data["devices"]) == 3


async def test_options_settings(hass: HomeAssistant, setup_entry: MockConfigEntry) -> None:
    result = await hass.config_entries.options.async_init(setup_entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"next_step_id": "settings"}
    )
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {
            "reading_interval_days": 7,
            "reminder_time": "09:30:00",
        },
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert setup_entry.options["reminder_time"] == "09:30:00"


async def test_task_days_and_repeat(hass: HomeAssistant, setup_entry: MockConfigEntry) -> None:
    subentry_id = next(iter(setup_entry.subentries))
    result = await hass.config_entries.subentries.async_init(
        (setup_entry.entry_id, SUBENTRY_TYPE_PLAN),
        context={"source": SOURCE_RECONFIGURE, "subentry_id": subentry_id},
    )
    flow_id = result["flow_id"]
    result = await _configure(hass, flow_id, {"next_step_id": "tasks"})
    result = await _configure(hass, flow_id, {"next_step_id": "pick__s1"})
    # Existing repeat is described in the list.
    assert "Every 2 days from day 3: Top up" in result["description_placeholders"]["tasks"]
    result = await _configure(hass, flow_id, {"next_step_id": "add_task"})
    task = {"task_type": "reminder", "title": "Mist"}
    result = await _configure(hass, flow_id, {**task, "days": "one"})
    assert result["errors"] == {"base": "invalid_days"}
    result = await _configure(hass, flow_id, {**task, "days": "2", "until": 5})
    assert result["errors"] == {"base": "invalid_until"}
    result = await _configure(hass, flow_id, {**task, "days": "1", "every": 2, "until": 5})
    assert (
        "Every 2 days from day 1 until day 5: Mist" in result["description_placeholders"]["tasks"]
    )

    # Editing pre-fills days as text.
    result = await _configure(hass, flow_id, {"next_step_id": "edit_task"})
    result = await _configure(hass, flow_id, {"next_step_id": "pick__t2"})
    suggested = {
        str(k): k.description["suggested_value"]
        for k in result["data_schema"].schema
        if k.description and "suggested_value" in k.description
    }
    assert suggested["days"] == "3"
    assert suggested["every"] == 2
    assert suggested["task_type"] == "refill"
    result = await _configure(hass, flow_id, {**suggested, "days": "3, 6"})
    result = await _configure(hass, flow_id, {"next_step_id": "menu"})
    result = await _configure(hass, flow_id, {"next_step_id": "save"})
    await hass.async_block_till_done()
    tasks = {t["title"]: t for t in setup_entry.subentries[subentry_id].data["stages"][0]["tasks"]}
    assert tasks["Top up"]["days"] == [3, 6]
    assert "day" not in tasks["Top up"]
    assert (tasks["Mist"]["days"], tasks["Mist"]["every"], tasks["Mist"]["until"]) == ([1], 2, 5)


async def test_options_edit_device_light_flag(
    hass: HomeAssistant, setup_entry: MockConfigEntry
) -> None:
    result = await hass.config_entries.options.async_init(setup_entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"next_step_id": "rename_device"}
    )
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"id": "dev_pump"}
    )
    assert result["step_id"] == "device_details"
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {"name": "Pump", "entity_id": "input_boolean.water_pump", "light": True},
    )
    await hass.async_block_till_done()
    pump = next(d for d in setup_entry.data["devices"] if d["id"] == "dev_pump")
    assert pump == {
        "id": "dev_pump",
        "name": "Pump",
        "entity_id": "input_boolean.water_pump",
        "light": True,
    }


async def test_plan_climate_ranges_use_ha_units(
    hass: HomeAssistant, setup_entry: MockConfigEntry
) -> None:
    """Presets store °F; the form shows and saves Home Assistant's unit (°C in tests)."""
    result = await _plan_flow(hass, setup_entry)
    result = await _configure(hass, result["flow_id"], {"name": "Salad", "preset": "lettuce"})
    result = await _configure(
        hass,
        result["flow_id"],
        {"center_lights": "dev_center", "side_lights": "dev_side", "water_pump": "dev_pump"},
    )
    assert "Temperature 60–65 °F" in result["description_placeholders"]["summary"]
    flow_id = result["flow_id"]
    result = await _configure(hass, flow_id, {"next_step_id": "details"})
    suggested = {
        str(k): k.description["suggested_value"]
        for k in result["data_schema"].schema
        if k.description and "suggested_value" in k.description
    }
    assert (suggested["temp_min"], suggested["temp_max"]) == (15.6, 18.3)
    result = await _configure(hass, flow_id, {**suggested, "humidity_min": 80, "humidity_max": 60})
    assert result["errors"] == {"base": "humidity_range_inverted"}
    result = await _configure(
        hass, flow_id, {**suggested, "temp_max": 20, "humidity_min": 50, "humidity_max": 70}
    )
    result = await _configure(hass, flow_id, {"next_step_id": "save"})
    data = result["data"]
    assert (data["temp_min"], data["temp_max"], data["temp_unit"]) == (15.6, 20, "°C")
    assert (data["humidity_min"], data["humidity_max"]) == (50, 70)
