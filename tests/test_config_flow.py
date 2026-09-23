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
        {"name": "Grow", "stage_type": "vegetative", "days": 30, "target_ec": 1.4},
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
    result = await _configure(hass, flow_id, {"stage": "s2"})
    assert result["step_id"] == "task_menu"
    result = await _configure(hass, flow_id, {"next_step_id": "add_task"})
    result = await _configure(
        hass, flow_id, {"day": 5, "task_type": "trimming", "title": "Trim roots"}
    )
    result = await _configure(hass, flow_id, {"next_step_id": "menu"})

    # Move stage 2 to the front, then remove the old stage 1.
    result = await _configure(hass, flow_id, {"next_step_id": "move_stage"})
    result = await _configure(hass, flow_id, {"stage": "s2", "position": "1"})
    result = await _configure(hass, flow_id, {"next_step_id": "remove_stage"})
    result = await _configure(hass, flow_id, {"stage": "s1"})
    result = await _configure(hass, flow_id, {"next_step_id": "details"})
    result = await _configure(hass, flow_id, {"name": "Lettuce v2", "target_ph": 5.8})
    result = await _configure(hass, flow_id, {"next_step_id": "save"})
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reconfigure_successful"
    await hass.async_block_till_done()

    subentry = setup_entry.subentries[subentry_id]
    assert subentry.title == "Lettuce v2"
    assert subentry.data["target_ph"] == 5.8
    assert [s["id"] for s in subentry.data["stages"]] == ["s2"]
    assert subentry.data["stages"][0]["tasks"][0]["title"] == "Trim roots"


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
    result = await _configure(hass, flow_id, {"stage": "s1"})
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
        result["flow_id"], {"switch.fan": "Fan"}
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
            "ph_tolerance": 0.5,
            "ec_tolerance": 0.2,
            "reading_interval_days": 7,
            "reminder_time": "09:30:00",
            "auto_advance": True,
        },
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert setup_entry.options["auto_advance"] is True
