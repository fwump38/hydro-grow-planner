"""The grow system engine: its running grows, devices, tasks, readings and alerts.

`GrowSystem` has no I/O of its own. Home Assistant, the clock and persistence are
injected (see ports.py), so the whole thing is testable with fakes. All persisted
state lives in one JSON-friendly dict (`data`); mutate it only through the methods
here, which call `on_save` and `on_change`.

Stages never change on their own. The engine only prompts (the
`stage_complete_due` event and a "ready to move on?" task); a person moves on.
"""

from __future__ import annotations

from collections.abc import Callable
import copy
from dataclasses import dataclass
from datetime import date, datetime, timedelta
import logging
from typing import Any

from .core import nutrients as nutrient_calc, units
from .core.const import (
    DEFAULT_EC_UNIT,
    DEFAULT_READING_INTERVAL_DAYS,
    EVENT_BACK_IN_RANGE,
    EVENT_GROW_ENDED,
    EVENT_GROW_STARTED,
    EVENT_OUT_OF_RANGE,
    EVENT_READING_OVERDUE,
    EVENT_STAGE_CHANGED,
    EVENT_STAGE_COMPLETE_DUE,
    MODE_MANUAL,
)
from .core.maintenance import default_maintenance, normalize_maintenance
from .core.models import DeviceSchedule, Plan, Stage, Task, new_id, out_of_range
from .core.presets import LIGHT_ROLES, PRESET_ROLES, guess_role
from .core.progress import (
    day_number,
    expected_end,
    grow_start_for,
)
from .core.ranges import EVENT_OUT, RangeAlert, convert_temperature
from .core.schedule import desired_state, next_transition, shift_for_night
from .core.tasks import TaskInstance, due_date, initial_instances, next_instance
from .ports import Clock, EntityState, HAPort, ReadingsPort

_LOGGER = logging.getLogger(__name__)

STAGE_CHECK_ID = "stage_check"
MAX_HISTORY = 20
MAX_ACTIVITY = 200
KEEP_DONE_DAYS = 7
METRICS = ("ph", "ec", "temperature", "humidity")
CONFIG_KEYS = {
    "name",
    "devices",
    "zones",
    "sensors",
    "ec_unit",
    "ec_sensor_unit",
    "reading_interval_days",
    "maintenance",
    "capacity",
    "volume_unit",
    "temperature_unit",
    "weight_unit",
    "ec_stale_hours",
    "nutrients",
}
# What describes one stage run; saved to history when a stage is left.
RUN_KEYS = ("stage_id", "stage_started", "stage_run", "instances")
# What a system used to keep for its one grow; moved into a grow record on load.
LEGACY_GROW_KEYS = (
    "plan_id",
    "stage_id",
    "stage_started",
    "grow_started",
    "stage_run",
    "stage_check_notified",
)


def _litres_per(volume_unit: str) -> float:
    return units.LITRES_PER_GALLON if volume_unit == "gal" else 1.0


def _grams_per(weight_unit: str) -> float:
    return units.GRAMS_PER_OUNCE if weight_unit == "oz" else 1.0


class GrowError(Exception):
    """A command could not be carried out; the message is safe to show a user."""


@dataclass(frozen=True, slots=True)
class Device:
    """A controlled device (any entity with turn_on/turn_off)."""

    id: str
    name: str
    entity_id: str
    light: bool = False
    role: str = ""
    zone: str | None = None


class Grow:
    """One running plan: its own stage, dates, tasks and night lighting.

    A system can run several grows at once. They share its devices, sensors and
    water readings; everything else lives in the grow's record (`rt["grows"]`).
    """

    def __init__(self, system: GrowSystem, data: dict[str, Any]) -> None:
        """Wrap a grow record of `system`."""
        self.system = system
        self.data = data

    @property
    def id(self) -> str:
        """Return the grow id."""
        return self.data["id"]

    @property
    def seq(self) -> int:
        """Return the order grows were started in (the oldest wins range conflicts)."""
        return int(self.data.get("seq", 0))

    @property
    def plan(self) -> Plan | None:
        """Return the grow's own copy of its plan (schedules, tasks, targets)."""
        return self.system.plan_of(self)

    @property
    def name(self) -> str:
        """Return the grow's label, e.g. "Layers 1+2" (the plan name by default)."""
        plan = self.plan
        return self.data.get("name") or (plan.name if plan else "Grow")

    @property
    def stage_index(self) -> int | None:
        """Return the 0-based index of the current stage."""
        plan = self.plan
        return plan.stage_index(self.data.get("stage_id")) if plan else None

    @property
    def stage(self) -> Stage | None:
        """Return the current stage."""
        plan, index = self.plan, self.stage_index
        return plan.stages[index] if plan is not None and index is not None else None

    @property
    def is_active(self) -> bool:
        """Return True when the plan and stage still exist."""
        return self.stage is not None

    @property
    def stage_started(self) -> date | None:
        """Return the date the current stage started."""
        value = self.data.get("stage_started")
        return date.fromisoformat(value) if value else None

    @property
    def grow_started(self) -> date | None:
        """Return the date the grow started."""
        value = self.data.get("grow_started")
        return date.fromisoformat(value) if value else None

    @property
    def stage_day(self) -> int | None:
        """Return the 1-based day of the current stage."""
        started = self.stage_started
        return day_number(started, self.system.today) if self.is_active and started else None

    @property
    def grow_day(self) -> int | None:
        """Return the 1-based day of the whole grow."""
        started = self.grow_started
        return day_number(started, self.system.today) if self.is_active and started else None

    @property
    def night_lighting(self) -> bool:
        """Return True when this grow's light windows are shifted by 12 hours."""
        return bool(self.data.get("night_lighting"))

    def schedule_for(self, device: Device) -> DeviceSchedule | None:
        """Return the device's effective schedule in this grow's current stage."""
        stage = self.stage
        if stage is None:
            return None
        schedule = stage.schedule_for(device.id)
        return shift_for_night(schedule) if self.night_lighting and device.light else schedule

    def range_for(self, metric: str) -> tuple[float | None, float | None]:
        """Return this grow's own target range (EC in mS/cm; temperature in the plan's unit)."""
        plan, stage = self.plan, self.stage
        if plan is None or stage is None:
            return None, None
        return {
            "ph": (plan.ph_min, plan.ph_max),
            "ec": (stage.ec_min, stage.ec_max),
            "temperature": (plan.temp_min, plan.temp_max),
            "humidity": (plan.humidity_min, plan.humidity_max),
        }[metric]


def combined_desired(schedules: list[DeviceSchedule], now: datetime) -> bool | None:
    """Return what a device shared by several grows should do: on if any grow wants it on."""
    states = [state for s in schedules if (state := desired_state(s, now)) is not None]
    return any(states) if states else None


def guess_is_light(entity_id: str, name: str) -> bool:
    """Guess whether a device is a grow light (for night lighting)."""
    return entity_id.startswith("light.") or "light" in f"{entity_id} {name}".lower()


def new_system_data(system_id: str, name: str) -> dict[str, Any]:
    """Return the persisted dict for a new, empty grow system."""
    return {
        "id": system_id,
        "name": name,
        "devices": [],
        "zones": [],
        "sensors": {metric: None for metric in METRICS},
        "ec_unit": DEFAULT_EC_UNIT,
        "ec_sensor_unit": None,
        "reading_interval_days": DEFAULT_READING_INTERVAL_DAYS,
        "maintenance": default_maintenance(),
        # Tank size in litres. Units are None to follow Home Assistant's unit system.
        "capacity_l": None,
        "volume_unit": None,
        "temperature_unit": None,
        "weight_unit": None,
        "ec_stale_hours": nutrient_calc.DEFAULT_STALE_HOURS,
        "nutrients": nutrient_calc.default_nutrients(),
        "runtime": {},
    }


class GrowSystem:
    """Holds and drives one grow system."""

    def __init__(
        self,
        data: dict[str, Any],
        ha: HAPort,
        clock: Clock,
        readings: ReadingsPort | None = None,
        on_save: Callable[[], None] = lambda: None,
        on_change: Callable[[], None] = lambda: None,
        make_id: Callable[[], str] = new_id,
    ) -> None:
        """Wrap a persisted data dict (see new_system_data)."""
        self.data = data
        self.ha = ha
        self.clock = clock
        self.readings = readings
        self._on_save = on_save
        self._on_change = on_change
        self._make_id = make_id
        self.states: dict[str, EntityState] = {}
        self._plans_cache: dict[str, tuple[dict[str, Any], Plan]] = {}

        data.setdefault("maintenance", default_maintenance())
        data.setdefault("zones", [])
        data.setdefault("capacity_l", None)
        data.setdefault("volume_unit", None)
        data.setdefault("temperature_unit", None)
        data.setdefault("weight_unit", None)
        # The units Home Assistant is set to; the app shares one dict with every system.
        self.ha_units: dict[str, str] = {}
        data.setdefault("ec_stale_hours", nutrient_calc.DEFAULT_STALE_HOURS)
        data.setdefault("nutrients", nutrient_calc.default_nutrients())
        for device in data.get("devices", []):
            device.setdefault("role", guess_role(device["entity_id"], device["name"]))
            device.setdefault("zone", None)
        rt = data.setdefault("runtime", {})
        rt.setdefault("maintenance", {})
        rt.setdefault("schedule_enabled", True)
        rt.setdefault("last_desired", {})
        rt.setdefault("instances", [])
        # Upkeep used to be task instances; Home Keeper schedules it now.
        rt["instances"] = [i for i in rt["instances"] if not i.get("maintenance")]
        rt.setdefault("custom_tasks", {})
        rt.setdefault("grows", {})
        rt.setdefault("grow_seq", 0)
        rt.setdefault("activity", [])
        # Whether Home Keeper answered its last sync (None before the first); the panel
        # shows a notice when it did not.
        self.home_keeper_available: bool | None = None
        rt.setdefault("alerts", {})
        self._alerts = {m: RangeAlert(rt["alerts"].setdefault(m, {})) for m in METRICS}
        self._migrate_single_grow()
        self._absorb_plans()

    def _absorb_plans(self) -> None:
        """Move the saved plans older versions kept into the grows running them.

        Each grow gets its own copy. Plans no grow uses stay in `data["plans"]` for the app
        to turn into templates (see `take_unused_plans`).
        """
        saved = self.data.get("plans") or {}
        used: set[str] = set()
        for record in list(self.rt["grows"].values()):
            plan_id = record.pop("plan_id", None)
            if "plan" in record:
                continue
            if plan_id not in saved:
                # Its plan is gone, so there is nothing to run.
                self.rt["grows"].pop(record["id"], None)
                self.rt["instances"] = [
                    i
                    for i in self.rt["instances"]
                    if i.get("grow") != record["id"] or i.get("custom")
                ]
                continue
            record["plan"] = copy.deepcopy(saved[plan_id])
            used.add(plan_id)
        self.data["plans"] = {pid: plan for pid, plan in saved.items() if pid not in used}

    def take_unused_plans(self) -> dict[str, dict[str, Any]]:
        """Hand over (and forget) old saved plans no grow uses, so they can become templates."""
        return self.data.pop("plans", None) or {}

    def _migrate_single_grow(self) -> None:
        """Move the one grow older versions kept in the runtime into a grow record."""
        rt = self.rt
        if not any(key in rt for key in (*LEGACY_GROW_KEYS, "night_lighting", "history")):
            return
        night = bool(rt.pop("night_lighting", False))
        history = rt.pop("history", [])
        legacy = {key: rt.pop(key) for key in LEGACY_GROW_KEYS if key in rt}
        saved = (self.data.get("plans") or {}).get(legacy.get("plan_id") or "")
        plan = Plan.from_dict(legacy.get("plan_id") or "", saved) if saved else None
        if plan is None or plan.stage_index(legacy.get("stage_id")) is None:
            rt["instances"] = [i for i in rt["instances"] if i.get("custom")]
            return
        grow_id = self._make_id()
        rt["grow_seq"] += 1
        rt["grows"][grow_id] = {
            "id": grow_id,
            "name": plan.name,
            "seq": rt["grow_seq"],
            "night_lighting": night,
            "history": history,
            **legacy,
        }
        for inst in rt["instances"]:
            if not inst.get("custom"):
                inst["grow"] = grow_id

    # ------------------------------------------------------------------
    # Basics
    # ------------------------------------------------------------------

    @property
    def rt(self) -> dict[str, Any]:
        """Return the runtime state dict."""
        return self.data["runtime"]

    @property
    def id(self) -> str:
        """Return the system id."""
        return self.data["id"]

    @property
    def name(self) -> str:
        """Return the system name."""
        return self.data["name"]

    @property
    def now(self) -> datetime:
        """Return the current local time."""
        return self.clock()

    @property
    def today(self) -> date:
        """Return today's local date."""
        return self.now.date()

    def _changed(self) -> None:
        self._on_save()
        self._on_change()

    def _log(self, kind: str, message: str) -> None:
        activity = self.rt["activity"]
        activity.append({"at": self.now.isoformat(), "kind": kind, "message": message})
        del activity[:-MAX_ACTIVITY]

    async def _fire(self, event: str, payload: dict[str, Any]) -> None:
        body = {"system_id": self.id, "system": self.name, **payload}
        try:
            await self.ha.fire_event(event, body)
        except Exception:
            _LOGGER.exception("Failed to fire %s", event)

    @property
    def devices(self) -> list[Device]:
        """Return the controlled devices."""
        return [
            Device(
                d["id"],
                d["name"],
                d["entity_id"],
                d.get("light", guess_is_light(d["entity_id"], d["name"])),
                d.get("role", ""),
                d.get("zone"),
            )
            for d in self.data["devices"]
        ]

    def plan_of(self, grow: Grow) -> Plan | None:
        """Return a grow's plan, parsed once per change."""
        raw = grow.data.get("plan")
        if raw is None:
            return None
        cached = self._plans_cache.get(grow.id)
        if cached is None or cached[0] is not raw:
            cached = (raw, Plan.from_dict(grow.id, raw))
            self._plans_cache[grow.id] = cached
        return cached[1]

    def set_grow_plan(self, grow: str | None, plan_data: dict[str, Any]) -> None:
        """Replace a grow's own plan (editing it keeps the grow going).

        If the stage the grow was in is gone, it moves to the first stage.
        """
        found = self.grow(grow)
        found.data["plan"] = copy.deepcopy(plan_data)
        self._plans_cache.pop(found.id, None)
        if not found.is_active:
            plan = found.plan
            if plan is not None and plan.stages:
                self._log(
                    "plan", f"{found.name}: the current stage was removed; moved to the first stage"
                )
                self._enter_stage(found, plan, plan.stages[0], self.today)
            else:
                self._clear_grow(found)
        self._changed()

    def update_config(self, **fields: Any) -> None:
        """Change settings: name, devices, sensors, EC units, intervals, to-do list.

        Raises GrowError for an invalid value, leaving everything unchanged.
        """
        unknown = set(fields) - CONFIG_KEYS
        if unknown:
            raise GrowError(f"Unknown setting: {', '.join(sorted(unknown))}")
        clean: dict[str, Any] = {}
        if "name" in fields:
            name = str(fields["name"]).strip()
            if not name:
                raise GrowError("A system needs a name")
            clean["name"] = name
        for key in ("ec_unit", "ec_sensor_unit"):
            if key in fields:
                value = fields[key] or None
                if value is not None and not units.is_valid_unit(value):
                    raise GrowError(f"Unknown EC unit: {value}")
                if key == "ec_unit" and value is None:
                    raise GrowError("Choose an EC unit")
                clean[key] = value
        if "reading_interval_days" in fields:
            days = int(fields["reading_interval_days"])
            if not 1 <= days <= 60:
                raise GrowError("The reading interval must be 1-60 days")
            clean["reading_interval_days"] = days
        if "maintenance" in fields:
            tasks, problems = normalize_maintenance(fields["maintenance"], self._make_id)
            if problems:
                raise GrowError(f"{problems[0]['message']} ({problems[0]['path']})")
            clean["maintenance"] = tasks
        for key, allowed in (
            ("volume_unit", units.VOLUME_UNITS),
            ("temperature_unit", units.TEMPERATURE_UNITS),
            ("weight_unit", units.WEIGHT_UNITS),
        ):
            if key in fields:
                value = fields[key] or None
                if value is not None and value not in allowed:
                    raise GrowError(f"Unknown unit: {value}")
                clean[key] = value
        if "capacity" in fields:
            # Entered in the volume unit that will apply once this change is saved.
            raw = fields["capacity"]
            capacity = None if raw in (None, "") else float(raw)
            if capacity is not None and not 0 < capacity <= 100000:
                raise GrowError("The tank capacity must be above 0")
            unit = self._resolve("volume_unit", clean.get("volume_unit", self.data["volume_unit"]))
            clean["capacity_l"] = None if capacity is None else capacity * _litres_per(unit)
        if "ec_stale_hours" in fields:
            hours = int(fields["ec_stale_hours"])
            if not 1 <= hours <= 24 * 60:
                raise GrowError("An EC reading goes stale after 1-1440 hours")
            clean["ec_stale_hours"] = hours
        if "nutrients" in fields:
            nutrients, problems = nutrient_calc.normalize_nutrients(
                fields["nutrients"], self._make_id
            )
            if problems:
                raise GrowError(f"{problems[0]['message']} ({problems[0]['path']})")
            clean["nutrients"] = nutrients
        if "sensors" in fields:
            sensors = {m: (fields["sensors"].get(m) or None) for m in METRICS}
            clean["sensors"] = sensors
        if "zones" in fields or "devices" in fields:
            zones = self._clean_zones(fields["zones"]) if "zones" in fields else None
            if zones is not None:
                clean["zones"] = zones
        if "devices" in fields:
            devices = []
            zone_ids = {z["id"] for z in (zones if zones is not None else self.data["zones"])}
            for raw in fields["devices"]:
                entity_id, name = raw.get("entity_id"), (raw.get("name") or "").strip()
                if not entity_id or "." not in entity_id:
                    raise GrowError("Every device needs an entity")
                name = name or entity_id
                role = raw["role"] if "role" in raw else guess_role(entity_id, name)
                if role and role not in PRESET_ROLES:
                    raise GrowError(f"Unknown device role: {role}")
                devices.append(
                    {
                        "id": raw.get("id") or self._make_id(),
                        "name": name,
                        "entity_id": entity_id,
                        "light": bool(raw.get("light", guess_is_light(entity_id, name))),
                        "role": role,
                        "zone": raw.get("zone") if role in LIGHT_ROLES else None,
                    }
                )
                if devices[-1]["zone"] not in zone_ids:
                    devices[-1]["zone"] = None
            clean["devices"] = devices
        elif "zones" in clean:
            # Lights in a removed zone become unzoned.
            known = {z["id"] for z in clean["zones"]}
            for device in self.data["devices"]:
                if device.get("zone") not in known:
                    device["zone"] = None
        self.data.update(clean)
        if "devices" in clean:
            known = {d["id"] for d in clean["devices"]}
            self.rt["last_desired"] = {
                k: v for k, v in self.rt["last_desired"].items() if k in known
            }
        self._changed()

    def _clean_zones(self, raw_zones: list[dict[str, Any]]) -> list[dict[str, str]]:
        """Validate zones: named, unique (ignoring case). Keeps ids of existing zones."""
        zones: list[dict[str, str]] = []
        for raw in raw_zones:
            name = (raw.get("name") or "").strip()
            if not name:
                raise GrowError("A zone needs a name")
            if any(z["name"].casefold() == name.casefold() for z in zones):
                raise GrowError(f"There are two zones called {name}")
            zones.append({"id": raw.get("id") or self._make_id(), "name": name})
        return zones

    def set_state(self, entity_id: str, state: EntityState | None) -> None:
        """Feed an entity's latest state (from the HA websocket)."""
        if state is None:
            self.states.pop(entity_id, None)
        else:
            self.states[entity_id] = state

    # ------------------------------------------------------------------
    # Current grow
    # ------------------------------------------------------------------

    @property
    def grows(self) -> list[Grow]:
        """Return every grow, oldest first."""
        records = sorted(self.rt["grows"].values(), key=lambda g: (g.get("seq", 0), g["id"]))
        return [Grow(self, record) for record in records]

    @property
    def active_grows(self) -> list[Grow]:
        """Return the grows that are running."""
        return [g for g in self.grows if g.is_active]

    @property
    def is_active(self) -> bool:
        """Return True when at least one grow is running."""
        return bool(self.active_grows)

    @property
    def system_started(self) -> date | None:
        """Return when the system started running: the earliest start of a running grow.

        A grow's start date is backdated when it was started late and kept when its
        plan is changed mid-grow, so this is how long the system has really been in use.
        """
        starts = [s for g in self.active_grows if (s := g.grow_started) is not None]
        return min(starts, default=None)

    @property
    def system_day(self) -> int | None:
        """Return the 1-based day the system has been running, or None when idle."""
        started = self.system_started
        return day_number(started, self.today) if started else None

    def grow(self, ref: str | None = None) -> Grow:
        """Return a grow by id or name; without a ref, the only grow."""
        grows = self.grows
        if ref is None:
            if len(grows) == 1:
                return grows[0]
            if not grows:
                raise GrowError("No grow is running")
            raise GrowError("Choose which grow: " + ", ".join(g.name for g in grows))
        for grow in grows:
            if ref == grow.id:
                return grow
        for grow in grows:
            if grow.name.casefold() == str(ref).casefold():
                return grow
        raise GrowError(f"Unknown grow: {ref}")

    def _grow_fields(self, grow: Grow) -> dict[str, Any]:
        return {"grow_id": grow.id, "grow": grow.name}

    @property
    def schedule_enabled(self) -> bool:
        """Return True when the app may switch devices."""
        return bool(self.rt["schedule_enabled"])

    # ------------------------------------------------------------------
    # Water and climate
    # ------------------------------------------------------------------

    @property
    def ec_unit(self) -> str:
        """Return the unit EC is entered and shown in."""
        return self.data.get("ec_unit") or DEFAULT_EC_UNIT

    def _sensor_entity(self, metric: str) -> str | None:
        return self.data["sensors"].get(metric)

    def _sensor_state(self, metric: str) -> tuple[float, str | None] | None:
        entity_id = self._sensor_entity(metric)
        state = self.states.get(entity_id) if entity_id else None
        if state is None or state.state in ("unknown", "unavailable", ""):
            return None
        try:
            return float(state.state), state.unit
        except ValueError:
            return None

    def has_sensor(self, metric: str) -> bool:
        """Return True if the metric comes from a sensor rather than manual entry."""
        return bool(self._sensor_entity(metric))

    @property
    def ec_sensor_unit(self) -> str:
        """Return the unit the EC sensor reports in (override, else detected)."""
        override = self.data.get("ec_sensor_unit")
        if override:
            return override
        state = self.states.get(self._sensor_entity("ec") or "")
        return units.detect_unit(state.unit if state else None) or DEFAULT_EC_UNIT

    @property
    def ph(self) -> float | None:
        """Return the latest pH reading."""
        if self.has_sensor("ph"):
            reading = self._sensor_state("ph")
            return reading[0] if reading else None
        return self.rt.get("ph")

    @property
    def ec(self) -> float | None:
        """Return the latest EC reading in mS/cm."""
        if self.has_sensor("ec"):
            reading = self._sensor_state("ec")
            return units.to_canonical(reading[0], self.ec_sensor_unit) if reading else None
        return self.rt.get("ec")

    @property
    def ec_display(self) -> float | None:
        """Return the latest EC reading in the system's display unit."""
        ec = self.ec
        return units.from_canonical(ec, self.ec_unit) if ec is not None else None

    def _resolve(self, key: str, override: str | None) -> str:
        """Return a display unit: the setting if it has one, else Home Assistant's, else a default."""
        if override:
            return override
        ha_key = {
            "volume_unit": "volume",
            "temperature_unit": "temperature",
            "weight_unit": "weight",
        }
        if found := self.ha_units.get(ha_key[key]):
            return found
        if key == "temperature_unit":
            # Without either, use the oldest running plan's unit.
            grows = self.active_grows
            plan = grows[0].plan if grows else None
            return plan.temp_unit if plan else "°C"
        return {"volume_unit": "gal", "weight_unit": "g"}[key]

    @property
    def temperature_unit(self) -> str:
        """Return the unit temperatures are shown in."""
        return self._resolve("temperature_unit", self.data["temperature_unit"])

    @property
    def volume_unit(self) -> str:
        """Return the unit water volumes are shown in."""
        return self._resolve("volume_unit", self.data["volume_unit"])

    @property
    def weight_unit(self) -> str:
        """Return the unit nutrient weights are shown in."""
        return self._resolve("weight_unit", self.data["weight_unit"])

    @property
    def capacity(self) -> float | None:
        """Return the tank capacity in `volume_unit`."""
        litres = self.data["capacity_l"]
        return None if litres is None else round(litres / _litres_per(self.volume_unit), 2)

    @property
    def temperature(self) -> float | None:
        """Return the room temperature in `temperature_unit`."""
        reading = self._sensor_state("temperature")
        if reading is None:
            return None
        return round(convert_temperature(reading[0], reading[1], self.temperature_unit), 1)

    @property
    def humidity(self) -> float | None:
        """Return the room humidity (%)."""
        reading = self._sensor_state("humidity")
        return reading[0] if reading else None

    def _combined_range(self, metric: str) -> tuple[float | None, float | None, bool]:
        """Return (min, max, conflict) over every running grow.

        The room and reservoir are shared, so the target is where the grows'
        ranges overlap. When they don't, the oldest grow's range is used and
        `conflict` is True.
        """
        ranges = []
        for grow in self.active_grows:
            low, high = grow.range_for(metric)
            plan = grow.plan
            if metric == "temperature" and plan is not None:
                unit = self.temperature_unit
                low = convert_temperature(low, plan.temp_unit, unit) if low is not None else None
                high = convert_temperature(high, plan.temp_unit, unit) if high is not None else None
            ranges.append((low, high))
        lows = [low for low, _ in ranges if low is not None]
        highs = [high for _, high in ranges if high is not None]
        low, high = (max(lows) if lows else None), (min(highs) if highs else None)
        if low is not None and high is not None and low > high:
            return ranges[0][0], ranges[0][1], True
        return low, high, False

    def range_for(self, metric: str) -> tuple[float | None, float | None]:
        """Return the target range of a metric in canonical units (EC in mS/cm)."""
        low, high, _ = self._combined_range(metric)
        return low, high

    def range_conflict(self, metric: str) -> bool:
        """Return True when the running grows' ranges for a metric don't overlap."""
        return self._combined_range(metric)[2]

    def value_of(self, metric: str) -> float | None:
        """Return the current value of a metric in canonical units."""
        return {
            "ph": self.ph,
            "ec": self.ec,
            "temperature": self.temperature,
            "humidity": self.humidity,
        }[metric]

    def is_out_of_range(self, metric: str) -> bool | None:
        """Return whether a metric is outside its target range."""
        return out_of_range(self.value_of(metric), *self.range_for(metric))

    @property
    def last_reading(self) -> datetime | None:
        """Return when a reading was last recorded by hand."""
        value = self.rt.get("last_reading")
        return datetime.fromisoformat(value) if value else None

    @property
    def reading_overdue(self) -> bool | None:
        """Return whether a manual water reading is due (None when sensors cover it)."""
        if self.has_sensor("ph") and self.has_sensor("ec"):
            return None
        if not self.is_active:
            return False
        last = self.last_reading
        if last is None:
            starts = [g.grow_started for g in self.active_grows if g.grow_started]
            if not starts:
                return False
            started = min(starts)
            last = datetime.combine(started, datetime.min.time(), tzinfo=self.now.tzinfo)
        interval = timedelta(
            days=self.data.get("reading_interval_days", DEFAULT_READING_INTERVAL_DAYS)
        )
        return self.now - last >= interval

    # ------------------------------------------------------------------
    # Devices
    # ------------------------------------------------------------------

    def drivers(self, device: Device) -> list[tuple[Grow, DeviceSchedule]]:
        """Return the running grows that manage a device, with their schedules."""
        result = []
        for grow in self.active_grows:
            schedule = grow.schedule_for(device)
            if schedule is not None and schedule.mode != MODE_MANUAL:
                result.append((grow, schedule))
        return result

    def schedule_for(self, device: Device) -> DeviceSchedule | None:
        """Return the schedule to show for a device (the oldest managing grow's)."""
        drivers = self.drivers(device)
        if drivers:
            return drivers[0][1]
        return DeviceSchedule() if self.is_active else None

    def desired(self, device: Device) -> bool | None:
        """Return the desired state of a device right now (None = unmanaged).

        A device two grows schedule is on whenever either wants it on.
        """
        return combined_desired([s for _, s in self.drivers(device)], self.now)

    def next_change(self, device: Device) -> datetime | None:
        """Return when the device's desired state may next change."""
        changes = [t for _, s in self.drivers(device) if (t := next_transition(s, self.now))]
        return min(changes) if changes else None

    def actual(self, device: Device) -> bool | None:
        """Return whether the device is on right now (None when unknown)."""
        state = self.states.get(device.entity_id)
        if state is None or state.state in ("unknown", "unavailable"):
            return None
        return state.state == "on"

    async def sync(self, force: bool = False) -> None:
        """Bring devices in line with the schedule.

        Without force, only devices whose desired state changed since the last
        evaluation are switched, so a manual override lasts until the next
        scheduled change. With force, every managed device is asserted.
        """
        last: dict[str, bool] = self.rt["last_desired"]
        changed = False
        for device in self.devices:
            want = self.desired(device)
            if want is None:
                if last.pop(device.id, None) is not None:
                    changed = True
                continue
            if not force and last.get(device.id) == want:
                continue
            last[device.id] = want
            changed = True
            if self.schedule_enabled:
                await self.switch(device, want, "forced sync" if force else "schedule")
        if changed or force:
            self._on_save()
            self._on_change()

    async def switch(self, device: Device, on: bool, reason: str) -> None:
        """Turn a device on or off (skipped when unavailable or already there)."""
        state = self.states.get(device.entity_id)
        if state is None or state.state == "unavailable":
            _LOGGER.warning("%s is unavailable; cannot switch it", device.entity_id)
            return
        if state.state == ("on" if on else "off"):
            return
        try:
            await self.ha.call_service(
                device.entity_id.split(".", 1)[0],
                "turn_on" if on else "turn_off",
                {"entity_id": device.entity_id},
            )
        except Exception as err:
            _LOGGER.error("Failed to switch %s: %s", device.entity_id, err)
            self._log("device", f"Could not switch {device.name}: {err}")
            return
        self._log("device", f"{device.name} {'on' if on else 'off'} ({reason})")

    async def manual_switch(self, device_id: str, on: bool) -> None:
        """Switch a device by hand; the schedule takes over again at its next change."""
        device = next((d for d in self.devices if d.id == device_id), None)
        if device is None:
            raise GrowError("Unknown device")
        await self.switch(device, on, "manual")
        self._on_change()

    async def set_night_lighting(self, enabled: bool, grow: str | None = None) -> None:
        """Shift one grow's light windows by 12 hours (or back) and re-sync."""
        self.grow(grow).data["night_lighting"] = enabled
        self._on_save()
        await self.sync(force=True)

    async def set_schedule_enabled(self, enabled: bool) -> None:
        """Enable or disable device control."""
        self.rt["schedule_enabled"] = enabled
        self._on_save()
        if enabled:
            await self.sync(force=True)
        else:
            self._on_change()

    def next_wakeup(self) -> datetime:
        """Return when tick() next needs to run (at most a minute from now)."""
        now = self.now
        candidates = [now + timedelta(seconds=60)]
        candidates += [t for d in self.devices if (t := self.next_change(d)) is not None]
        return min(candidates)

    # ------------------------------------------------------------------
    # Stage lifecycle
    # ------------------------------------------------------------------

    def _stage_or_raise(self, plan: Plan, stage_ref: str | int) -> Stage:
        # Ids and names first: a random hex id can be all digits.
        if not isinstance(stage_ref, int):
            for stage in plan.stages:
                if stage_ref == stage.id or stage.name.casefold() == str(stage_ref).casefold():
                    return stage
        if isinstance(stage_ref, int) or str(stage_ref).isdigit():
            index = int(stage_ref) - 1
            if 0 <= index < len(plan.stages):
                return plan.stages[index]
        raise GrowError(f"Unknown stage {stage_ref} in {plan.name}")

    def _stage_check_task(self, plan: Plan, stage: Stage) -> Task:
        """A reminder on the stage's last planned day to decide on moving on."""
        index = plan.stage_index(stage.id) or 0
        nxt = plan.stages[index + 1] if index + 1 < len(plan.stages) else None
        if nxt is None and plan.continuous:
            # Harvesting a little at a time has no natural end; the plants decide.
            return Task(
                id=STAGE_CHECK_ID,
                task_type="reminder",
                title="Check if it's time to finish the grow",
                days=(stage.days,),
                note="\n\n".join(
                    part
                    for part in (
                        f"Signs the plants are spent: {stage.outcome}" if stage.outcome else "",
                        "If they are still regrowing, use Restart stage to keep harvesting. "
                        "Otherwise end the grow, clean the system and replant.",
                    )
                    if part
                ),
            )
        title = f"Check if ready for {nxt.name}" if nxt else "Check if ready to finish the grow"
        action = f"If so, move on with Next stage ({nxt.name})." if nxt else "If so, end the grow."
        outcome = f"Expected by now: {stage.outcome}" if stage.outcome else ""
        return Task(
            id=STAGE_CHECK_ID,
            task_type="reminder",
            title=title,
            days=(stage.days,),
            note="\n\n".join(part for part in (outcome, action) if part),
        )

    def _require_active(self, grow: str | None) -> tuple[Grow, Plan, Stage]:
        found = self.grow(grow)
        plan, stage = found.plan, found.stage
        if plan is None or stage is None:
            raise GrowError("No grow is running")
        return found, plan, stage

    def _enter_stage(
        self,
        grow: Grow,
        plan: Plan,
        stage: Stage,
        started: date,
        include_past_tasks: bool = False,
    ) -> None:
        rt, record = self.rt, grow.data
        if record.get("stage_id"):
            # Remember the stage being left so going back can undo the move.
            entry = {key: record.get(key) for key in RUN_KEYS}
            entry["instances"] = [
                i for i in rt["instances"] if i.get("grow") == grow.id and not i.get("custom")
            ]
            record.setdefault("history", []).append(entry)
            del record["history"][:-MAX_HISTORY]
        # Plan task instances belong to a stage run; custom ones carry over.
        rt["instances"] = [
            i for i in rt["instances"] if i.get("custom") or i.get("grow") != grow.id
        ]
        record["stage_id"] = stage.id
        record["stage_started"] = started.isoformat()
        record["stage_run"] = record.get("stage_run", 0) + 1
        record["stage_check_notified"] = False
        today = self.today
        created = initial_instances(
            stage, record["stage_run"], started, today, self._make_id, include_past_tasks
        )
        check_due = max(due_date(started, stage.days), today)
        created.append(
            TaskInstance(self._make_id(), STAGE_CHECK_ID, record["stage_run"], check_due)
        )
        rt["instances"].extend(_dump_instance(i, custom=False, grow=grow.id) for i in created)

    def _clear_grow(self, grow: Grow) -> None:
        rt = self.rt
        rt["grows"].pop(grow.id, None)
        self._plans_cache.pop(grow.id, None)
        kept = []
        for inst in rt["instances"]:
            if inst.get("grow") == grow.id:
                if not inst.get("custom"):
                    continue
                inst["grow"] = None
            kept.append(inst)
        rt["instances"] = kept
        if not rt["grows"]:
            rt["last_desired"] = {}
        for alert in self._alerts.values():
            alert.reset()
        rt["reading_overdue_notified"] = False

    async def start_grow(
        self,
        plan_data: dict[str, Any],
        stage_ref: str | int | None = None,
        stage_started: date | None = None,
        grow_started: date | None = None,
        night_lighting: bool | None = None,
        include_past_tasks: bool = False,
        name: str | None = None,
        replace: str | None = None,
        keep_start: bool = False,
    ) -> str:
        """Start a grow from plan data (a template with devices filled in); the grow keeps its own copy.

        `stage_started` is the date the chosen stage began. Unless `grow_started` is
        given, the grow's start date is worked out from the earlier stages' lengths.
        With `replace` (a grow id or name) that grow is replaced, keeping its place;
        with `keep_start` too, the new grow counts from the replaced grow's start, as
        when the plan is changed mid-grow. Returns the grow's id.
        """
        plan = Plan.from_dict("new", plan_data)
        if not plan.stages:
            raise GrowError(f"{plan.name} has no stages")
        stage = plan.stages[0] if stage_ref is None else self._stage_or_raise(plan, stage_ref)
        index = plan.stage_index(stage.id) or 0
        started = stage_started or self.today
        old = self.grow(replace) if replace is not None else None
        label = (name or "").strip() or plan.name
        if label.casefold() in {
            g.name.casefold() for g in self.grows if old is None or g.id != old.id
        }:
            raise GrowError(f"There is already a grow called {label}")
        grow_id = old.id if old else self._make_id()
        seq = old.seq if old else self.rt["grow_seq"] + 1
        night = night_lighting if night_lighting is not None else bool(old and old.night_lighting)
        if grow_started is None and keep_start and old is not None:
            grow_started = old.grow_started
        if old:
            self._clear_grow(old)
        self.rt["grow_seq"] = max(self.rt["grow_seq"], seq)
        self.rt["grows"][grow_id] = {
            "id": grow_id,
            "name": label,
            "seq": seq,
            "plan": copy.deepcopy(plan_data),
            "night_lighting": night,
            "grow_started": (grow_started or grow_start_for(plan, index, started)).isoformat(),
            "history": [],
        }
        grow = self.grow(grow_id)
        plan = grow.plan or plan
        stage = plan.stages[index]
        self._enter_stage(grow, plan, stage, started, include_past_tasks)
        self._log("grow", f"Started {label} ({plan.name}) at {stage.name}")
        await self._fire(
            EVENT_GROW_STARTED,
            {
                **self._grow_fields(grow),
                "plan": plan.name,
                "stage": stage.name,
                "stage_started": started.isoformat(),
            },
        )
        await self._after_stage_change(grow, None)
        return grow_id

    def preview_start(
        self,
        plan_data: dict[str, Any],
        stage_ref: str | int | None = None,
        stage_started: date | None = None,
        include_past_tasks: bool = False,
        replace: str | None = None,
        night_lighting: bool | None = None,
        keep_start: bool = False,
    ) -> dict[str, Any]:
        """Describe what starting a grow this way would do, without doing it.

        `plan_data` is a template with devices filled in; nothing is saved.
        """
        plan = Plan.from_dict("preview", plan_data)
        if not plan.stages:
            raise GrowError(f"{plan.name} has no stages")
        stage = plan.stages[0] if stage_ref is None else self._stage_or_raise(plan, stage_ref)
        index = plan.stage_index(stage.id) or 0
        today, now = self.today, self.now
        started = stage_started or today
        counter = iter(range(10**6))
        created = initial_instances(
            stage, 0, started, today, lambda: str(next(counter)), include_past_tasks
        )
        wanted = {i.task_id for i in created}
        tasks = []
        for inst in created:
            task = next((t for t in stage.tasks if t.id == inst.task_id), None)
            if task is not None:
                tasks.append(
                    {
                        "title": task.title,
                        "due": inst.due.isoformat(),
                        "overdue": inst.due < today,
                        "recurring": task.recurring,
                    }
                )
        skipped = [t.title for t in stage.tasks if t.id not in wanted]
        old = self.grow(replace) if replace is not None else None
        night = night_lighting if night_lighting is not None else bool(old and old.night_lighting)
        grow_started = grow_start_for(plan, index, started)
        if keep_start and old is not None and old.grow_started is not None:
            grow_started = old.grow_started
        others = [g for g in self.active_grows if old is None or g.id != old.id]
        devices = []
        for device in self.devices:
            schedule = stage.schedule_for(device.id)
            if night and device.light:
                schedule = shift_for_night(schedule)
            mine = schedule.mode != MODE_MANUAL
            shared = [
                (g.name, s)
                for g in others
                if (s := g.schedule_for(device)) and s.mode != MODE_MANUAL
            ]
            schedules = [s for _, s in shared] + ([schedule] if mine else [])
            devices.append(
                {
                    "name": device.name,
                    "desired": combined_desired(schedules, now),
                    "shared_with": [n for n, _ in shared] if mine else [],
                }
            )
        return {
            "plan": plan.name,
            "stage": stage.name,
            "stage_number": index + 1,
            "stage_count": len(plan.stages),
            "stage_started": started.isoformat(),
            "stage_day": day_number(started, today),
            "stage_days": stage.days,
            "grow_started": grow_started.isoformat(),
            "expected_end": expected_end(plan, index, started).isoformat(),
            "stage_check_due": max(due_date(started, stage.days), today).isoformat(),
            "devices": devices,
            "tasks": sorted(tasks, key=lambda t: t["due"]),
            "skipped_tasks": skipped,
        }

    async def end_grow(self, grow: str | None = None) -> None:
        """Stop a grow. Devices are left as they are."""
        found = self.grow(grow)
        plan = found.plan
        fields = self._grow_fields(found)
        self._clear_grow(found)
        self._log("grow", f"{fields['grow']} ended")
        self._changed()
        await self._fire(EVENT_GROW_ENDED, {**fields, "plan": plan.name if plan else None})

    async def rename_grow(self, name: str, grow: str | None = None) -> None:
        """Change a grow's label."""
        found = self.grow(grow)
        name = name.strip()
        if not name:
            raise GrowError("A grow needs a name")
        if any(g.id != found.id and g.name.casefold() == name.casefold() for g in self.grows):
            raise GrowError(f"There is already a grow called {name}")
        found.data["name"] = name
        self._changed()

    async def set_stage(
        self,
        stage_ref: str | int,
        started: date | None = None,
        include_past_tasks: bool = False,
        grow: str | None = None,
    ) -> None:
        """Jump to a stage of a running plan."""
        found, plan, previous = self._require_active(grow)
        stage = self._stage_or_raise(plan, stage_ref)
        history = found.data.setdefault("history", [])
        if started is None and history and history[-1]["stage_id"] == stage.id:
            # Going back to the stage we just left: undo the move instead of
            # restarting it, keeping its start date and its tasks' progress.
            entry = history.pop()
            self.rt["instances"] = [
                i for i in self.rt["instances"] if i.get("custom") or i.get("grow") != found.id
            ]
            found.data.update({k: entry[k] for k in ("stage_id", "stage_started", "stage_run")})
            self.rt["instances"].extend(entry["instances"])
            found.data["stage_check_notified"] = False
        else:
            self._enter_stage(found, plan, stage, started or self.today, include_past_tasks)
        self._log("stage", f"{found.name}: moved to {stage.name}")
        await self._after_stage_change(found, previous)

    async def advance_stage(self, grow: str | None = None) -> None:
        """Move a grow to the next stage."""
        found, plan, _ = self._require_active(grow)
        index = found.stage_index or 0
        if index + 1 >= len(plan.stages):
            raise GrowError("Already on the last stage")
        await self.set_stage(plan.stages[index + 1].id, grow=found.id)

    async def previous_stage(self, grow: str | None = None) -> None:
        """Move a grow back one stage, undoing the last advance when possible."""
        found, plan, _ = self._require_active(grow)
        index = found.stage_index or 0
        if index == 0:
            raise GrowError("Already on the first stage")
        await self.set_stage(plan.stages[index - 1].id, grow=found.id)

    async def restart_stage(self, grow: str | None = None) -> None:
        """Restart a grow's current stage from today."""
        found, _, stage = self._require_active(grow)
        # An explicit start date bypasses the "undo" path, so this is a true restart.
        await self.set_stage(stage.id, started=self.today, grow=found.id)

    async def _after_stage_change(self, grow: Grow, previous: Stage | None) -> None:
        plan, stage = grow.plan, grow.stage
        assert plan is not None and stage is not None
        self._changed()
        await self._fire(
            EVENT_STAGE_CHANGED,
            {
                **self._grow_fields(grow),
                "plan": plan.name,
                "stage": stage.name,
                "stage_number": (grow.stage_index or 0) + 1,
                "stage_count": len(plan.stages),
                "previous_stage": previous.name if previous else None,
                "expected_outcome": stage.outcome,
            },
        )
        await self.sync(force=True)

    # ------------------------------------------------------------------
    # Readings
    # ------------------------------------------------------------------

    async def record_reading(self, ph: float | None = None, ec: float | None = None) -> None:
        """Record a manual water reading. `ec` is in the system's display unit."""
        if ph is None and ec is None:
            raise GrowError("Enter a pH or EC value")
        if ph is not None and not 0 <= ph <= 14:
            raise GrowError("pH must be between 0 and 14")
        ec_canonical = None
        if ec is not None:
            if ec < 0:
                raise GrowError("EC cannot be negative")
            ec_canonical = units.to_canonical(ec, self.ec_unit)
        if ph is not None:
            self.rt["ph"] = ph
        if ec_canonical is not None:
            self.rt["ec"] = ec_canonical
            self.rt["ec_at"] = self.now.isoformat()
        self.rt["last_reading"] = self.now.isoformat()
        self.rt["reading_overdue_notified"] = False
        parts = []
        if ph is not None:
            parts.append(f"pH {ph:g}")
        if ec is not None:
            parts.append(f"EC {ec:g} {self.ec_unit}")
        self._log("reading", "Recorded " + ", ".join(parts))
        if self.readings is not None:
            self.readings.add(self.id, self.now, ph, ec_canonical)
        self._changed()
        await self.evaluate_alerts()

    @property
    def ec_updated(self) -> datetime | None:
        """Return when the EC reading was taken (None when unknown)."""
        if self.has_sensor("ec"):
            state = self.states.get(self._sensor_entity("ec") or "")
            return state.updated if state else None
        stamp = self.rt.get("ec_at") or self.rt.get("last_reading")
        return datetime.fromisoformat(stamp) if stamp else None

    @property
    def ec_stale(self) -> bool | None:
        """Return whether the EC reading is too old to dose by; None when there is none.

        A sensor that doesn't say when it last reported is trusted.
        """
        if self.ec is None:
            return None
        updated = self.ec_updated
        if updated is None:
            return not self.has_sensor("ec")
        return self.now - updated > timedelta(hours=self.data["ec_stale_hours"])

    def nutrient_dose(
        self, added: float, ec: float | None = None, target_ec: float | None = None
    ) -> dict[str, Any]:
        """Work out nutrients for topping the tank up with `added` water.

        `added` is in the system's volume unit; `ec` and `target_ec` are in the EC display
        unit. EC defaults to the current reading and the target to the middle of the
        running grows' combined EC range. Raises GrowError when something is missing.
        """
        capacity_l, unit, weight = self.data["capacity_l"], self.volume_unit, self.weight_unit
        if not capacity_l:
            raise GrowError("Set the tank capacity in Settings first")
        grows = [g for g in self.active_grows if g.stage is not None]
        if not grows:
            raise GrowError("Nothing is growing, so there is no stage to dose for")
        line = nutrient_calc.active_line(self.data["nutrients"])
        low, high, conflict = self._combined_range("ec")
        columns, stages = [], []
        for grow in grows:
            stage = grow.stage
            stage_low, stage_high = grow.range_for("ec")
            column = nutrient_calc.column_for(
                stage.stage_type, nutrient_calc.target_ec(stage_low, stage_high), line
            )
            columns.append(column)
            stages.append({"grow": grow.name, "stage": stage.name, "column": column["name"]})
        target = (
            units.to_canonical(target_ec, self.ec_unit)
            if target_ec is not None
            else nutrient_calc.target_ec(low, high)
        )
        if target is None:
            raise GrowError("The running grows have no EC range. Enter a target EC.")
        current = units.to_canonical(ec, self.ec_unit) if ec is not None else self.ec
        to_l = _litres_per(unit)
        try:
            result = nutrient_calc.calculate(
                line, columns, capacity_l, added * to_l, current, target
            )
        except ValueError as err:
            raise GrowError(str(err)) from None

        def show(mscm: float) -> float:
            return units.from_canonical(mscm, self.ec_unit)

        warnings = []
        if conflict:
            warnings.append(
                "The running grows' EC ranges don't overlap, so the oldest grow's range was used."
            )
        if (
            target_ec is not None
            and low is not None
            and high is not None
            and not low - 1e-9 <= target <= high + 1e-9
        ):
            warnings.append("That target is outside the running grows' EC range.")
        if result["concentrated"] and result["needs_nutrients"]:
            warnings.append(
                "That is stronger than the feeding chart for plain water because the tank "
                "is below target. Add the total amount to the tank, not per gallon of new water."
            )
        if not result["needs_nutrients"]:
            warnings.append("The tank will already be at or above the target, so add no nutrients.")
        return {
            "line": line["name"],
            "volume_unit": unit,
            "capacity": self.capacity,
            "added": added,
            "weight_unit": weight,
            "current_volume": round(result["existing_l"] / to_l, 2),
            "current_ec": show(current) if current is not None else None,
            "diluted_ec": show(result["diluted_ec"]),
            "target_ec": show(target),
            "ec_unit": self.ec_unit,
            "needs_nutrients": result["needs_nutrients"],
            "stages": stages,
            "products": [
                {
                    "id": p["id"],
                    "name": p["name"],
                    "short": p["short"],
                    "ml": round(p["ml"], 1),
                    "weight": round(p["g"] / _grams_per(weight), 1 if weight == "g" else 2),
                    "ml_per_unit": round(p["ml_per_gal" if unit == "gal" else "ml_per_l"], 2),
                    "weight_per_unit": round(
                        p["g_per_gal" if unit == "gal" else "g_per_l"] / _grams_per(weight),
                        2 if weight == "g" else 3,
                    ),
                }
                for p in result["products"]
            ],
            "warnings": warnings,
        }

    async def water_checked(self) -> None:
        """Note that the water was checked without changing any value."""
        self.rt["last_reading"] = self.now.isoformat()
        self.rt["reading_overdue_notified"] = False
        self._log("reading", "Water checked")
        self._changed()

    def smart_conditions(self) -> dict[str, dict[str, str]]:
        """Return the condition tasks that should exist right now, by key.

        These replace the old date-based "check pH", "monitor temperature" and "add
        nutrients if needed" tasks: a task only appears when there is something to do.
        Temperature and humidity get alerts (events and notifications), not tasks.
        """
        if not self.is_active:
            return {}
        found: dict[str, dict[str, str]] = {}
        if self.reading_overdue:
            found["reading"] = {
                "title": "Record a pH and EC reading",
                "note": "No pH or EC reading has been recorded recently. Measure the water "
                "and enter it in Grow Planner (or put a sensor on the system).",
            }
        for metric, label in (("ph", "pH"), ("ec", "EC")):
            if not self._alerts[metric].state["notified"]:
                continue
            value = self.value_of(metric)
            low, high = self.range_for(metric)
            if value is None:
                continue
            if low is not None and value < low:
                found[f"{metric}_low"] = {
                    "title": f"{label} is low: add nutrients"
                    if metric == "ec"
                    else "pH is low: raise it",
                    "note": f"{label} is below the target for this stage. Use the Nutrients "
                    "calculator in Grow Planner for a dose."
                    if metric == "ec"
                    else "pH is below the target for this stage. Add a little pH up, mix, and "
                    "measure again.",
                }
            elif high is not None and value > high:
                found[f"{metric}_high"] = {
                    "title": f"{label} is high: add water"
                    if metric == "ec"
                    else "pH is high: lower it",
                    "note": f"{label} is above the target for this stage. Top up with plain "
                    "water to dilute it, then measure again."
                    if metric == "ec"
                    else "pH is above the target for this stage. Add a little pH down, mix, "
                    "and measure again.",
                }
        return found

    async def evaluate_alerts(self) -> None:
        """Feed current values to the range alerts and fire any transitions."""
        if not self.is_active:
            return
        now = self.now
        for metric in METRICS:
            low, high = self.range_for(metric)
            transition = self._alerts[metric].update(now, self.value_of(metric), low, high)
            if transition is None:
                continue
            self._on_save()
            value = self.value_of(metric)
            if metric == "ec":
                value = units.from_canonical(value, self.ec_unit) if value is not None else None
                low = units.from_canonical(low, self.ec_unit) if low is not None else None
                high = units.from_canonical(high, self.ec_unit) if high is not None else None
            unit = {
                "ph": None,
                "ec": self.ec_unit,
                "temperature": self.temperature_unit,
                "humidity": "%",
            }[metric]
            self._log(
                "alert", f"{metric} {'out of' if transition == EVENT_OUT else 'back in'} range"
            )
            await self._fire(
                EVENT_OUT_OF_RANGE if transition == EVENT_OUT else EVENT_BACK_IN_RANGE,
                {"metric": metric, "value": value, "min": low, "max": high, "unit": unit},
            )

    # ------------------------------------------------------------------
    # Tasks
    # ------------------------------------------------------------------

    def _task_for(self, inst: dict[str, Any]) -> Task | None:
        """Resolve the Task template behind an instance."""
        if inst.get("custom"):
            custom = self.rt["custom_tasks"].get(inst["task_id"])
            if custom is None:
                return None
            return Task.from_dict({"id": inst["task_id"], "days": [1], **custom})
        grow = next((g for g in self.grows if g.id == inst.get("grow")), None)
        plan, stage = (grow.plan, grow.stage) if grow else (None, None)
        if plan is None or stage is None:
            return None
        if inst["task_id"] == STAGE_CHECK_ID:
            return self._stage_check_task(plan, stage)
        return next((t for t in stage.tasks if t.id == inst["task_id"]), None)

    def task_items(self, include_done: bool = True) -> list[dict[str, Any]]:
        """Return the instances as display dicts, soonest first."""
        today = self.today
        names = {g.id: g.name for g in self.grows}
        items = []
        for inst in self.rt["instances"]:
            task = self._task_for(inst)
            if task is None:
                continue
            done = inst.get("completed_on") is not None
            if done and not include_done:
                continue
            due = date.fromisoformat(inst["due"])
            items.append(
                {
                    "id": inst["id"],
                    "title": task.title,
                    "note": task.description,
                    "task_type": task.task_type,
                    "due": inst["due"],
                    "overdue": not done and due < today,
                    "done": done,
                    "every": task.every,
                    "custom": bool(inst.get("custom")),
                    "grow_id": inst.get("grow"),
                    "grow": names.get(inst.get("grow") or ""),
                }
            )
        return sorted(items, key=lambda i: (i["done"], i["due"]))

    def tasks_due(self) -> list[dict[str, Any]]:
        """Return open instances due today or earlier."""
        today = self.today.isoformat()
        return [t for t in self.task_items(include_done=False) if t["due"] <= today]

    def _instance(self, instance_id: str) -> dict[str, Any]:
        for inst in self.rt["instances"]:
            if inst["id"] == instance_id:
                return inst
        raise GrowError("Unknown task")

    async def complete_task(self, instance_id: str) -> None:
        """Check a task off; a recurring task schedules its next instance."""
        inst = self._instance(instance_id)
        if inst.get("completed_on"):
            return
        task = self._task_for(inst)
        today = self.today
        inst["completed_on"] = today.isoformat()
        nxt = None
        grow = next((g for g in self.grows if g.id == inst.get("grow")), None)
        if task is not None:
            started = (grow.stage_started if grow else None) or today
            nxt = next_instance(task, today, inst["stage_run"], started, self._make_id)
        if nxt is not None:
            self.rt["instances"].append(
                _dump_instance(
                    nxt,
                    custom=bool(inst.get("custom")),
                    grow=inst.get("grow"),
                )
            )
        title = task.title if task else ""
        self._log("task", f"Done: {title}" + (f" ({grow.name})" if grow else ""))
        self._changed()

    async def reopen_task(self, instance_id: str) -> None:
        """Undo a check-off. Recurring tasks cannot be reopened (their next one exists)."""
        inst = self._instance(instance_id)
        task = self._task_for(inst)
        if task is not None and task.recurring:
            raise GrowError("A repeating task can't be reopened; its next one is already scheduled")
        inst["completed_on"] = None
        self._changed()

    def delete_task(self, instance_id: str) -> None:
        """Remove an instance. For a repeating task this also stops the repeat."""
        inst = self._instance(instance_id)
        self.rt["instances"].remove(inst)
        if inst.get("custom") and not any(
            i["task_id"] == inst["task_id"] for i in self.rt["instances"]
        ):
            self.rt["custom_tasks"].pop(inst["task_id"], None)
        self._changed()

    async def add_custom_task(
        self,
        title: str,
        due: date | None = None,
        note: str = "",
        every: int = 0,
        grow: str | None = None,
    ) -> str:
        """Add your own task, optionally repeating every N days after completion.

        `grow` (an id or name) tags the task with a grow; without it the task is
        for the whole system.
        """
        title = title.strip()
        if not title:
            raise GrowError("A task needs a title")
        if every < 0:
            raise GrowError("Repeat interval cannot be negative")
        tagged = self.grow(grow) if grow else None
        task_id = f"custom_{self._make_id()}"
        self.rt["custom_tasks"][task_id] = {"title": title, "note": note, "every": every}
        inst = TaskInstance(self._make_id(), task_id, 0, due or self.today)
        self.rt["instances"].append(
            _dump_instance(inst, custom=True, grow=tagged.id if tagged else None)
        )
        self._changed()
        return inst.instance_id

    # ------------------------------------------------------------------
    # System upkeep
    # ------------------------------------------------------------------

    def upkeep_defs(self) -> list[dict[str, Any]]:
        """Return the enabled upkeep definitions (Home Keeper schedules them; see hk_tasks)."""
        return [m for m in self.data["maintenance"] if m["enabled"]]

    def upkeep_done_on(self, upkeep_id: str) -> date | None:
        """Return when this upkeep was last done, if ever."""
        done = self.rt["maintenance"].get(upkeep_id, {}).get("done")
        return date.fromisoformat(done) if done else None

    def upkeep_anchor(self, upkeep_id: str) -> date | None:
        """Return where this upkeep's clock runs from: last done, else when the system started."""
        return self.upkeep_done_on(upkeep_id) or self.system_started

    def upkeep_done(self, upkeep_id: str, day: date) -> bool:
        """Record upkeep as done on `day`; return whether that is news (newer than before)."""
        known = self.upkeep_done_on(upkeep_id)
        if known is not None and day <= known:
            return False
        self.rt["maintenance"].setdefault(upkeep_id, {})["done"] = day.isoformat()
        self._changed()
        return True

    def maintenance_view(self) -> list[dict[str, Any]]:
        """Return each upkeep task with when it was last done and when it is next due."""
        view = []
        for upkeep in self.data["maintenance"]:
            last = self.upkeep_done_on(upkeep["id"])
            anchor = self.upkeep_anchor(upkeep["id"])
            due = max(anchor + timedelta(days=upkeep["every"]), self.today) if anchor else None
            view.append(
                {
                    **upkeep,
                    "last_done": last.isoformat() if last else None,
                    "days_since": (self.today - last).days if last else None,
                    "next_due": due.isoformat() if due else None,
                }
            )
        return view

    # ------------------------------------------------------------------
    # Periodic work
    # ------------------------------------------------------------------

    async def tick(self) -> None:
        """Do whatever is due now; safe to call as often as you like."""
        await self.sync()
        await self.evaluate_alerts()
        await self._maybe_prompt_stage_check()
        await self._maybe_notify_reading_overdue()
        self._prune_done()

    async def _maybe_prompt_stage_check(self) -> None:
        for grow in self.active_grows:
            plan, stage, started = grow.plan, grow.stage, grow.stage_started
            if plan is None or stage is None or started is None:
                continue
            if grow.data.get("stage_check_notified") or self.today < due_date(started, stage.days):
                continue
            grow.data["stage_check_notified"] = True
            self._on_save()
            index = grow.stage_index or 0
            nxt = plan.stages[index + 1] if index + 1 < len(plan.stages) else None
            await self._fire(
                EVENT_STAGE_COMPLETE_DUE,
                {
                    **self._grow_fields(grow),
                    "plan": plan.name,
                    "stage": stage.name,
                    "next_stage": nxt.name if nxt else None,
                    "expected_outcome": stage.outcome,
                },
            )

    async def _maybe_notify_reading_overdue(self) -> None:
        if not self.reading_overdue or self.rt.get("reading_overdue_notified"):
            return
        self.rt["reading_overdue_notified"] = True
        self._on_save()
        last = self.last_reading
        await self._fire(
            EVENT_READING_OVERDUE,
            {
                "last_reading": last.isoformat() if last else None,
                "interval_days": self.data.get(
                    "reading_interval_days", DEFAULT_READING_INTERVAL_DAYS
                ),
            },
        )

    def _prune_done(self) -> None:
        cutoff = (self.today - timedelta(days=KEEP_DONE_DAYS)).isoformat()
        keep = [
            i
            for i in self.rt["instances"]
            if not i.get("completed_on") or i["completed_on"] >= cutoff
        ]
        if len(keep) != len(self.rt["instances"]):
            self.rt["instances"] = keep
            self._on_save()


def _dump_instance(inst: TaskInstance, custom: bool, grow: str | None) -> dict[str, Any]:
    return {
        "grow": grow,
        "id": inst.instance_id,
        "task_id": inst.task_id,
        "stage_run": inst.stage_run,
        "due": inst.due.isoformat(),
        "completed_on": inst.completed_on.isoformat() if inst.completed_on else None,
        "custom": custom,
    }
