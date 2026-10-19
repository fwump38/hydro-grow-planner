"""Harvest style: harvest everything at once, or a little at a time while it keeps growing."""

from __future__ import annotations

from itertools import count

import pytest

from grow_planner.core.models import Plan, new_id
from grow_planner.core.presets import PRESETS, build_from_preset
from grow_planner.core.validate import normalize_plan
from grow_planner.snapshot import snapshot
from grow_planner.templates import summarize

from .conftest import Harness


def stage(name: str, stage_type: str = "other", days: int = 7, tasks: list | None = None) -> dict:
    return {"name": name, "stage_type": stage_type, "days": days, "tasks": tasks or []}


def plan_data(style: str | None, *stages: dict) -> dict:
    data = {"name": "P", "stages": list(stages)}
    if style is not None:
        data["harvest_style"] = style
    return data


def make_ids():
    counter = count(1)
    return lambda: f"id{next(counter)}"


def harvest_tasks(plan: dict) -> list[dict]:
    return [t for s in plan["stages"] for t in s["tasks"] if t["task_type"] == "harvest"]


def test_plans_harvest_once_by_default() -> None:
    plan, errors = normalize_plan(plan_data(None, stage("Grow")), make_ids())
    assert not errors and plan["harvest_style"] == "once"
    assert not Plan.from_dict("p", plan).continuous
    assert harvest_tasks(plan) == []


def test_unknown_harvest_style_is_an_error() -> None:
    _, errors = normalize_plan(plan_data("sometimes", stage("Grow")), make_ids())
    assert [e["path"] for e in errors] == ["harvest_style"]


def test_a_continuous_plan_without_a_harvest_task_gets_one_in_the_harvest_stage() -> None:
    plan, errors = normalize_plan(
        plan_data(
            "continuous", stage("Veg", "vegetative"), stage("Pick", "harvest", 30), stage("X")
        ),
        make_ids(),
    )
    assert not errors
    [task] = harvest_tasks(plan)
    assert plan["stages"][1]["tasks"] == [task]
    assert task["every"] > 0 and task["until"] == 30 and task["days"] == [1]


def test_a_continuous_plan_with_a_harvest_task_is_left_alone() -> None:
    mine = {"task_type": "harvest", "title": "Pick", "days": [3], "every": 2}
    plan, _ = normalize_plan(
        plan_data("continuous", stage("Veg", tasks=[mine]), stage("Late")), make_ids()
    )
    assert [t["title"] for t in harvest_tasks(plan)] == ["Pick"]
    assert plan["stages"][1]["tasks"] == []


def test_a_one_off_harvest_task_does_not_count_as_repeating() -> None:
    once = {"task_type": "harvest", "title": "Pick", "days": [3]}
    plan, _ = normalize_plan(plan_data("continuous", stage("Veg", tasks=[once])), make_ids())
    assert len(harvest_tasks(plan)) == 2


@pytest.mark.parametrize("key", sorted(PRESETS))
def test_every_builtin_template_says_how_it_is_harvested(key: str) -> None:
    preset = PRESETS[key]
    assert preset["harvest_style"] in ("once", "continuous")
    if preset["harvest_style"] != "continuous":
        return
    repeating = [
        (stage_["name"], t)
        for stage_ in preset["stages"]
        for t in stage_["tasks"]
        if t["task_type"] == "harvest" and t["every"] > 0
    ]
    assert repeating, f"{key} is continuous but has no repeating harvest task"
    for name, task in repeating:
        stage_ = next(s for s in preset["stages"] if s["name"] == name)
        # It says how much and from where, and ends with the stage rather than running on.
        assert task["method"] and len(task["note"]) > 80
        assert task["until"] is None or task["until"] <= stage_["days"]
        assert task["days"][0] <= stage_["days"]
    # The last stage is where the plants wear out, so it says how to tell.
    assert preset["stages"][-1]["outcome"]


def test_lettuce_is_cut_a_third_at_a_time_in_a_harvest_stage() -> None:
    lettuce = PRESETS["lettuce"]
    vegetative, harvest = lettuce["stages"][-2:]
    assert vegetative["days"] == 21 and harvest["stage_type"] == "harvest"
    [task] = [t for t in harvest["tasks"] if t["task_type"] == "harvest"]
    assert "third" in task["method"] and "hand" in task["note"] and "crown" in task["note"]
    assert task["days"] == [1] and task["until"] == harvest["days"]
    # The harvest stage keeps the pump and lights of the stage before it.
    assert harvest["schedules"] == vegetative["schedules"]
    assert Plan.from_dict("p", build_from_preset("lettuce", {}, new_id)).continuous


def test_summary_and_snapshot_carry_the_harvest_style(h: Harness) -> None:
    assert summarize("builtin:lettuce", PRESETS["lettuce"])["harvest_style"] == "continuous"
    summary = summarize(
        "custom:x", {"name": "X", "stages": [{"name": "S", "days": 1, "stage_type": "other"}]}
    )
    assert summary["harvest_style"] == "once"


async def test_a_continuous_plan_ends_by_asking_if_the_plants_are_spent(h: Harness) -> None:
    h.system.data["plans"]["leafy"]["harvest_style"] = "continuous"
    h.system.data["plans"]["leafy"]["stages"][-1]["outcome"] = "Regrowth has slowed."
    h.system.set_plan("leafy", h.system.data["plans"]["leafy"])
    await h.system.start_grow("Leafy Greens", stage_ref=3)
    check = next(t for t in h.system.task_items() if t["title"].startswith("Check if"))
    assert check["title"] == "Check if it's time to finish the grow"
    assert "Regrowth has slowed." in check["note"] and "Restart stage" in check["note"]
    assert snapshot(h.system)["grows"][0]["plan"]["harvest_style"] == "continuous"


async def test_a_single_harvest_plan_keeps_the_usual_wording(h: Harness) -> None:
    h.system.data["plans"]["leafy"]["harvest_style"] = "once"
    h.system.set_plan("leafy", h.system.data["plans"]["leafy"])
    await h.system.start_grow("Leafy Greens", stage_ref=3)
    check = next(t for t in h.system.task_items() if t["title"].startswith("Check if"))
    assert check["title"] == "Check if ready to finish the grow"
