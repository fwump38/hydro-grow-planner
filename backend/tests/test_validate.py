"""Tests for plan validation and normalisation."""

from __future__ import annotations

from itertools import count
from typing import Any

import pytest

from grow_planner.core.models import Plan, new_id
from grow_planner.core.presets import PRESETS, build_from_preset
from grow_planner.core.validate import normalize_plan


def ids():
    c = count(1)
    return lambda: f"n{next(c)}"


def stage(**kw: Any) -> dict[str, Any]:
    return {"name": "Veg", "stage_type": "vegetative", "days": 10, **kw}


def paths(errors: list[dict[str, str]]) -> set[str]:
    return {e["path"] for e in errors}


def test_valid_plan_is_normalised_and_gets_ids() -> None:
    plan, errors = normalize_plan(
        {
            "name": " Basil ",
            "ph_min": "5.8",
            "ph_max": 6.5,
            "stages": [
                stage(
                    ec_min="1.0",
                    ec_max=2,
                    schedules={
                        "d1": {"mode": "time_window", "on_time": "6:00", "off_time": "22:00"}
                    },
                    tasks=[{"title": " Feed ", "days": ["1", 4], "every": "3"}],
                )
            ],
        },
        ids(),
    )
    assert errors == []
    assert plan["name"] == "Basil" and plan["ph_min"] == 5.8 and plan["temp_unit"] == "°C"
    s = plan["stages"][0]
    assert s["id"] and s["id"] != s["tasks"][0]["id"] and s["ec_min"] == 1.0
    assert s["schedules"]["d1"] == {
        "mode": "time_window",
        "on_time": "06:00:00",
        "off_time": "22:00:00",
    }
    assert s["tasks"][0]["days"] == [1, 4] and s["tasks"][0]["every"] == 3 and s["tasks"][0]["id"]
    Plan.from_dict("p", plan)  # the model accepts it


def test_existing_ids_are_kept() -> None:
    plan, _ = normalize_plan(
        {"name": "A", "stages": [stage(id="keep", tasks=[{"id": "t", "title": "x", "days": [1]}])]},
        ids(),
    )
    assert plan["stages"][0]["id"] == "keep" and plan["stages"][0]["tasks"][0]["id"] == "t"


@pytest.mark.parametrize(
    ("data", "expected"),
    [
        ({"name": "", "stages": [stage()]}, "name"),
        ({"name": "A", "stages": []}, "stages"),
        ({"name": "A", "ph_min": 7, "ph_max": 6, "stages": [stage()]}, "ph_min"),
        ({"name": "A", "ph_max": 15, "stages": [stage()]}, "ph_max"),
        ({"name": "A", "humidity_min": -1, "stages": [stage()]}, "humidity_min"),
        ({"name": "A", "temp_unit": "K", "stages": [stage()]}, "temp_unit"),
        ({"name": "A", "ph_min": "abc", "stages": [stage()]}, "ph_min"),
        ({"name": "A", "stages": [stage(name="")]}, "stages[0].name"),
        ({"name": "A", "stages": [stage(days=0)]}, "stages[0].days"),
        ({"name": "A", "stages": [stage(days="x")]}, "stages[0].days"),
        ({"name": "A", "stages": [stage(stage_type="zzz")]}, "stages[0].stage_type"),
        ({"name": "A", "stages": [stage(ec_min=3, ec_max=1)]}, "stages[0].ec_min"),
    ],
)
def test_plan_and_stage_errors(data: dict, expected: str) -> None:
    _, errors = normalize_plan(data, ids())
    assert expected in paths(errors)


@pytest.mark.parametrize(
    ("sched", "expected"),
    [
        ({"mode": "time_window"}, "on_time"),
        ({"mode": "time_window", "on_time": "06:00", "off_time": "06:00"}, "off_time"),
        ({"mode": "time_window", "on_time": "nope", "off_time": "06:00"}, "on_time"),
        ({"mode": "interval", "interval_on": 0, "interval_every": 600}, "interval_on"),
        ({"mode": "interval", "interval_on": 600, "interval_every": 600}, "interval_on"),
        ({"mode": "interval", "interval_on": 60}, "interval_every"),
        ({"mode": "bogus"}, "mode"),
    ],
)
def test_schedule_errors(sched: dict, expected: str) -> None:
    _, errors = normalize_plan({"name": "A", "stages": [stage(schedules={"d": sched})]}, ids())
    assert f"stages[0].schedules.d.{expected}" in paths(errors)


def test_overnight_window_and_other_modes_are_fine() -> None:
    _, errors = normalize_plan(
        {
            "name": "A",
            "stages": [
                stage(
                    schedules={
                        "a": {"mode": "time_window", "on_time": "22:00", "off_time": "04:00"},
                        "b": {"mode": "always_on"},
                        "c": {"mode": "off"},
                        "d": {"mode": "manual"},
                        "e": {"mode": "interval", "interval_on": 900, "interval_every": 10800},
                    }
                )
            ],
        },
        ids(),
    )
    assert errors == []


def test_unknown_schedule_key_is_rejected_when_limited() -> None:
    data = {"name": "A", "stages": [stage(schedules={"ghost": {"mode": "off"}})]}
    assert normalize_plan(data, ids(), schedule_keys={"d1"})[1]
    assert normalize_plan(data, ids())[1] == []


@pytest.mark.parametrize(
    ("task", "expected"),
    [
        ({"title": "", "days": [1]}, "title"),
        ({"title": "x", "days": []}, "days"),
        ({"title": "x", "days": [0]}, "days"),
        ({"title": "x", "days": ["a"]}, "days"),
        ({"title": "x", "days": [1], "task_type": "zzz"}, "task_type"),
        ({"title": "x", "days": [1], "every": -2}, "every"),
        ({"title": "x", "days": [1], "until": 5}, "until"),
        ({"title": "x", "days": [4], "every": 2, "until": 3}, "until"),
    ],
)
def test_task_errors(task: dict, expected: str) -> None:
    _, errors = normalize_plan({"name": "A", "stages": [stage(tasks=[task])]}, ids())
    assert f"stages[0].tasks[0].{expected}" in paths(errors)


@pytest.mark.parametrize("key", sorted(PRESETS))
def test_every_builtin_template_validates_cleanly(key: str) -> None:
    roles = {"center_lights", "side_lights", "water_pump"}
    plan, errors = normalize_plan(
        build_from_preset(key, {r: r for r in roles}, new_id), new_id, roles
    )
    assert errors == []
    assert Plan.from_dict("p", plan).total_days == sum(s["days"] for s in PRESETS[key]["stages"])
