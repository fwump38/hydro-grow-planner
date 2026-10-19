"""Several grows running at once in one system (shared devices, water and room)."""

from __future__ import annotations

import copy
from datetime import date, timedelta

import pytest

from grow_planner.core.models import new_id
from grow_planner.core.presets import build_from_preset
from grow_planner.engine import GrowError, GrowSystem
from grow_planner.ports import EntityState
from grow_planner.snapshot import snapshot
from grow_planner.todo_sync import TodoSync

from .conftest import Harness
from .test_todo_sync import FakeTodo

TODAY = date(2026, 9, 20)


def two_zones(h: Harness) -> None:
    """Add a second pair of light plugs and a plan for them (the pump is shared)."""
    h.system.data["devices"] += [
        {"id": "d_center2", "name": "Center 3+4", "entity_id": "switch.center2", "light": True},
        {"id": "d_side2", "name": "Side 3+4", "entity_id": "switch.side2", "light": True},
    ]
    for entity in ("switch.center2", "switch.side2"):
        h.system.set_state(entity, EntityState("off"))
    roles = {"center_lights": "d_center2", "side_lights": "d_side2", "water_pump": "d_pump"}
    h.plans["Herbs"] = build_from_preset("leafy_greens", roles, new_id)
    h.plans["Herbs"]["name"] = "Herbs"


def edit_plan(h: Harness, grow: str, mutate=None, **changes) -> None:
    """Change a running grow's own plan, as the plan editor does."""
    plan = copy.deepcopy(h.system.grow(grow).data["plan"])
    if mutate:
        mutate(plan)
    plan.update(changes)
    h.system.set_grow_plan(grow, plan)


async def start_two(h: Harness) -> tuple[str, str]:
    two_zones(h)
    a = await h.start("Leafy Greens", name="Layers 1+2", stage_ref=3)
    b = await h.start("Herbs", name="Layers 3+4", stage_ref=1)
    return a, b


async def test_grows_run_side_by_side_and_end_independently(h: Harness) -> None:
    a, b = await start_two(h)
    assert [g.name for g in h.system.grows] == ["Layers 1+2", "Layers 3+4"]
    assert h.system.grow(a).stage.name == "Vegetative"
    assert h.system.grow(b).stage.name == "Sprouting"

    await h.system.advance_stage(b)
    assert h.system.grow(a).stage.name == "Vegetative"  # untouched
    assert h.system.grow(b).stage.name == "Seedling"

    await h.system.end_grow("Layers 1+2")
    assert [g.name for g in h.system.grows] == ["Layers 3+4"]
    assert h.system.is_active


async def test_the_grow_must_be_named_when_there_are_several(h: Harness) -> None:
    await start_two(h)
    with pytest.raises(GrowError, match="Choose which grow"):
        await h.system.advance_stage()
    with pytest.raises(GrowError, match="Unknown grow"):
        await h.system.end_grow("nope")


async def test_grow_names_are_unique_and_replacing_keeps_the_place(h: Harness) -> None:
    a, b = await start_two(h)
    with pytest.raises(GrowError, match="already a grow called"):
        await h.start("Herbs", name="layers 1+2")
    with pytest.raises(GrowError, match="already a grow called"):
        await h.system.rename_grow("Layers 1+2", b)

    await h.system.rename_grow("Salad", a)
    again = await h.start("Leafy Greens", name="Salad", replace=a)
    assert again == a and h.system.grow(a).stage.name == "Sprouting"
    assert [g.name for g in h.system.grows] == ["Salad", "Layers 3+4"]  # still the oldest


async def test_shared_pump_is_on_when_either_grow_wants_it(h: Harness) -> None:
    await start_two(h)
    pump = next(d for d in h.system.devices if d.id == "d_pump")

    # 12:00 is inside a pump run for both; make the herbs plan keep the pump off.
    def pump_off(plan):
        for stage in plan["stages"]:
            stage["schedules"]["d_pump"] = {"mode": "off"}

    edit_plan(h, "Layers 3+4", pump_off)
    assert [g.name for g, _ in h.system.drivers(pump)] == ["Layers 1+2", "Layers 3+4"]
    assert h.system.desired(pump) is True  # Layers 1+2 wants it on

    edit_plan(h, "Layers 1+2", pump_off)
    assert h.system.desired(pump) is False


async def test_an_unmanaged_device_does_not_veto_a_managed_one(h: Harness) -> None:
    await start_two(h)

    def unmanage_pump(plan):
        for stage in plan["stages"]:
            stage["schedules"].pop("d_pump")  # not managed by this grow

    edit_plan(h, "Layers 3+4", unmanage_pump)
    pump = next(d for d in h.system.devices if d.id == "d_pump")
    assert [g.name for g, _ in h.system.drivers(pump)] == ["Layers 1+2"]
    assert h.system.desired(pump) is True


async def test_each_grow_drives_only_its_own_lights(h: Harness) -> None:
    await start_two(h)
    await h.system.tick()
    snap = snapshot(h.system)
    by_id = {d["id"]: d for d in snap["devices"]}
    assert [d["grow"] for d in by_id["d_center"]["drivers"]] == ["Layers 1+2"]
    assert [d["grow"] for d in by_id["d_center2"]["drivers"]] == ["Layers 3+4"]
    assert [d["grow"] for d in by_id["d_pump"]["drivers"]] == ["Layers 1+2", "Layers 3+4"]


async def test_night_lighting_is_per_grow(h: Harness) -> None:
    a, b = await start_two(h)
    day_a = h.system.grow(a).schedule_for(h.system.devices[1])
    await h.system.set_night_lighting(True, b)
    assert h.system.grow(b).night_lighting and not h.system.grow(a).night_lighting
    assert h.system.grow(a).schedule_for(h.system.devices[1]) == day_a
    side2 = next(d for d in h.system.devices if d.id == "d_side2")
    assert h.system.grow(b).schedule_for(side2).on_time != day_a.on_time
    # Switching it off for one grow leaves the other as it was.
    await h.system.set_night_lighting(True, a)
    await h.system.set_night_lighting(False, b)
    assert h.system.grow(a).night_lighting and not h.system.grow(b).night_lighting


async def test_a_new_grow_starts_in_daylight_and_a_replacement_inherits(h: Harness) -> None:
    a, _ = await start_two(h)
    assert not h.system.grow(a).night_lighting
    await h.system.set_night_lighting(True, a)
    await h.start("Leafy Greens", name="Layers 1+2", replace=a)
    assert h.system.grow(a).night_lighting


async def test_water_targets_are_where_the_grows_overlap(h: Harness) -> None:
    await start_two(h)
    edit_plan(h, "Layers 1+2", ph_min=5.8, ph_max=6.5)
    edit_plan(h, "Layers 3+4", ph_min=6.0, ph_max=7.0)
    assert h.system.range_for("ph") == (6.0, 6.5)
    assert not h.system.range_conflict("ph")


async def test_disagreeing_targets_use_the_oldest_grow_and_say_so(h: Harness) -> None:
    await start_two(h)
    edit_plan(h, "Layers 1+2", ph_min=5.5, ph_max=5.9)
    edit_plan(h, "Layers 3+4", ph_min=6.5, ph_max=7.0)
    assert h.system.range_for("ph") == (5.5, 5.9)
    assert h.system.range_conflict("ph")
    assert snapshot(h.system)["metrics"]["ph"]["conflict"] is True


async def test_a_grow_without_a_range_does_not_loosen_the_other(h: Harness) -> None:
    await start_two(h)
    edit_plan(h, "Layers 1+2", ph_min=5.8, ph_max=6.5)
    edit_plan(h, "Layers 3+4", ph_min=None, ph_max=None)
    assert h.system.range_for("ph") == (5.8, 6.5)


async def test_tasks_say_which_grow_they_are_for(h: Harness) -> None:
    a, b = await start_two(h)
    checks = [t for t in h.system.task_items() if t["title"].startswith("Check if")]
    assert {t["grow"] for t in checks} == {"Layers 1+2", "Layers 3+4"}
    assert {t["grow_id"] for t in checks} == {a, b}

    await h.system.add_custom_task("Harvest lettuce", grow="Layers 1+2")
    await h.system.add_custom_task("Buy filters")
    custom = {t["title"]: t["grow"] for t in h.system.task_items() if t["custom"]}
    assert custom == {"Harvest lettuce": "Layers 1+2", "Buy filters": None}


async def test_completing_a_task_uses_its_own_grows_dates(h: Harness) -> None:
    a, b = await start_two(h)
    recurring = next(t for t in h.system.task_items() if t["every"] and t["grow_id"] == b)
    await h.system.complete_task(recurring["id"])
    again = [t for t in h.system.task_items(False) if t["title"] == recurring["title"]]
    assert again and again[0]["grow_id"] == b


async def test_ending_a_grow_removes_its_tasks_and_untags_custom_ones(h: Harness) -> None:
    a, b = await start_two(h)
    await h.system.add_custom_task("Harvest lettuce", grow=a)
    await h.system.end_grow(a)
    tasks = h.system.task_items()
    assert all(t["grow_id"] != a for t in tasks)
    assert any(t["grow_id"] == b for t in tasks)
    assert next(t for t in tasks if t["title"] == "Harvest lettuce")["grow"] is None


async def test_each_grow_gets_its_own_stage_prompt(h: Harness) -> None:
    from grow_planner.core.const import EVENT_STAGE_COMPLETE_DUE

    await start_two(h)
    h.clock.advance(days=8)  # past Sprouting (7 days) for Layers 3+4 only
    await h.system.tick()
    fired = h.ha.fired(EVENT_STAGE_COMPLETE_DUE)
    assert [e["grow"] for e in fired] == ["Layers 3+4"]
    assert fired[0]["stage"] == "Sprouting" and fired[0]["next_stage"] == "Seedling"


async def test_events_say_which_grow(h: Harness) -> None:
    from grow_planner.core.const import EVENT_GROW_ENDED, EVENT_GROW_STARTED, EVENT_STAGE_CHANGED

    a, _ = await start_two(h)
    assert [e["grow"] for e in h.ha.fired(EVENT_GROW_STARTED)] == ["Layers 1+2", "Layers 3+4"]
    await h.system.previous_stage(a)
    assert h.ha.fired(EVENT_STAGE_CHANGED)[-1]["grow"] == "Layers 1+2"
    await h.system.end_grow(a)
    assert h.ha.fired(EVENT_GROW_ENDED)[-1]["grow_id"] == a


async def test_preview_shows_who_else_uses_a_device(h: Harness) -> None:
    two_zones(h)
    await h.start("Leafy Greens", name="Layers 1+2", stage_ref=3)
    preview = h.preview("Herbs")
    pump = next(d for d in preview["devices"] if d["name"] == "Water pump")
    assert pump["shared_with"] == ["Layers 1+2"]
    center = next(d for d in preview["devices"] if d["name"] == "Center lights")
    assert center["shared_with"] == []  # Herbs doesn't drive the first plugs


async def test_reading_overdue_counts_from_the_earliest_grow(h: Harness) -> None:
    two_zones(h)
    await h.start("Leafy Greens", name="Old", stage_ref=3)
    h.clock.advance(days=2)
    await h.start("Herbs", name="New")
    h.clock.advance(days=1, hours=1)
    assert h.system.reading_overdue is True  # 3 days since "Old" began; "New" is a day old


async def test_todo_text_names_the_grow_only_when_there_are_several(h: Harness) -> None:
    two_zones(h)
    await h.start("Leafy Greens", name="Layers 1+2", stage_ref=3)
    todo = FakeTodo()
    sync = TodoSync(h.system, todo)
    await sync.reconcile()
    assert not any(s.startswith("Layers 1+2:") for s in todo.open_summaries())

    await h.start("Herbs", name="Layers 3+4")
    await h.system.add_custom_task("Buy filters")
    todo2 = FakeTodo()
    await TodoSync(h.system, todo2).reconcile()
    summaries = todo2.open_summaries()
    assert any(s.startswith("Layers 3+4: ") for s in summaries)
    assert any(s.startswith("Layers 1+2: ") for s in summaries)
    assert "Buy filters" in summaries


def test_a_single_grow_saved_by_an_older_version_is_migrated() -> None:
    h = Harness()
    data = h.system.data
    data["plans"] = {
        "leafy": h.plans["Leafy Greens"],
        "unused": {**h.plans["Leafy Greens"], "name": "Spare"},
    }
    legacy = {
        "plan_id": "leafy",
        "stage_id": h.plans["Leafy Greens"]["stages"][1]["id"],
        "stage_started": TODAY.isoformat(),
        "grow_started": (TODAY - timedelta(days=7)).isoformat(),
        "stage_run": 2,
        "stage_check_notified": False,
        "night_lighting": True,
        "history": [],
        "instances": [
            {
                "id": "i1",
                "task_id": "stage_check",
                "stage_run": 2,
                "due": "2026-09-27",
                "completed_on": None,
                "custom": False,
            },
            {
                "id": "i2",
                "task_id": "custom_x",
                "stage_run": 0,
                "due": "2026-09-21",
                "completed_on": None,
                "custom": True,
            },
        ],
        "custom_tasks": {"custom_x": {"title": "Mine", "note": "", "every": 0}},
    }
    data["runtime"] = legacy
    system = GrowSystem(data, h.ha, h.clock, h.readings)
    [grow] = system.grows
    assert grow.name == "Leafy Greens" and grow.stage.name == "Seedling"
    assert grow.night_lighting and grow.grow_started == TODAY - timedelta(days=7)
    items = {t["id"]: t for t in system.task_items()}
    assert items["i1"]["grow"] == "Leafy Greens"
    assert items["i2"]["grow"] is None
    assert not any(k in system.rt for k in ("plan_id", "stage_id", "night_lighting", "history"))
    # The grow now holds its own plan; the plan nobody runs is left to become a template.
    assert grow.data["plan"]["name"] == "Leafy Greens" and "plan_id" not in grow.data
    assert list(system.take_unused_plans()) == ["unused"] and "plans" not in system.data


def test_a_legacy_grow_whose_plan_is_gone_is_dropped() -> None:
    h = Harness()
    data = h.system.data
    data["runtime"] = {
        "plan_id": "gone",
        "stage_id": "x",
        "instances": [
            {"id": "i1", "task_id": "t", "stage_run": 1, "due": "2026-09-27", "custom": False}
        ],
    }
    system = GrowSystem(data, h.ha, h.clock, h.readings)
    assert system.grows == [] and system.rt["instances"] == []
