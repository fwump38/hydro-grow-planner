"""System upkeep tasks that belong to the grow system, not to any plan. Pure logic.

A hydroponic system needs regular upkeep whatever is growing in it: fresh water, a
clean pump, calibrated meters. These tasks repeat every N days of the system running.
The clock starts at the earliest start date of the running grows, which is backdated
when a grow was started late or its plan was changed mid-grow, and restarts each time
a task is done (checking one off schedules the next `every` days later).

The defaults suit an Elfsys-style deep flow (DFT) vertical kit: 25-40 litres of water
held across the layers (about 10 gal with four layers), so the water stays balanced for
months; a full change is for when the numbers say so, or between crops.
They are only a starting point and can be edited in the settings.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from .const import TASK_TYPES

Error = dict[str, str]
MAX_EVERY = 365

# `covers`: doing this task also does those, so their clocks restart too.
DEFAULT_MAINTENANCE: list[dict[str, Any]] = [
    {
        "id": "reservoir_change",
        "title": "Change the reservoir water",
        "task_type": "flush_refill",
        "every": 90,
        "enabled": True,
        "covers": [],
        "note": "Drain the reservoir and the grow containers and refill with fresh water and "
        "nutrients mixed to the current stage's EC, then adjust the pH. Fill to the maximum "
        "water line with the pump off, and let the levels settle before checking it.\n\n"
        "How often depends on how much water you have, since more water stays balanced "
        "longer. Growers' rule of thumb: under 2 gal weekly, 2-5 gal monthly, 5-10 gal "
        "before flowering and after harvest, and over 10 gal you can mostly top up and "
        "re-balance. The 4-layer Elfsys kit holds about 10 gal, so a full change every few "
        "months is plenty, provided you keep checking pH and EC and don't let the level "
        "drop below a quarter to a third. A 2-layer kit (about 7 gal) wants it more "
        "often: shorten the interval. Change it sooner if the pH swings or won't hold, EC "
        "keeps climbing, salt crusts form, algae appear, or the water is cloudy or smells "
        "off. Look at the roots while it is empty: white or cream is healthy, brown and "
        "slimy is root rot.",
    },
    {
        "id": "pump_clean",
        "title": "Clean the pump and drains",
        "task_type": "reminder",
        "every": 56,
        "enabled": True,
        "covers": [],
        "note": "Unplug the pump, lift it out and rinse its intake screen under warm water. "
        "Clear any roots or debris from the drains and run clean water through the tubes. "
        "Do it sooner if the grow containers fill or drain slowly, or the pump sounds "
        "strained.",
    },
    {
        "id": "calibrate_meters",
        "title": "Calibrate the pH meter",
        "task_type": "reminder",
        "every": 30,
        "enabled": True,
        "covers": [],
        "note": "Calibrate with fresh buffer solutions (pH 7 and 4 or 10). Probes drift, and a "
        "drifting meter makes you correct a problem that is not there. Keep the probe wet in "
        "storage solution, never plain water. Check the EC meter against a standard solution "
        "every few months, too.",
    },
    {
        "id": "deep_clean",
        "title": "Deep-clean the system",
        "task_type": "flush_refill",
        "every": 180,
        "enabled": True,
        "covers": ["reservoir_change", "pump_clean"],
        "note": "Every few months, and whenever you end a grow or see slime, algae or root rot. Drain everything and take "
        "the system apart as far as you can: pump, tubes, grow containers, covers and net "
        "pots. Scrub off biofilm and algae with a soft brush and a mild sanitizer (a few "
        "drops of 3 % hydrogen peroxide per litre, or diluted white vinegar for mineral "
        "scale), then rinse until nothing smells of it. Refill with fresh water and "
        "nutrients.",
    },
]


def default_maintenance() -> list[dict[str, Any]]:
    """Return a fresh copy of the default upkeep tasks."""
    return [{**task, "covers": list(task["covers"])} for task in DEFAULT_MAINTENANCE]


def task_id(maintenance_id: str) -> str:
    """Return the task id used by the instances of an upkeep task."""
    return f"maint_{maintenance_id}"


def normalize_maintenance(
    raw: list[dict[str, Any]], make_id: Callable[[], str]
) -> tuple[list[dict[str, Any]], list[Error]]:
    """Return (clean upkeep tasks, errors) for the list the settings screen sends."""
    errors: list[Error] = []
    tasks: list[dict[str, Any]] = []
    seen: set[str] = set()
    for i, item in enumerate(raw):
        title = str(item.get("title") or "").strip()
        if not title:
            errors.append({"path": f"maintenance[{i}].title", "message": "Enter a title"})
        try:
            every = int(item.get("every"))
        except (TypeError, ValueError):
            every = 0
        if not 1 <= every <= MAX_EVERY:
            errors.append(
                {"path": f"maintenance[{i}].every", "message": f"Must be 1-{MAX_EVERY} days"}
            )
            every = 14
        task_type = item.get("task_type") or "reminder"
        if task_type not in TASK_TYPES:
            task_type = "reminder"
        item_id = str(item.get("id") or "")
        if not item_id or item_id.startswith("new-") or item_id in seen:
            item_id = make_id()
        seen.add(item_id)
        tasks.append(
            {
                "id": item_id,
                "title": title,
                "task_type": task_type,
                "every": every,
                "enabled": bool(item.get("enabled", True)),
                "covers": [str(c) for c in item.get("covers") or []],
                "note": str(item.get("note") or ""),
            }
        )
    for task in tasks:
        task["covers"] = [c for c in task["covers"] if c in seen and c != task["id"]]
    return tasks, errors
