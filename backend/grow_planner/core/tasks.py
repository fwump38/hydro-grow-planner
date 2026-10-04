"""Task instances and recurrence. Pure logic, no I/O.

A `Task` in a plan is a template. A `TaskInstance` is one concrete to-do with a due
date. Recurrence is anchored to completion: checking off a recurring instance
creates the next one `every` days after the completion date, so a late check-off
pushes the next one back instead of piling up missed copies.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, timedelta

from .models import Stage, Task


@dataclass(frozen=True, slots=True)
class TaskInstance:
    """One concrete to-do. `task_id` refers to a plan Task or a custom task."""

    instance_id: str
    task_id: str
    stage_run: int
    due: date
    completed_on: date | None = None

    @property
    def done(self) -> bool:
        """Return whether the instance has been checked off."""
        return self.completed_on is not None


def due_date(stage_start: date, day: int) -> date:
    """Return the calendar date of a 1-based stage day."""
    return stage_start + timedelta(days=day - 1)


def stage_day(stage_start: date, today: date) -> int:
    """Return today's 1-based day within the stage (can exceed the stage length)."""
    return (today - stage_start).days + 1


def initial_instances(
    stage: Stage,
    stage_run: int,
    stage_start: date,
    today: date,
    new_id: Callable[[], str],
    include_past: bool = False,
) -> list[TaskInstance]:
    """Return the instances to create when a stage starts.

    Starting mid-stage backdates `stage_start`, so some task days are already past.
    One-off days in the past are skipped unless `include_past` (then they are added
    as overdue). A recurring task whose first day has passed gets its first
    instance due today.
    """
    result: list[TaskInstance] = []
    for task in stage.tasks:
        for day in task.fixed_days:
            due = due_date(stage_start, day)
            if due < today:
                if task.recurring:
                    due = today
                elif not include_past:
                    continue
            result.append(TaskInstance(new_id(), task.id, stage_run, due))
    return result


def next_instance(
    task: Task,
    completed_on: date,
    stage_run: int,
    stage_start: date,
    new_id: Callable[[], str],
) -> TaskInstance | None:
    """Return the instance a completion schedules, or None.

    Only recurring tasks continue. `until` (a stage day) ends the recurrence when
    the next due date would fall after it.
    """
    if not task.recurring:
        return None
    due = completed_on + timedelta(days=task.every)
    if task.until is not None and due > due_date(stage_start, task.until):
        return None
    return TaskInstance(new_id(), task.id, stage_run, due)


def stage_check_day(stage: Stage) -> int:
    """Return the stage day the "ready to move on?" check is due."""
    return stage.days


def is_open_due(instance: TaskInstance, today: date) -> bool:
    """Return whether an open instance is due today or overdue."""
    return not instance.done and instance.due <= today
