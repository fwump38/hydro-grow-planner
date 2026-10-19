"""Tests for the app wiring, with fake adapters."""

from __future__ import annotations

import asyncio
from datetime import datetime
from pathlib import Path
from typing import Any

import pytest

from grow_planner.app import App
from grow_planner.core.models import new_id
from grow_planner.core.presets import build_from_preset
from grow_planner.engine import GrowError
from grow_planner.ports import EntityState
from grow_planner.store import Store

from .conftest import TZ, FakeClock, FakeHA, FakeReadings
from .test_todo_sync import FakeTodo


class FakeMqtt:
    def __init__(self) -> None:
        self.published: list[tuple[str, dict, dict]] = []
        self.removed: list[str] = []

    def publish_system(self, system_id, configs, states) -> None:
        self.published.append((system_id, configs, states))

    def remove_system(self, system_id: str) -> None:
        self.removed.append(system_id)


class FakeConnection(FakeHA):
    def __init__(self) -> None:
        super().__init__()
        self.lists: dict[str, FakeTodo] = {}
        self.subscriptions: list[dict[str, Any]] = []

    def todo(self, entity_id: str) -> FakeTodo:
        return self.lists.setdefault(entity_id, FakeTodo())

    async def subscribe(self, payload, callback) -> None:
        self.subscriptions.append(payload)


@pytest.fixture
def app(tmp_path: Path) -> App:
    store = Store(tmp_path / "state.json", save_delay=0)
    return App(
        store,
        FakeConnection(),
        FakeReadings(),
        FakeMqtt(),
        FakeClock(datetime(2026, 9, 20, 12, tzinfo=TZ)),
    )


def configure(app: App, name: str = "Tower"):
    system = app.create_system(name)
    system.update_config(
        devices=[{"entity_id": "switch.pump", "name": "Pump", "light": False}],
        todo_entity="todo.grow",
    )
    system.data["plans"]["p"] = build_from_preset(
        "leafy_greens", {"water_pump": system.data["devices"][0]["id"]}, new_id
    )
    system._plans_cache = None
    return system


async def test_create_validates_names(app: App) -> None:
    app.create_system("Tower")
    with pytest.raises(GrowError):
        app.create_system("tower")
    with pytest.raises(GrowError):
        app.create_system("  ")


async def test_changes_publish_to_mqtt_and_the_panel_once(app: App) -> None:
    system = configure(app)
    queue = app.subscribe()
    await app.settle()
    app.mqtt.published.clear()
    while not queue.empty():
        queue.get_nowait()

    app.on_ha_state("switch.pump", EntityState("off"))
    await system.start_grow("Leafy Greens")
    await system.record_reading(ph=6.1)
    await app.settle()
    assert len(app.mqtt.published) == 1  # a burst of changes is one publish
    assert queue.get_nowait() == {"type": "changed", "system_id": system.id}


async def test_tasks_are_mirrored_to_the_todo_list(app: App) -> None:
    system = configure(app)
    app.on_ha_state("switch.pump", EntityState("off"))
    await system.start_grow("Leafy Greens", stage_ref=3)
    await app.settle()
    todo = app.ha.todo("todo.grow")
    assert "Move the grow lights" in todo.open_summaries()


async def test_state_changes_reach_systems_and_fire_alerts(app: App) -> None:
    system = configure(app)
    system.update_config(sensors={"ph": "sensor.ph"})
    app.on_ha_state("switch.pump", EntityState("off"))
    await system.start_grow("Leafy Greens")
    app.on_ha_state("sensor.ph", EntityState("7.5"))
    await asyncio.sleep(0)
    assert system.ph == 7.5
    app.clock.advance(minutes=11)
    app.on_ha_state("sensor.ph", EntityState("7.6"))
    await asyncio.sleep(0.01)
    await app.settle()
    assert [e for e in app.ha.fired("hydro_grow_planner_out_of_range")]


async def test_mqtt_command_errors_are_contained(app: App) -> None:
    system = configure(app)
    await app.on_mqtt_command(system.id, "grow_nope_next_stage", "PRESS")  # no such grow
    await app.on_mqtt_command(system.id, "record_ph", "abc")
    await app.on_mqtt_command("missing", "sync_devices", "PRESS")
    app.on_ha_state("switch.pump", EntityState("off"))
    await app.on_mqtt_command(system.id, "sync_devices", "PRESS")
    assert not system.is_active


async def test_reconnect_resyncs_and_subscribes_to_todo(app: App) -> None:
    system = configure(app)
    app.on_ha_state("switch.pump", EntityState("off"))
    await system.start_grow("Leafy Greens", stage_ref=3)  # 12:00 is inside a pump run: on
    app.on_ha_state("switch.pump", EntityState("off"))  # something turned it off meanwhile
    app.ha.calls.clear()
    await app.on_ha_connected()
    assert ("switch", "turn_on", {"entity_id": "switch.pump"}) in app.ha.calls
    assert {"type": "todo/item/subscribe", "entity_id": "todo.grow"} in app.ha.subscriptions


async def test_state_survives_a_restart(app: App, tmp_path: Path) -> None:
    system = configure(app)
    app.on_ha_state("switch.pump", EntityState("off"))
    await system.start_grow("Leafy Greens", stage_ref=2)
    await system.add_custom_task("Buy filters", every=14)
    await app.stop()

    store = Store(tmp_path / "state.json", save_delay=0)
    store.load()
    again = App(store, FakeConnection(), FakeReadings(), FakeMqtt(), app.clock)
    again.load()
    restored = next(iter(again.systems.values()))
    assert restored.grow().stage.name == "Seedling"
    assert any(t["title"] == "Buy filters" and t["every"] == 14 for t in restored.task_items())


async def test_delete_system_removes_entities(app: App) -> None:
    system = configure(app)
    app.delete_system(system.id)
    assert app.mqtt.removed == [system.id]
    assert system.id not in app.store.systems
    with pytest.raises(GrowError):
        app.get(system.id)


async def test_loops_tick_and_stop(app: App) -> None:
    system = configure(app)
    app.on_ha_state("switch.pump", EntityState("off"))
    await system.start_grow("Leafy Greens", stage_ref=3)
    app.start()
    await asyncio.sleep(0.05)
    await app.stop()
    assert app._tasks == []


async def test_update_config_validation(app: App) -> None:
    system = configure(app)
    for bad in (
        {"name": " "},
        {"ec_unit": "furlongs"},
        {"ec_unit": None},
        {"reading_interval_days": 0},
        {"reminder_time": "soon"},
        {"todo_entity": "light.x"},
        {"devices": [{"entity_id": "nope"}]},
        {"bogus": 1},
    ):
        with pytest.raises(GrowError):
            system.update_config(**bad)
    assert system.name == "Tower" and system.ec_unit == "mS/cm"
    system.update_config(ec_unit="ppm 700", reminder_time="07:30:00", reading_interval_days=5)
    assert system.ec_unit == "ppm 700"


async def test_devices_added_later_already_know_their_state(app: App) -> None:
    # The entity's state arrived (e.g. at connect) before any system used it.
    app.on_ha_state("switch.late", EntityState("on", None, "Late"))
    app.on_ha_state("sensor.late_temp", EntityState("20", "°C", "Late temp"))
    system = app.create_system("Tower")
    system.update_config(
        devices=[{"entity_id": "switch.late", "name": "Late"}],
        sensors={"temperature": "sensor.late_temp"},
    )
    assert system.actual(system.devices[0]) is True
    assert system.data["sensors"]["temperature"] == "sensor.late_temp"
    system._plans_cache = None
    assert system.states["sensor.late_temp"].state == "20"


async def test_repeated_identical_states_do_not_notify_anyone(app: App) -> None:
    system = configure(app)
    system.update_config(sensors={"temperature": "sensor.room_temp"})
    app.on_ha_state("sensor.room_temp", EntityState("21", "°C", "Room"))
    await app.settle()
    app.mqtt.published.clear()
    queue = app.subscribe()

    for _ in range(5):  # HA re-sends the same state when only an attribute changed
        app.on_ha_state("sensor.room_temp", EntityState("21", "°C", "Room"))
    await app.settle()
    assert app.mqtt.published == [] and queue.empty()

    app.on_ha_state("sensor.room_temp", EntityState("22", "°C", "Room"))  # a real change
    await app.settle()
    assert len(app.mqtt.published) == 1 and not queue.empty()
