"""Maps a system snapshot to Home Assistant MQTT discovery entities. Pure logic.

`build()` returns the discovery configs and current state payloads;
`handle_command()` applies a command an entity sent back. Neither does any I/O, so
both are tested without a broker.
"""

from __future__ import annotations

import json
import re
from typing import Any

from .core import units
from .core.const import APP_SLUG, NO_PLAN
from .engine import GrowError, GrowSystem

DISCOVERY_PREFIX = "homeassistant"
TOPIC_PREFIX = "hydro_grow_planner"
STATUS_TOPIC = f"{TOPIC_PREFIX}/status"
NONE_PAYLOAD = "None"  # HA resets sensor/binary_sensor state to unknown on this payload


def slugify(text: str) -> str:
    """Return a lowercase entity-id-safe slug."""
    return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_") or "grow"


def base_topic(system_id: str) -> str:
    """Return the topic prefix for a system."""
    return f"{TOPIC_PREFIX}/{system_id}"


def _state(value: Any) -> str:
    if value is None:
        return NONE_PAYLOAD
    if isinstance(value, bool):
        return "ON" if value else "OFF"
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value)


def _next_maintenance_due(snap: dict[str, Any]) -> str | None:
    due = [m["next_due"] for m in snap["maintenance"] if m["enabled"] and m["next_due"]]
    return min(due) if due else None


def _next_task_due(snap: dict[str, Any]) -> str | None:
    open_tasks = [t["due"] for t in snap["tasks"] if not t["done"]]
    return min(open_tasks) if open_tasks else None


def _grow_adder(add: Any, grow: dict[str, Any]) -> Any:
    """Return an `add` for one grow's entities: keys and names carry the grow."""
    gid, label = grow["id"], grow["name"]

    def gadd(platform: str, key: str, name: str, value: Any, *args: Any, **extra: Any) -> None:
        add(
            platform,
            f"grow_{gid}_{key}",
            f"{label} {name.lower()}",
            value,
            *args,
            object_id=f"{slugify(label)}_{key}",
            **extra,
        )

    return gadd


def build(snap: dict[str, Any]) -> tuple[dict[str, dict[str, Any]], dict[str, str]]:
    """Return ({config_topic: discovery_payload}, {state_topic: payload})."""
    system_id = snap["id"]
    slug = slugify(snap["name"])
    base = base_topic(system_id)
    device = {
        "identifiers": [f"{APP_SLUG}_{system_id}"],
        "name": snap["name"],
        "manufacturer": "Hydro Grow Planner",
        "model": "Grow system",
    }
    configs: dict[str, dict[str, Any]] = {}
    states: dict[str, str] = {}

    def add(
        platform: str, key: str, name: str, value: Any, commandable: bool = False, **extra: Any
    ) -> None:
        unique = f"{APP_SLUG}_{system_id}_{key}"
        object_id = extra.pop("object_id", key)
        state_topic = f"{base}/{key}/state"
        payload: dict[str, Any] = {
            "name": name,
            "unique_id": unique,
            "default_entity_id": f"{platform}.{slug}_{object_id}",
            "device": device,
            "availability_topic": STATUS_TOPIC,
            **extra,
        }
        if platform != "button":
            payload["state_topic"] = state_topic
            states[state_topic] = _state(value)
        if commandable:
            payload["command_topic"] = f"{base}/{key}/set"
        configs[f"{DISCOVERY_PREFIX}/{platform}/{unique}/config"] = payload

    metrics = snap["metrics"]
    ec_unit = snap["ec_unit"]

    # -- tasks -------------------------------------------------------------------------------
    add("sensor", "tasks_due", "Tasks due", snap["tasks_due"], icon="mdi:clipboard-list-outline")
    add("sensor", "next_task", "Next task", _next_task_due(snap), device_class="date")

    # -- the system itself: how long it has been running, and its upkeep --------------------
    add("sensor", "system_day", "System day", snap["system_day"], icon="mdi:calendar-range")
    add(
        "sensor",
        "next_maintenance",
        "Next maintenance",
        _next_maintenance_due(snap),
        device_class="date",
        icon="mdi:wrench-clock",
    )

    # -- each running grow ---------------------------------------------------------------------
    plan_names = [p["name"] for p in snap["plans"]]
    for grow in snap["grows"]:
        gadd = _grow_adder(add, grow)
        stage = grow["stage"]
        gadd(
            "sensor",
            "plan",
            "Plan",
            grow["plan"]["name"] if grow["plan"] else None,
            icon="mdi:sprout",
        )
        gadd(
            "sensor", "stage", "Current stage", stage["name"] if stage else None, icon="mdi:stairs"
        )
        gadd(
            "sensor",
            "stage_day",
            "Stage day",
            stage["day"] if stage else None,
            icon="mdi:calendar-today",
        )
        gadd(
            "sensor",
            "stage_days_remaining",
            "Stage days remaining",
            stage["days_remaining"] if stage else None,
            unit_of_measurement="d",
            icon="mdi:calendar-end",
        )
        gadd(
            "sensor",
            "stage_progress",
            "Stage progress",
            stage["progress"] if stage else None,
            unit_of_measurement="%",
            icon="mdi:progress-clock",
        )
        gadd("sensor", "grow_day", "Grow day", grow["grow_day"], icon="mdi:calendar-range")
        gadd("sensor", "grow_started", "Grow started", grow["grow_started"], device_class="date")
        gadd("sensor", "expected_end", "Expected end", grow["expected_end"], device_class="date")
        gadd(
            "select",
            "active_plan",
            "Plan",
            grow["plan"]["name"] if grow["plan"] else NO_PLAN,
            True,
            options=[NO_PLAN, *plan_names],
            icon="mdi:sprout",
        )
        stage_options = [f"{i}. {s['name']}" for i, s in enumerate(grow["stages"], 1)]
        gadd(
            "select",
            "current_stage",
            "Stage",
            f"{stage['number']}. {stage['name']}" if stage else None,
            True,
            options=stage_options or [NONE_PAYLOAD],
            icon="mdi:stairs",
        )
        gadd(
            "switch",
            "night_lighting",
            "Night lighting",
            grow["night_lighting"],
            True,
            icon="mdi:weather-night",
        )
        if grow["active"]:
            for key, name, icon in (
                ("next_stage", "Next stage", "mdi:skip-next"),
                ("previous_stage", "Previous stage", "mdi:skip-previous"),
                ("restart_stage", "Restart stage", "mdi:restart"),
            ):
                gadd("button", key, name, None, True, icon=icon)

    # -- water and climate -------------------------------------------------------------
    for metric, label, icon in (("ph", "pH", "mdi:ph"), ("ec", "EC", "mdi:flash-outline")):
        data = metrics[metric]
        unit = {"unit_of_measurement": ec_unit} if metric == "ec" else {}
        add(
            "sensor",
            f"measured_{metric}",
            f"Measured {label}",
            data["value"],
            state_class="measurement",
            icon=icon,
            **unit,
        )
        add("sensor", f"{metric}_min", f"{label} min", data["min"], icon=icon, **unit)
        add("sensor", f"{metric}_max", f"{label} max", data["max"], icon=icon, **unit)
        if not data["from_sensor"]:
            number: dict[str, Any] = {"mode": "box", "icon": icon, "min": 0, "max": 14, "step": 0.1}
            if metric == "ec":
                number.update(
                    max=units.from_canonical(20, ec_unit),
                    step=units.step(ec_unit),
                    unit_of_measurement=ec_unit,
                )
            add("number", f"record_{metric}", f"Record {label}", data["value"], True, **number)

    for metric, label in (
        ("ph", "pH"),
        ("ec", "EC"),
        ("temperature", "Temperature"),
        ("humidity", "Humidity"),
    ):
        add(
            "binary_sensor",
            f"{metric}_out_of_range",
            f"{label} out of range",
            metrics[metric]["out_of_range"],
            device_class="problem",
        )
    add(
        "binary_sensor",
        "reading_overdue",
        "Water reading overdue",
        snap["reading_overdue"],
        device_class="problem",
    )

    # -- devices -------------------------------------------------------------------------
    for dev in snap["devices"]:
        add(
            "binary_sensor",
            f"device_{dev['id']}_scheduled",
            f"{dev['name']} scheduled",
            dev["desired"],
            icon="mdi:calendar-clock",
            json_attributes_topic=f"{base}/device_{dev['id']}_scheduled/attrs",
        )
        states[f"{base}/device_{dev['id']}_scheduled/attrs"] = json.dumps(
            {
                "controlled_entity": dev["entity_id"],
                "mode": dev["mode"],
                "schedule": dev["schedule"],
                "light": dev["light"],
            }
        )

    # -- controls ------------------------------------------------------------------------
    add("switch", "schedule_control", "Schedule control", snap["schedule_enabled"], True)
    add("button", "sync_devices", "Sync devices", None, True, icon="mdi:sync")
    add("button", "water_checked", "Water checked", None, True, icon="mdi:water-check")
    return configs, states


GROW_KEY = re.compile(r"^grow_([^_]+)_(.+)$")


async def handle_command(system: GrowSystem, key: str, payload: str) -> None:
    """Apply a command received on an entity's command topic."""
    on = payload.upper() == "ON"
    if match := GROW_KEY.match(key):
        grow, key = match.group(1), match.group(2)
        if key == "night_lighting":
            await system.set_night_lighting(on, grow)
        elif key == "next_stage":
            await system.advance_stage(grow)
        elif key == "previous_stage":
            await system.previous_stage(grow)
        elif key == "restart_stage":
            await system.restart_stage(grow)
        elif key == "active_plan":
            if payload == NO_PLAN:
                await system.end_grow(grow)
            else:
                await system.start_grow(
                    payload, replace=grow, name=system.grow(grow).name, keep_start=True
                )
        elif key == "current_stage":
            number = payload.split(".", 1)[0]
            await system.set_stage(int(number) if number.isdigit() else payload, grow=grow)
        else:
            raise GrowError(f"Unknown command: {key}")
    elif key == "schedule_control":
        await system.set_schedule_enabled(on)
    elif key == "sync_devices":
        await system.sync(force=True)
    elif key == "water_checked":
        await system.water_checked()
    elif key == "record_ph":
        await system.record_reading(ph=float(payload))
    elif key == "record_ec":
        await system.record_reading(ec=float(payload))
    else:
        raise GrowError(f"Unknown command: {key}")
