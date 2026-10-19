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
        "Harvest outer leaves": 5,
    }


@pytest.mark.parametrize("key", sorted(PRESETS))
def test_pump_runs_15_minutes_every_3_hours_in_every_stage(key: str) -> None:
    # Every built-in stage uses this cycle; an always-on pump is a data error.
    for stage in PRESETS[key]["stages"]:
        pump = stage["schedules"]["water_pump"]
        assert pump == {"mode": "interval", "interval_on": 900, "interval_every": 10800}, (
            key,
            stage["name"],
        )


def test_leafy_greens_lights_follow_the_lettuce_and_spinach_pattern() -> None:
    # The source's generic template had 15 h of side light while sprouting, both lights
    # in Seedling and 17 h in Vegetative. It now matches the other leafy templates.
    lights = lambda key: [  # noqa: E731
        (s["name"], s["schedules"]["center_lights"], s["schedules"]["side_lights"])
        for s in PRESETS[key]["stages"]
    ]
    assert lights("leafy_greens") == lights("lettuce")[:3]  # Lettuce adds a Harvest stage
    sprouting, seedling, vegetative = PRESETS["leafy_greens"]["stages"]
    assert sprouting["schedules"]["center_lights"]["mode"] == "off"
    assert seedling["schedules"]["side_lights"]["mode"] == "off"
    assert vegetative["schedules"]["center_lights"]["on_time"] == "07:00:00"
    assert vegetative["schedules"]["center_lights"]["off_time"] == "21:00:00"


def test_leafy_greens_humidity_is_wide_enough_for_herbs() -> None:
    leafy = PRESETS["leafy_greens"]
    assert (leafy["humidity_min"], leafy["humidity_max"]) == (40.0, 70.0)
    # The leafy-vegetable templates keep the tighter 50-70 % range.
    assert (PRESETS["lettuce"]["humidity_min"], PRESETS["lettuce"]["humidity_max"]) == (50.0, 70.0)


def test_mixed_herbs_is_leafy_greens_tuned_for_a_shared_herb_reservoir() -> None:
    herbs, leafy = PRESETS["mixed_herbs"], PRESETS["leafy_greens"]
    assert herbs["name"] == "Mixed Herbs"
    # pH sits where basil (<= 6.5) and cilantro/alliums/bok choy (>= 6.0) overlap.
    assert (herbs["ph_min"], herbs["ph_max"]) == (6.0, 6.5)
    assert [s["name"] for s in herbs["stages"]] == [s["name"] for s in leafy["stages"]]
    assert herbs["stages"][0]["days"] > leafy["stages"][0]["days"]  # slower to sprout
    # A copy, not an alias: editing one must not change the other.
    assert herbs["stages"][0]["tasks"] is not leafy["stages"][0]["tasks"]
    assert (leafy["ph_min"], leafy["ph_max"]) == (5.8, 6.5)
    vegetative = {t["title"]: t for t in herbs["stages"][2]["tasks"]}
    assert vegetative["Pinch and harvest herbs"]["every"] == 7
    assert vegetative["Sow cilantro again"]["until"] <= herbs["stages"][2]["days"]


def test_a_role_can_drive_several_devices() -> None:
    role_map = {
        "center_lights": ["plug_a", "plug_b"],
        "side_lights": "plug_c",
        "water_pump": [],
    }
    plan = build_from_preset("leafy_greens", role_map, new_id)
    schedules = plan["stages"][2]["schedules"]
    assert set(schedules) == {"plug_a", "plug_b", "plug_c"}
    assert schedules["plug_a"] == schedules["plug_b"]
    assert schedules["plug_a"] is not schedules["plug_b"]  # separate copies


def test_saving_a_plan_with_shared_roles_as_a_template_keeps_one_schedule_per_role() -> None:
    from grow_planner.core.presets import plan_to_template

    role_map = {"center_lights": ["plug_a", "plug_b"], "side_lights": "plug_c"}
    plan = build_from_preset("leafy_greens", role_map, new_id)
    template = plan_to_template(
        plan, {"plug_a": "center_lights", "plug_b": "center_lights", "plug_c": "side_lights"}
    )
    assert set(template["stages"][2]["schedules"]) == {"center_lights", "side_lights"}
