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


def _device_ids(value: str | list[str] | None) -> list[str]:
    """Return the device ids a role is mapped to (one id or a list of them)."""
    if not value:
        return []
    return [value] if isinstance(value, str) else [d for d in value if d]


def build_from_template(
    template: dict[str, Any],
    role_map: dict[str, str | list[str] | None],
    new_id: Any,
    name: str | None = None,
) -> dict[str, Any]:
    """Return plan data for a template, with roles mapped onto device ids.

    A role can drive several devices (e.g. one plug per pair of layers); each gets
    its own copy of the role's schedule.
    """
    stages = []
    for stage in template["stages"]:
        schedules = {
            device_id: dict(stage["schedules"][role])
            for role, value in role_map.items()
            for device_id in _device_ids(value)
            if role in stage["schedules"]
        }
        tasks = [{**task, "id": new_id()} for task in stage["tasks"]]
        stages.append({**stage, "id": new_id(), "schedules": schedules, "tasks": tasks})
    return {
        "name": name or template["name"],
        "ph_min": template.get("ph_min"),
        "ph_max": template.get("ph_max"),
        "temp_min": template.get("temp_min"),
        "temp_max": template.get("temp_max"),
        "temp_unit": template.get("temp_unit"),
        "humidity_min": template.get("humidity_min"),
        "humidity_max": template.get("humidity_max"),
        "notes": template.get("notes", ""),
        "harvest_style": template.get("harvest_style", "once"),
        "stages": stages,
    }


def build_from_preset(
    preset_key: str, role_map: dict[str, str | list[str] | None], new_id: Any
) -> dict[str, Any]:
    """Return plan data for a built-in preset, with roles mapped onto device ids."""
    return build_from_template(PRESETS[preset_key], role_map, new_id)


def plan_to_template(plan: dict[str, Any], device_roles: dict[str, str]) -> dict[str, Any]:
    """Turn plan data back into a template, renaming device ids to roles.

    Devices without a role are dropped, since a template can only describe roles.
    When several devices share a role, the first one's schedule describes it.
    """
    stages = []
    for stage in plan["stages"]:
        schedules: dict[str, Any] = {}
        for device_id, schedule in stage.get("schedules", {}).items():
            if device_id in device_roles:
                schedules.setdefault(device_roles[device_id], dict(schedule))
        stages.append({**stage, "schedules": schedules})
    return {**plan, "stages": stages}
