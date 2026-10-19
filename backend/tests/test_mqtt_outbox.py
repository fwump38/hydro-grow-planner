"""Tests for the MQTT outbox diffing."""

from __future__ import annotations

from grow_planner.mqtt import Outbox, parse_command_topic
from grow_planner.mqtt_entities import build
from grow_planner.ports import EntityState
from grow_planner.snapshot import snapshot

from .conftest import Harness


def test_parse_command_topic() -> None:
    assert parse_command_topic("hydro_grow_planner/sys1/next_stage/set") == ("sys1", "next_stage")
    assert parse_command_topic("hydro_grow_planner/sys1/next_stage/state") is None
    assert parse_command_topic("other/sys1/x/set") is None
    assert parse_command_topic("hydro_grow_planner/sys1/set") is None


async def test_only_changes_are_sent(h: Harness) -> None:
    outbox = Outbox()
    first = outbox.update("sys1", *build(snapshot(h.system)))
    assert first
    assert outbox.update("sys1", *build(snapshot(h.system))) == []  # nothing changed

    await h.start("Leafy Greens")
    changed = outbox.update("sys1", *build(snapshot(h.system)))
    topics = {t for t, _, _ in changed}
    assert any(t.endswith("_stage/state") for t in topics)
    assert any(t.endswith("_next_stage/config") for t in topics)  # appears with the grow
    assert not any(t.endswith("_measured_ph/config") for t in topics)  # unchanged: not resent


async def test_removed_entities_are_cleared(h: Harness) -> None:
    outbox = Outbox()
    outbox.update("sys1", *build(snapshot(h.system)))
    assert any("record_ph" in t for t, _, _ in outbox.everything())

    h.system.data["sensors"]["ph"] = "sensor.ph"
    h.system.set_state("sensor.ph", EntityState("6.2"))
    changed = outbox.update("sys1", *build(snapshot(h.system)))
    assert any(t.endswith("_record_ph/config") and p == "" and r for t, p, r in changed)
    assert not any("record_ph" in t for t, _, _ in outbox.everything())


async def test_unit_change_republishes_discovery(h: Harness) -> None:
    outbox = Outbox()
    outbox.update("sys1", *build(snapshot(h.system)))
    h.system.data["ec_unit"] = "ppm 500"
    changed = outbox.update("sys1", *build(snapshot(h.system)))
    assert any(t.endswith("_measured_ec/config") for t, _, _ in changed)


async def test_remove_system_and_resend_everything(h: Harness) -> None:
    outbox = Outbox()
    outbox.update("sys1", *build(snapshot(h.system)))
    everything = outbox.everything()
    configs = [m for m in everything if m[0].endswith("/config")]
    assert everything[: len(configs)] == configs  # discovery before state
    removal = outbox.remove_system("sys1")
    assert removal and all(p == "" for _, p, _ in removal)
    assert outbox.everything() == []
