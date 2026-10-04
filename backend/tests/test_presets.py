"""Sanity checks on the bundled Elfsys templates."""

from __future__ import annotations

import re

import pytest

from grow_planner.core.const import SCHEDULE_MODES, STAGE_TYPES, TASK_TYPES
from grow_planner.core.models import Plan, new_id
from grow_planner.core.presets import (
    PRESET_ROLES,
    PRESETS,
    build_from_preset,
    preset_label,
)


@pytest.mark.parametrize("key", sorted(PRESETS))
def test_preset_is_valid(key: str) -> None:
    preset = PRESETS[key]
    assert preset["stages"], key
    assert preset_label(key).startswith(preset["name"])
    for stage in preset["stages"]:
        assert stage["days"] >= 1
        assert stage["stage_type"] in STAGE_TYPES
        assert set(stage["schedules"]) == set(PRESET_ROLES)
        for sched in stage["schedules"].values():
            assert sched["mode"] in SCHEDULE_MODES
        for task in stage["tasks"]:
            assert task["days"] and task["days"][0] >= 1
            assert task["every"] >= 0
            assert task["task_type"] in TASK_TYPES
            assert task["title"]

    assert preset["ph_min"] < preset["ph_max"]
    assert preset["temp_min"] < preset["temp_max"]
    assert preset["temp_unit"] == "°F"
    assert 0 <= preset["humidity_min"] < preset["humidity_max"] <= 100
    assert all(s["ec_min"] < s["ec_max"] for s in preset["stages"])
    for stage in preset["stages"]:
        for task in stage["tasks"]:
            # "(every 3 days)" in a title must be a real recurrence.
            match = re.search(r"every (\d+) days?", task["title"], re.IGNORECASE)
            if match:
                assert task["every"] == int(match.group(1)), task["title"]

    role_map = {role: f"dev_{role}" for role in PRESET_ROLES}
    plan = Plan.from_dict("p", build_from_preset(key, role_map, new_id))
    assert [s.name for s in plan.stages] == [s["name"] for s in preset["stages"]]
    assert plan.humidity_min == preset["humidity_min"]
    assert sum(len(s.tasks) for s in plan.stages) == sum(len(s["tasks"]) for s in preset["stages"])


def test_leafy_greens_vegetative_tasks_repeat() -> None:
    vegetative = PRESETS["leafy_greens"]["stages"][2]
    repeating = {t["title"]: t["every"] for t in vegetative["tasks"] if t["every"]}
    assert repeating == {
        "Move the grow lights": 3,
        "Add nutrients": 3,
        "Add water if needed": 3,
    }
