"""Reference for the events the app fires (shown in Settings and the README)."""

from __future__ import annotations

from typing import Any

from .const import (
    EVENT_BACK_IN_RANGE,
    EVENT_GROW_ENDED,
    EVENT_GROW_STARTED,
    EVENT_OUT_OF_RANGE,
    EVENT_STAGE_CHANGED,
)

COMMON = {"system_id": "abc123", "system": "Grow System"}
GROW = {"grow_id": "d4e5f6a7", "grow": "Layers 1+2"}

EVENTS: list[dict[str, Any]] = [
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
        "event": EVENT_STAGE_CHANGED,
        "when": "The stage changes (always by hand).",
        "example": {
            **GROW,
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
        "example": {
            **GROW,
            "plan": "Leafy Greens",
            "stage": "Sprouting",
            "stage_started": "2026-09-20",
        },
    },
    {
        "event": EVENT_GROW_ENDED,
        "when": "A grow is ended.",
        "example": {**GROW, "plan": "Leafy Greens"},
    },
]


def example_payload(event: str) -> dict[str, Any] | None:
    """Return a sample payload for an event name, or None if it is unknown."""
    for entry in EVENTS:
        if entry["event"] == event:
            return {**COMMON, **entry["example"], "test": True}
    return None
