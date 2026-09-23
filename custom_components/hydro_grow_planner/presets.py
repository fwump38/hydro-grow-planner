"""Built-in starter plans.

Preset schedules are keyed by *role* rather than by device. When a plan is
created from a preset, the user maps each role onto one of their devices.
Targets (pH/EC), outcomes and tasks are intentionally left blank: they depend on
the crop, nutrients and water, and a wrong number would drive real alerts.
"""

from __future__ import annotations

from typing import Any

ROLE_CENTER_LIGHTS = "center_lights"
ROLE_SIDE_LIGHTS = "side_lights"
ROLE_WATER_PUMP = "water_pump"

PRESET_ROLES: dict[str, str] = {
    ROLE_CENTER_LIGHTS: "Center lights",
    ROLE_SIDE_LIGHTS: "Side lights",
    ROLE_WATER_PUMP: "Water pump",
}

_OFF = {"mode": "off"}
_PUMP = {"mode": "interval", "interval_on": 900, "interval_every": 10800}


def _window(on: str, off: str) -> dict[str, Any]:
    return {"mode": "time_window", "on_time": f"{on}:00", "off_time": f"{off}:00"}


def _stage(name: str, stage_type: str, days: int, schedules: dict[str, Any]) -> dict[str, Any]:
    return {
        "name": name,
        "stage_type": stage_type,
        "days": days,
        "outcome": "",
        "schedules": schedules,
        "tasks": [],
    }


PRESETS: dict[str, dict[str, Any]] = {
    "lettuce": {
        "name": "Lettuce",
        "stages": [
            _stage(
                "Sprouting",
                "sprouting",
                7,
                {
                    ROLE_CENTER_LIGHTS: _OFF,
                    ROLE_SIDE_LIGHTS: _window("11:30", "16:30"),
                    ROLE_WATER_PUMP: _PUMP,
                },
            ),
            _stage(
                "Seedling",
                "seedling",
                7,
                {
                    ROLE_CENTER_LIGHTS: _window("10:00", "18:00"),
                    ROLE_SIDE_LIGHTS: _OFF,
                    ROLE_WATER_PUMP: _PUMP,
                },
            ),
            _stage(
                "Vegetative",
                "vegetative",
                21,
                {
                    ROLE_CENTER_LIGHTS: _window("07:00", "21:00"),
                    ROLE_SIDE_LIGHTS: _window("07:00", "21:00"),
                    ROLE_WATER_PUMP: _PUMP,
                },
            ),
        ],
    },
    "leafy_greens": {
        "name": "Leafy Greens",
        "stages": [
            _stage(
                "Sprouting",
                "sprouting",
                7,
                {
                    ROLE_CENTER_LIGHTS: _OFF,
                    ROLE_SIDE_LIGHTS: _window("06:00", "21:00"),
                    ROLE_WATER_PUMP: _PUMP,
                },
            ),
            _stage(
                "Seedling",
                "seedling",
                7,
                {
                    ROLE_CENTER_LIGHTS: _window("06:00", "21:00"),
                    ROLE_SIDE_LIGHTS: _window("09:00", "18:00"),
                    ROLE_WATER_PUMP: _PUMP,
                },
            ),
            _stage(
                "Vegetative",
                "vegetative",
                90,
                {
                    ROLE_CENTER_LIGHTS: _window("05:00", "22:00"),
                    ROLE_SIDE_LIGHTS: _window("05:00", "22:00"),
                    ROLE_WATER_PUMP: _PUMP,
                },
            ),
        ],
    },
}


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
        stages.append({**stage, "id": new_id(), "schedules": schedules, "tasks": []})
    return {"name": preset["name"], "notes": "", "stages": stages}
