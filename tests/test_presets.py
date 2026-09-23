"""Sanity checks on the bundled Elfsys templates."""

from __future__ import annotations

import pytest

from custom_components.hydro_grow_planner.const import SCHEDULE_MODES, STAGE_TYPES, TASK_TYPES
from custom_components.hydro_grow_planner.models import Plan, new_id
from custom_components.hydro_grow_planner.presets import (
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

    if key != "leafy_greens":
        assert preset["ph_min"] < preset["ph_max"]
        assert all(s["ec_min"] < s["ec_max"] for s in preset["stages"])

    role_map = {role: f"dev_{role}" for role in PRESET_ROLES}
    plan = Plan.from_dict("p", build_from_preset(key, role_map, new_id))
    assert [s.name for s in plan.stages] == [s["name"] for s in preset["stages"]]
    assert sum(len(s.tasks) for s in plan.stages) == sum(len(s["tasks"]) for s in preset["stages"])
