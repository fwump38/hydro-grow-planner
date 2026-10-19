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


async def test_idle_system_publishes_only_the_shared_entities(h: Harness) -> None:
    configs, states = build(snapshot(h.system))
    assert states[by_key(configs, "sensor", "measured_ph")["state_topic"]] == "None"
    assert not any("stage" in t for t in configs)  # grow entities exist only while a grow does


async def test_entity_ids_follow_the_system_and_grow_names(h: Harness) -> None:
    await h.start("Leafy Greens", name="Layers 1+2")
    configs, _ = build(snapshot(h.system))
    assert (
        by_key(configs, "sensor", "stage_day")["default_entity_id"]
        == "sensor.tower_layers_1_2_stage_day"
    )
    assert (
        by_key(configs, "switch", "night_lighting")["default_entity_id"]
        == "switch.tower_layers_1_2_night_lighting"
    )
    assert not any(t.endswith("_active_plan/config") for t in configs)
    ids = [c["unique_id"] for c in configs.values()]
    assert len(ids) == len(set(ids))


async def test_running_grow_state(h: Harness) -> None:
    await h.start("Leafy Greens", stage_ref=3, stage_started=h.system.today - timedelta(days=4))
    configs, states = build(snapshot(h.system))
    value = lambda platform, key: states[by_key(configs, platform, key)["state_topic"]]  # noqa: E731
    assert value("sensor", "stage") == "Vegetative"
    assert value("sensor", "stage_day") == "5"
    assert value("select", "current_stage") == "3. Vegetative"
    assert value("binary_sensor", "device_d_pump_scheduled") == "ON"
    assert value("switch", "schedule_control") == "ON"
    assert value("sensor", "ph_min") == "5.8"
    gid = h.system.grow().id
    assert by_key(configs, "button", "next_stage")["command_topic"].endswith(
        f"/grow_{gid}_next_stage/set"
    )


async def test_each_grow_gets_its_own_entities(h: Harness) -> None:
    await h.start("Leafy Greens", name="Layers 1+2", stage_ref=1)
    await h.start("Leafy Greens", name="Layers 3+4", stage_ref=3)
    configs, states = build(snapshot(h.system))
    stages = {
        c["name"]: states[c["state_topic"]]
        for t, c in configs.items()
        if t.startswith("homeassistant/sensor/") and t.endswith("_stage/config")
    }
    assert stages == {
        "Layers 1+2 current stage": "Sprouting",
        "Layers 3+4 current stage": "Vegetative",
    }
    # Water readings and tasks are shared: one set of entities.
    assert len([t for t in configs if t.endswith("_measured_ph/config")]) == 1


async def test_ec_entities_use_the_display_unit(h: Harness) -> None:
    h.system.data["ec_unit"] = "ppm 500"
    await h.start("Leafy Greens", stage_ref=3)
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
    await h.start("Leafy Greens", name="Layers 1+2")
    key = f"grow_{s.grow().id}_"
    await handle_command(s, key + "next_stage", "PRESS")
    assert s.grow().stage.name == "Seedling"
    await handle_command(s, key + "current_stage", "3. Vegetative")
    assert s.grow().stage.name == "Vegetative"
    await handle_command(s, key + "previous_stage", "PRESS")
    assert s.grow().stage.name == "Seedling"
    await handle_command(s, key + "night_lighting", "ON")
    assert s.grow().night_lighting
    await handle_command(s, key + "restart_stage", "PRESS")
    assert s.grow().stage.name == "Seedling" and s.grow().name == "Layers 1+2"
    await handle_command(s, "schedule_control", "OFF")
    assert not s.schedule_enabled
    await handle_command(s, "record_ph", "6.3")
    assert s.ph == 6.3
    await handle_command(s, "water_checked", "PRESS")
    with pytest.raises(GrowError):
        await handle_command(s, key + "active_plan", "none")  # plans are no longer switched here
    with pytest.raises(GrowError):
        await handle_command(s, "bogus", "")
