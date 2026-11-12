"""System upkeep tasks (water changes, cleaning, calibration) that belong to no plan."""

from __future__ import annotations

from datetime import date, timedelta

import pytest

from grow_planner.core.maintenance import normalize_maintenance
from grow_planner.engine import GrowError, new_system_data
from grow_planner.mqtt_entities import build
from grow_planner.snapshot import snapshot

from .conftest import Harness

TODAY = date(2026, 9, 20)


def test_a_new_system_gets_the_default_upkeep_tasks() -> None:
    data = new_system_data("s", "S")
    ids = [m["id"] for m in data["maintenance"]]
    assert "deep_clean" in ids and "reservoir_change" in ids
    assert all(m["enabled"] and m["every"] > 0 and len(m["note"]) > 50 for m in data["maintenance"])


async def test_nothing_runs_while_nothing_is_growing(h: Harness) -> None:
    assert h.system.system_day is None
    assert h.system.upkeep_anchor("deep_clean") is None
    assert all(m["next_due"] is None for m in snapshot(h.system)["maintenance"])


async def test_upkeep_counts_from_the_system_start_then_from_when_it_was_done(h: Harness) -> None:
    await h.start("Leafy Greens")
    assert h.system.upkeep_anchor("deep_clean") == TODAY
    h.clock.advance(days=100)
    done = TODAY + timedelta(days=100)
    assert h.system.upkeep_done("reservoir_change", done) is True
    assert h.system.upkeep_done("reservoir_change", done) is False  # not news the second time
    assert h.system.upkeep_done("reservoir_change", TODAY) is False  # nor is an older one
    [row] = [m for m in snapshot(h.system)["maintenance"] if m["id"] == "reservoir_change"]
    assert row["last_done"] == done.isoformat() and row["days_since"] == 0
    assert row["next_due"] == (done + timedelta(days=90)).isoformat()


async def test_a_grow_that_started_long_ago_has_its_upkeep_overdue(h: Harness) -> None:
    long_ago = TODAY - timedelta(days=200)
    await h.start("Leafy Greens", stage_ref=3, stage_started=long_ago)
    # 14 days of earlier stages + 200 days in this one.
    assert h.system.system_started == long_ago - timedelta(days=14)
    assert h.system.system_day == 215
    rows = {m["id"]: m for m in snapshot(h.system)["maintenance"]}
    for upkeep_id in ("reservoir_change", "deep_clean", "calibrate_meters"):
        assert rows[upkeep_id]["next_due"] == TODAY.isoformat()  # overdue, so due today


async def test_switching_plans_mid_grow_keeps_counting_from_the_original_start(h: Harness) -> None:
    gid = await h.start("Leafy Greens", stage_ref=3, stage_started=TODAY - timedelta(days=10))
    original = h.system.grow(gid).grow_started
    # A plan whose first stages are much shorter would otherwise give a later start.
    await h.start("Leafy Greens", replace=gid, stage_ref=1, keep_start=True)
    assert h.system.grow(gid).grow_started == original
    assert h.system.grow(gid).stage.name == "Sprouting"
    # Without keep_start the start is worked out from the new plan, as before.
    await h.start("Leafy Greens", replace=gid, stage_ref=1)
    assert h.system.grow(gid).grow_started == TODAY
    preview = h.preview("Leafy Greens", replace=gid)
    assert preview["grow_started"] == TODAY.isoformat()
    assert (
        h.preview("Leafy Greens", replace=gid, keep_start=True)["grow_started"] == TODAY.isoformat()
    )


async def test_the_system_day_runs_from_the_oldest_running_grow(h: Harness) -> None:
    older = TODAY - timedelta(days=20)
    await h.start("Leafy Greens", stage_ref=3, stage_started=older, name="A")
    started = h.system.system_started
    gid = await h.start("Leafy Greens", name="B")
    assert h.system.system_started == started
    await h.system.end_grow("A")
    assert h.system.system_started == h.system.grow(gid).grow_started == TODAY


def test_upkeep_settings_are_validated() -> None:
    tasks, errors = normalize_maintenance([{"title": "", "every": 0}], lambda: "x")
    assert {e["path"] for e in errors} == {"maintenance[0].title", "maintenance[0].every"}
    assert tasks[0]["id"] == "x"
    tasks, errors = normalize_maintenance(
        [
            {"id": "a", "title": "A", "every": 3, "covers": ["a", "b", "gone"]},
            {"id": "b", "title": "B", "every": 3},
        ],
        lambda: "x",
    )
    assert not errors and tasks[0]["covers"] == ["b"]


async def test_invalid_upkeep_leaves_settings_unchanged(h: Harness) -> None:
    before = list(h.system.data["maintenance"])
    with pytest.raises(GrowError, match="Must be 1-365"):
        h.system.update_config(maintenance=[{"title": "x", "every": 0}])
    assert h.system.data["maintenance"] == before


async def test_snapshot_and_entities_show_system_day_and_next_upkeep(h: Harness) -> None:
    snap = snapshot(h.system)
    assert snap["system_day"] is None
    await h.start("Leafy Greens", stage_ref=3, stage_started=TODAY - timedelta(days=9))
    snap = snapshot(h.system)
    assert snap["system_day"] == 24
    assert {m["id"] for m in snap["maintenance"]} >= {"deep_clean", "pump_clean"}
    configs, states = build(snap)
    by_name = {c["name"]: c for c in configs.values()}
    assert states[by_name["System day"]["state_topic"]] == "24"
    assert states[by_name["Next maintenance"]["state_topic"]] == (
        (TODAY + timedelta(days=7)).isoformat()
    )
