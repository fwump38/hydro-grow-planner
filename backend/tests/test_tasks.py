"""Tests for task recurrence."""

from __future__ import annotations

from datetime import date, timedelta
from itertools import count

import pytest

from grow_planner.core.models import Stage, Task
from grow_planner.core.tasks import (
    due_date,
    initial_instances,
    is_open_due,
    next_instance,
    stage_day,
)

START = date(2026, 9, 20)  # stage day 1


def make_ids():
    counter = count(1)
    return lambda: f"i{next(counter)}"


def task(**kwargs) -> Task:
    base = {"id": "t", "task_type": "reminder", "title": "T", "days": (1,)}
    return Task.from_dict({**base, **kwargs, "days": list(kwargs.get("days", (1,)))})


def stage(*tasks: Task, days: int = 21) -> Stage:
    return Stage(id="s", name="S", stage_type="vegetative", days=days, tasks=tuple(tasks))


def test_due_date_and_stage_day() -> None:
    assert due_date(START, 1) == START
    assert due_date(START, 4) == date(2026, 9, 23)
    assert stage_day(START, date(2026, 9, 23)) == 4


def test_recurrence_is_anchored_to_completion() -> None:
    t = task(every=3)
    # Completed three days late: the next one is 3 days after *completion*.
    nxt = next_instance(t, date(2026, 9, 26), 1, START, make_ids())
    assert nxt is not None
    assert nxt.due == date(2026, 9, 29)


def test_recurrence_continues_past_stage_length() -> None:
    t = task(every=3)
    nxt = next_instance(t, START + timedelta(days=40), 1, START, make_ids())
    assert nxt is not None  # stage is 21 days; no cutoff without `until`


def test_recurrence_stops_after_until_day() -> None:
    t = task(every=2, until=7)
    assert next_instance(t, date(2026, 9, 24), 1, START, make_ids()) is not None  # due day 7
    assert next_instance(t, date(2026, 9, 25), 1, START, make_ids()) is None  # due day 8


def test_one_off_task_does_not_repeat() -> None:
    assert next_instance(task(), START, 1, START, make_ids()) is None


def test_initial_instances_one_off_and_multi_day() -> None:
    s = stage(task(id="a", days=(1, 9)), task(id="b", days=(4,)))
    got = initial_instances(s, 1, START, START, make_ids())
    assert [(i.task_id, i.due) for i in got] == [
        ("a", date(2026, 9, 20)),
        ("a", date(2026, 9, 28)),
        ("b", date(2026, 9, 23)),
    ]


def test_recurring_task_creates_only_first_instance() -> None:
    got = initial_instances(stage(task(every=3)), 1, START, START, make_ids())
    assert len(got) == 1


@pytest.mark.parametrize(
    ("include_past", "expected"), [(False, ["late_rec"]), (True, ["old", "late_rec"])]
)
def test_starting_mid_stage(include_past: bool, expected: list[str]) -> None:
    today = START + timedelta(days=10)
    s = stage(task(id="old", days=(2,)), task(id="late_rec", days=(1,), every=3))
    got = initial_instances(s, 1, START, today, make_ids(), include_past=include_past)
    assert sorted(i.task_id for i in got) == sorted(expected)
    rec = next(i for i in got if i.task_id == "late_rec")
    assert rec.due == today  # first recurring instance is due today, not in the past


def test_is_open_due() -> None:
    inst = initial_instances(stage(task(days=(3,))), 1, START, START, make_ids())[0]
    assert not is_open_due(inst, date(2026, 9, 21))
    assert is_open_due(inst, date(2026, 9, 22))
    assert is_open_due(inst, date(2026, 9, 30))  # overdue still counts
