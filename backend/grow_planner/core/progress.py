"""Stage and grow progress math. Pure logic, no I/O."""

from __future__ import annotations

from datetime import date, timedelta

from .models import Plan


def day_number(started: date, today: date) -> int:
    """Return the 1-based day counted from `started`."""
    return (today - started).days + 1


def days_remaining(stage_days: int, day: int) -> int:
    """Return the days left in a stage (0 once it is overdue)."""
    return max(stage_days - day + 1, 0)


def progress_percent(stage_days: int, day: int) -> float | None:
    """Return the progress through a stage, 0-100."""
    if stage_days <= 0:
        return None
    return round(min(max(day - 1, 0) / stage_days, 1) * 100, 1)


def expected_end(plan: Plan, stage_index: int, stage_started: date) -> date:
    """Return the estimated end of the last stage."""
    return stage_started + timedelta(days=sum(s.days for s in plan.stages[stage_index:]))


def grow_start_for(plan: Plan, stage_index: int, stage_started: date) -> date:
    """Return the grow's start date implied by starting at a later stage.

    Earlier stages are assumed to have taken exactly their planned length.
    """
    return stage_started - timedelta(days=sum(s.days for s in plan.stages[:stage_index]))
