"""Built-in starter plans: the Elfsys Grow Cloud templates (see presets_data.py).

Preset schedules are keyed by *role* rather than by device. When a plan is
created from a preset, the user maps each role onto one of their devices.
pH (per plan) and EC (per stage) ranges come from the templates' task notes.
Light windows are the daytime versions; the Night lighting switch shifts them.
"""

from __future__ import annotations

from typing import Any

from .presets_data import PRESETS

ROLE_CENTER_LIGHTS = "center_lights"
ROLE_SIDE_LIGHTS = "side_lights"
ROLE_WATER_PUMP = "water_pump"

PRESET_ROLES: dict[str, str] = {
    ROLE_CENTER_LIGHTS: "Center lights",
    ROLE_SIDE_LIGHTS: "Side lights",
    ROLE_WATER_PUMP: "Water pump",
}


def preset_label(key: str) -> str:
    """Return a dropdown label, e.g. "Lettuce — 3 stages, 35 days"."""
    preset = PRESETS[key]
    stages = preset["stages"]
    days = sum(stage["days"] for stage in stages)
    return f"{preset['name']} — {len(stages)} stages, {days} days"


def build_from_preset(
    preset_key: str, role_map: dict[str, str | None], new_id: Any
) -> dict[str, Any]:
    """Return plan data for a preset, with roles mapped onto device ids."""
    preset = PRESETS[preset_key]
    stages = []
    for stage in preset["stages"]:
        schedules = {
            device_id: dict(stage["schedules"][role])
            for role, device_id in role_map.items()
            if device_id and role in stage["schedules"]
        }
        tasks = [{**task, "id": new_id()} for task in stage["tasks"]]
        stages.append({**stage, "id": new_id(), "schedules": schedules, "tasks": tasks})
    return {
        "name": preset["name"],
        "ph_min": preset.get("ph_min"),
        "ph_max": preset.get("ph_max"),
        "temp_min": preset.get("temp_min"),
        "temp_max": preset.get("temp_max"),
        "temp_unit": preset.get("temp_unit"),
        "humidity_min": None,
        "humidity_max": None,
        "notes": "",
        "stages": stages,
    }
