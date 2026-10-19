"""System upkeep tasks (water changes, cleaning, calibration) that belong to no plan."""

from __future__ import annotations

from datetime import date, timedelta

import pytest

from grow_planner.core.maintenance import default_maintenance, normalize_maintenance
from grow_planner.engine import GrowError, new_system_data
from grow_planner.mqtt_entities import build
from grow_planner.snapshot import snapshot

from .conftest import Harness

TODAY = date(2026, 9, 20)


def upkeep(h: Harness) -> dict[str, dict]:
    return {t["title"]: t for t in h.system.task_items(False) if t["maintenance"]}


def due_in(h: Harness, title: str) -> int:
    return (date.fromisoformat(upkeep(h)[title]["due"]) - TODAY).days


def test_a_new_system_gets_the_default_upkeep_tasks() -> None:
    data = new_system_data("s", "S")
    ids = [m["id"] for m in data["maintenance"]]
    assert "deep_clean" in ids and "reservoir_change" in ids
    assert all(m["enabled"] and m["every"] > 0 and len(m["note"]) > 50 for m in data["maintenance"])


async def test_nothing_is_due_while_nothing_is_growing(h: Harness) -> None:
    h.system._ensure_maintenance()
    assert upkeep(h) == {}
    assert h.system.system_day is None


async def test_upkeep_is_due_an_interval_after_the_grow_started(h: Harness) -> None:
    await h.start("Leafy Greens")
    assert h.system.system_day == 1
    assert due_in(h, "Change the reservoir water") == 90
    assert due_in(h, "Deep-clean the system") == 180
    assert upkeep(h)["Deep-clean the system"]["grow"] is None  # for the whole system


async def test_a_grow_that_started_long_ago_has_its_upkeep_due_now(h: Harness) -> None:
    long_ago = TODAY - timedelta(days=200)
    await h.start("Leafy Greens", stage_ref=3, stage_started=long_ago)
    # 14 days of earlier stages + 200 days in this one.
    assert h.system.system_started == long_ago - timedelta(days=14)
    assert h.system.system_day == 215
    assert due_in(h, "Change the reservoir water") == 0  # overdue, so due today
    assert due_in(h, "Deep-clean the system") == 0
    assert due_in(h, "Calibrate the pH meter") == 0


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


async def test_checking_off_upkeep_schedules_the_next_one_from_today(h: Harness) -> None:
    await h.start("Leafy Greens")
    h.clock.advance(days=100)
    task = upkeep(h)["Change the reservoir water"]
    assert task["overdue"]
    await h.system.complete_task(task["id"])
    next_change = next(
        t for t in h.system.task_items(False) if t["title"] == "Change the reservoir water"
    )
    assert next_change["due"] == (TODAY + timedelta(days=190)).isoformat()
    [row] = [m for m in snapshot(h.system)["maintenance"] if m["id"] == "reservoir_change"]
    assert row["last_done"] == (TODAY + timedelta(days=100)).isoformat() and row["days_since"] == 0


async def test_a_deep_clean_also_counts_as_a_water_change_and_pump_clean(h: Harness) -> None:
    await h.start("Leafy Greens")
    h.clock.advance(days=185)
    now = TODAY + timedelta(days=185)
    await h.system.complete_task(upkeep(h)["Deep-clean the system"]["id"])
    for title, days in (("Change the reservoir water", 90), ("Clean the pump and drains", 56)):
        assert upkeep(h)[title]["due"] == (now + timedelta(days=days)).isoformat()
    # ...but not the meters.
    assert (
        due_in(h, "Calibrate the pH meter") == 0
        or upkeep(h)["Calibrate the pH meter"]["due"] <= now.isoformat()
    )


async def test_upkeep_stops_repeating_once_nothing_is_growing(h: Harness) -> None:
    gid = await h.start("Leafy Greens")
    await h.system.end_grow(gid)
    # Open upkeep stays (clean up after the grow), but finishing it does not schedule more.
    task = upkeep(h)["Deep-clean the system"]
    await h.system.complete_task(task["id"])
    assert "Deep-clean the system" not in upkeep(h)
    await h.system.tick()
    assert "Deep-clean the system" not in upkeep(h)


async def test_skipping_upkeep_pushes_it_back_a_full_interval(h: Harness) -> None:
    await h.start("Leafy Greens")
    h.clock.advance(days=90)
    h.system.delete_task(upkeep(h)["Change the reservoir water"]["id"])
    assert (
        upkeep(h)["Change the reservoir water"]["due"] == (TODAY + timedelta(days=180)).isoformat()
    )


async def test_settings_can_change_disable_and_add_upkeep(h: Harness) -> None:
    await h.start("Leafy Greens")
    tasks = default_maintenance()
    for task in tasks:
        if task["id"] == "deep_clean":
            task["every"] = 21
        if task["id"] == "pump_clean":
            task["enabled"] = False
    tasks.append({"title": "Replace the air stone", "every": 90, "note": "Soft and clogged."})
    h.system.update_config(maintenance=tasks)
    assert due_in(h, "Deep-clean the system") == 180  # open instance keeps its date
    assert "Clean the pump and drains" not in upkeep(h)
    assert due_in(h, "Replace the air stone") == 90

    h.system.update_config(maintenance=[])
    assert upkeep(h) == {}


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
