"""Reference for the events the app fires (shown in Settings and the README)."""

from __future__ import annotations

from typing import Any

from .const import (
    EVENT_BACK_IN_RANGE,
    EVENT_GROW_ENDED,
    EVENT_GROW_STARTED,
    EVENT_OUT_OF_RANGE,
    EVENT_READING_OVERDUE,
    EVENT_STAGE_CHANGED,
    EVENT_STAGE_COMPLETE_DUE,
    EVENT_TASK_COMPLETED,
    EVENT_TASK_CREATED,
    EVENT_TASKS_DUE,
)

COMMON = {"system_id": "abc123", "system": "Grow System"}

EVENTS: list[dict[str, Any]] = [
    {
        "event": EVENT_TASKS_DUE,
        "when": "Once a day at the reminder time, if any tasks are due or overdue.",
        "example": {
            "plan": "Leafy Greens",
            "stage": "Vegetative",
            "count": 2,
            "tasks": [
                {
                    "title": "Add nutrients",
                    "task_type": "reminder",
                    "note": "",
                    "due": "2026-09-20",
                    "overdue": False,
                    "recurring": True,
                }
            ],
        },
    },
    {
        "event": EVENT_STAGE_COMPLETE_DUE,
        "when": "Once, when a stage reaches its planned length. The stage never changes by itself.",
        "example": {
            "plan": "Leafy Greens",
            "stage": "Sprouting",
            "next_stage": "Seedling",
            "expected_outcome": "The first true leaf appears",
        },
    },
    {
        "event": EVENT_READING_OVERDUE,
        "when": "Once, when no pH/EC reading was recorded within the reading interval.",
        "example": {"last_reading": "2026-09-17T09:00:00-06:00", "interval_days": 3},
    },
    {
        "event": EVENT_OUT_OF_RANGE,
        "when": "pH, EC, temperature or humidity stayed outside its target for 10 minutes.",
        "example": {"metric": "ph", "value": 7.4, "min": 5.8, "max": 6.5, "unit": None},
    },
    {
        "event": EVENT_BACK_IN_RANGE,
        "when": "A metric that was out of range stayed back in range for 10 minutes.",
        "example": {"metric": "ph", "value": 6.1, "min": 5.8, "max": 6.5, "unit": None},
    },
    {
        "event": EVENT_TASK_CREATED,
        "when": "A repeating or custom task gets a new occurrence.",
        "example": {"task": "Add nutrients", "due": "2026-09-23"},
    },
    {
        "event": EVENT_TASK_COMPLETED,
        "when": "A task is checked off, in the panel or in Home Assistant.",
        "example": {"task": "Add nutrients", "next_due": "2026-09-23"},
    },
    {
        "event": EVENT_STAGE_CHANGED,
        "when": "The stage changes (always by hand).",
        "example": {
            "plan": "Leafy Greens",
            "stage": "Seedling",
            "stage_number": 2,
            "stage_count": 3,
            "previous_stage": "Sprouting",
            "expected_outcome": "Roots visible",
        },
    },
    {
        "event": EVENT_GROW_STARTED,
        "when": "A grow is started.",
        "example": {"plan": "Leafy Greens", "stage": "Sprouting", "stage_started": "2026-09-20"},
    },
    {
        "event": EVENT_GROW_ENDED,
        "when": "A grow is ended.",
        "example": {"plan": "Leafy Greens"},
    },
]


def example_payload(event: str) -> dict[str, Any] | None:
    """Return a sample payload for an event name, or None if it is unknown."""
    for entry in EVENTS:
        if entry["event"] == event:
            return {**COMMON, **entry["example"], "test": True}
    return None
