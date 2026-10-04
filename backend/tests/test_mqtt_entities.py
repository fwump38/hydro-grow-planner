"""Tests for MQTT discovery entities and command handling."""

from __future__ import annotations

from datetime import timedelta

import pytest

from grow_planner.engine import GrowError
from grow_planner.mqtt_entities import build, handle_command, slugify
from grow_planner.snapshot import snapshot

from .conftest import Harness


def by_key(configs: dict, platform: str, key: str) -> dict:
    return next(
        c
        for topic, c in configs.items()
        if topic.startswith(f"homeassistant/{platform}/") and topic.endswith(f"_{key}/config")
    )


def test_slugify() -> None:
    assert slugify("Grow System") == "grow_system"
    assert slugify("  Tower #2! ") == "tower_2"
    assert slugify("!!!") == "grow"


async def test_idle_system_publishes_unknowns_and_few_controls(h: Harness) -> None:
    configs, states = build(snapshot(h.system))
    sensor = by_key(configs, "sensor", "stage_day")
    assert states[sensor["state_topic"]] == "None"
    assert by_key(configs, "select", "active_plan")["options"] == ["none", "Leafy Greens"]
    assert not any(t.endswith("_next_stage/config") for t in configs)  # only while growing


async def test_entity_ids_follow_the_system_name(h: Harness) -> None:
    configs, _ = build(snapshot(h.system))
    assert by_key(configs, "sensor", "stage_day")["default_entity_id"] == "sensor.tower_stage_day"
    assert (
        by_key(configs, "switch", "night_lighting")["default_entity_id"]
        == "switch.tower_night_lighting"
    )
    ids = [c["unique_id"] for c in configs.values()]
    assert len(ids) == len(set(ids))


async def test_running_grow_state(h: Harness) -> None:
    await h.system.start_grow(
        "Leafy Greens", stage_ref=3, stage_started=h.system.today - timedelta(days=4)
    )
    configs, states = build(snapshot(h.system))
    value = lambda platform, key: states[by_key(configs, platform, key)["state_topic"]]  # noqa: E731
    assert value("sensor", "stage") == "Vegetative"
    assert value("sensor", "stage_day") == "5"
    assert value("select", "current_stage") == "3. Vegetative"
    assert value("binary_sensor", "device_d_pump_scheduled") == "ON"
    assert value("switch", "schedule_control") == "ON"
    assert value("sensor", "ph_min") == "5.8"
    assert by_key(configs, "button", "next_stage")["command_topic"].endswith("/next_stage/set")


async def test_ec_entities_use_the_display_unit(h: Harness) -> None:
    h.system.data["ec_unit"] = "ppm 500"
    await h.system.start_grow("Leafy Greens", stage_ref=3)
    await h.system.record_reading(ec=700)
    configs, states = build(snapshot(h.system))
    sensor = by_key(configs, "sensor", "measured_ec")
    assert sensor["unit_of_measurement"] == "ppm 500"
    assert sensor["state_class"] == "measurement"
    assert states[sensor["state_topic"]] == "700"
    number = by_key(configs, "number", "record_ec")
    assert number["mode"] == "box" and number["unit_of_measurement"] == "ppm 500"
    assert number["step"] == 10
    assert states[by_key(configs, "sensor", "ec_min")["state_topic"]] == "600"


async def test_no_record_number_when_a_sensor_provides_the_value(h: Harness) -> None:
    from grow_planner.ports import EntityState

    h.system.data["sensors"]["ph"] = "sensor.ph"
    h.system.set_state("sensor.ph", EntityState("6.2"))
    configs, states = build(snapshot(h.system))
    assert not any(t.endswith("_record_ph/config") for t in configs)
    assert any(t.endswith("_record_ec/config") for t in configs)
    assert states[by_key(configs, "sensor", "measured_ph")["state_topic"]] == "6.2"


async def test_commands(h: Harness) -> None:
    s = h.system
    await handle_command(s, "active_plan", "Leafy Greens")
    assert s.is_active
    await handle_command(s, "next_stage", "PRESS")
    assert s.active_stage.name == "Seedling"
    await handle_command(s, "current_stage", "3. Vegetative")
    assert s.active_stage.name == "Vegetative"
    await handle_command(s, "previous_stage", "PRESS")
    assert s.active_stage.name == "Seedling"
    await handle_command(s, "night_lighting", "ON")
    assert s.night_lighting
    await handle_command(s, "schedule_control", "OFF")
    assert not s.schedule_enabled
    await handle_command(s, "record_ph", "6.3")
    assert s.ph == 6.3
    await handle_command(s, "water_checked", "PRESS")
    await handle_command(s, "active_plan", "none")
    assert not s.is_active
    with pytest.raises(GrowError):
        await handle_command(s, "bogus", "")
