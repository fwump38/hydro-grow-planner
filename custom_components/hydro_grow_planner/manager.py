"""Runtime for one grow system: which plan and stage is active, and what the devices should do.

Device control works on *desired state transitions*. A device is only switched
when its desired state changes (e.g. the light window opens), or on an explicit
full sync (HA start, grow/stage change, re-enabling schedule control, the sync
button). A manual flip therefore persists until the next scheduled change.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
import logging
from typing import Any
import uuid

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    ATTR_ENTITY_ID,
    SERVICE_TURN_OFF,
    SERVICE_TURN_ON,
    STATE_OFF,
    STATE_ON,
    STATE_UNAVAILABLE,
    STATE_UNKNOWN,
)
from homeassistant.core import CALLBACK_TYPE, Event, HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.helpers.event import (
    async_track_point_in_time,
    async_track_state_change_event,
    async_track_time_change,
    async_track_time_interval,
)
from homeassistant.helpers.start import async_at_started
from homeassistant.helpers.storage import Store
from homeassistant.util import dt as dt_util

from .const import (
    CONF_AUTO_ADVANCE,
    CONF_DEVICE_ID,
    CONF_DEVICE_NAME,
    CONF_DEVICES,
    CONF_EC_SENSOR,
    CONF_EC_TOLERANCE,
    CONF_ENTITY_ID,
    CONF_PH_SENSOR,
    CONF_PH_TOLERANCE,
    CONF_READING_INTERVAL_DAYS,
    CONF_REMINDER_TIME,
    DEFAULT_AUTO_ADVANCE,
    DEFAULT_EC_TOLERANCE,
    DEFAULT_PH_TOLERANCE,
    DEFAULT_READING_INTERVAL_DAYS,
    DEFAULT_REMINDER_TIME,
    DOMAIN,
    EVENT_GROW_ENDED,
    EVENT_STAGE_CHANGED,
    EVENT_TASKS_DUE,
    STORAGE_VERSION,
    SUBENTRY_TYPE_PLAN,
)
from .models import Plan, Stage, Task
from .schedule import desired_state, next_transition, parse_time

_LOGGER = logging.getLogger(__name__)

SAFETY_INTERVAL = timedelta(minutes=5)
SAVE_DELAY = 2

type GrowConfigEntry = ConfigEntry[GrowManager]


@dataclass(frozen=True, slots=True)
class GrowDevice:
    """A controlled device (any entity that supports turn_on/turn_off)."""

    id: str
    name: str
    entity_id: str


@dataclass(frozen=True, slots=True)
class TaskItem:
    """A plan task placed on the calendar for the current stage run."""

    uid: str
    task: Task
    due: date
    completed: bool


class GrowManager:
    """Holds and drives the state of one grow system."""

    def __init__(self, hass: HomeAssistant, entry: GrowConfigEntry) -> None:
        """Initialize."""
        self.hass = hass
        self.entry = entry
        self.devices = [
            GrowDevice(d[CONF_DEVICE_ID], d[CONF_DEVICE_NAME], d[CONF_ENTITY_ID])
            for d in entry.data.get(CONF_DEVICES, [])
        ]
        self.plans: dict[str, Plan] = {
            sub_id: Plan.from_dict(sub_id, dict(sub.data))
            for sub_id, sub in entry.subentries.items()
            if sub.subentry_type == SUBENTRY_TYPE_PLAN
        }
        self._store: Store[dict[str, Any]] = Store(
            hass, STORAGE_VERSION, f"{DOMAIN}.{entry.entry_id}"
        )
        self._state: dict[str, Any] = {}
        self._listeners: list[CALLBACK_TYPE] = []
        self._unsubs: list[CALLBACK_TYPE] = []
        self._transition_unsub: CALLBACK_TYPE | None = None

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def async_setup(self) -> None:
        """Load state and start timers."""
        self._state = await self._store.async_load() or {}
        self._state.setdefault("schedule_enabled", True)
        self._state.setdefault("last_desired", {})
        self._state.setdefault("completed", [])
        self._state.setdefault("dismissed", [])
        self._state.setdefault("custom_items", [])

        # The active plan or stage may have been deleted while we were unloaded.
        if self._state.get("plan_id") and self.active_plan is None:
            _LOGGER.warning("Active plan was removed; ending the grow")
            self._clear_grow()
        elif self.active_plan is not None and self.active_stage is None:
            if self.active_plan.stages:
                _LOGGER.warning("Active stage was removed; moving to the first stage")
                self._enter_stage(self.active_plan.stages[0], dt_util.now().date())
            else:
                self._clear_grow()

        reminder = parse_time(self.option(CONF_REMINDER_TIME, DEFAULT_REMINDER_TIME))
        self._unsubs.append(
            async_track_time_change(
                self.hass,
                self._async_reminder_tick,
                hour=reminder.hour,
                minute=reminder.minute,
                second=reminder.second,
            )
        )
        self._unsubs.append(
            async_track_time_change(
                self.hass, self._async_midnight_tick, hour=0, minute=0, second=5
            )
        )
        self._unsubs.append(
            async_track_time_interval(self.hass, self._async_safety_tick, SAFETY_INTERVAL)
        )
        sensors = [
            s
            for s in (self.entry.data.get(CONF_PH_SENSOR), self.entry.data.get(CONF_EC_SENSOR))
            if s
        ]
        if sensors:
            self._unsubs.append(
                async_track_state_change_event(self.hass, sensors, self._async_sensor_changed)
            )
        self._unsubs.append(async_at_started(self.hass, self._async_started))

    async def _async_started(self, _hass: HomeAssistant) -> None:
        """Run once HA is up (or immediately on reload)."""
        await self._async_maybe_auto_advance()
        await self.async_sync(force=True)

    async def async_unload(self) -> None:
        """Stop timers and flush state."""
        for unsub in self._unsubs:
            unsub()
        self._unsubs.clear()
        if self._transition_unsub:
            self._transition_unsub()
            self._transition_unsub = None
        await self._store.async_save(self._state)

    # ------------------------------------------------------------------
    # Listeners
    # ------------------------------------------------------------------

    @callback
    def async_add_listener(self, update_callback: CALLBACK_TYPE) -> CALLBACK_TYPE:
        """Register an entity update callback."""
        self._listeners.append(update_callback)
        return lambda: self._listeners.remove(update_callback)

    @callback
    def _notify(self) -> None:
        for update_callback in list(self._listeners):
            update_callback()

    @callback
    def _save(self) -> None:
        self._store.async_delay_save(lambda: self._state, SAVE_DELAY)

    # ------------------------------------------------------------------
    # Read-only state
    # ------------------------------------------------------------------

    def option(self, key: str, default: Any) -> Any:
        """Return a config entry option."""
        return self.entry.options.get(key, default)

    @property
    def active_plan(self) -> Plan | None:
        """Return the running plan."""
        return self.plans.get(self._state.get("plan_id") or "")

    @property
    def is_active(self) -> bool:
        """Return True when a grow is running."""
        return self.active_plan is not None and self.active_stage is not None

    @property
    def stage_index(self) -> int | None:
        """Return the 0-based index of the current stage."""
        plan = self.active_plan
        return plan.stage_index(self._state.get("stage_id")) if plan else None

    @property
    def active_stage(self) -> Stage | None:
        """Return the current stage."""
        index = self.stage_index
        plan = self.active_plan
        return plan.stages[index] if plan is not None and index is not None else None

    @property
    def grow_started(self) -> date | None:
        """Return the date the grow started."""
        value = self._state.get("grow_started")
        return date.fromisoformat(value) if value else None

    @property
    def stage_started(self) -> date | None:
        """Return the date the current stage started."""
        value = self._state.get("stage_started")
        return date.fromisoformat(value) if value else None

    @property
    def stage_day(self) -> int | None:
        """Return the 1-based day of the current stage."""
        started = self.stage_started
        if not self.is_active or started is None:
            return None
        return (dt_util.now().date() - started).days + 1

    @property
    def grow_day(self) -> int | None:
        """Return the 1-based day of the whole grow."""
        started = self.grow_started
        if not self.is_active or started is None:
            return None
        return (dt_util.now().date() - started).days + 1

    @property
    def stage_days_remaining(self) -> int | None:
        """Return the days left in the current stage (0 when overdue)."""
        stage, day = self.active_stage, self.stage_day
        if stage is None or day is None:
            return None
        return max(stage.days - day + 1, 0)

    @property
    def stage_progress(self) -> float | None:
        """Return the progress through the current stage as a percentage."""
        stage, day = self.active_stage, self.stage_day
        if stage is None or day is None or stage.days <= 0:
            return None
        return round(min(max(day - 1, 0) / stage.days, 1) * 100, 1)

    @property
    def expected_harvest(self) -> date | None:
        """Return the estimated end of the last stage."""
        plan, index, started = self.active_plan, self.stage_index, self.stage_started
        if plan is None or index is None or started is None:
            return None
        remaining = sum(s.days for s in plan.stages[index:])
        return started + timedelta(days=remaining)

    @property
    def schedule_enabled(self) -> bool:
        """Return True when the integration may switch devices."""
        return bool(self._state.get("schedule_enabled", True))

    def desired(self, device_id: str) -> bool | None:
        """Return the desired state of a device right now (None = unmanaged)."""
        stage = self.active_stage
        if stage is None:
            return None
        return desired_state(stage.schedule_for(device_id), dt_util.now())

    # -- water ---------------------------------------------------------

    def _sensor_value(self, conf_key: str) -> float | None:
        entity_id = self.entry.data.get(conf_key)
        if not entity_id:
            return None
        state = self.hass.states.get(entity_id)
        if state is None or state.state in (STATE_UNKNOWN, STATE_UNAVAILABLE):
            return None
        try:
            return float(state.state)
        except ValueError:
            return None

    @property
    def has_ph_sensor(self) -> bool:
        """Return True if pH comes from a sensor."""
        return bool(self.entry.data.get(CONF_PH_SENSOR))

    @property
    def has_ec_sensor(self) -> bool:
        """Return True if EC comes from a sensor."""
        return bool(self.entry.data.get(CONF_EC_SENSOR))

    @property
    def measured_ph(self) -> float | None:
        """Return the latest pH reading."""
        if self.has_ph_sensor:
            return self._sensor_value(CONF_PH_SENSOR)
        return self._state.get("ph")

    @property
    def measured_ec(self) -> float | None:
        """Return the latest EC reading."""
        if self.has_ec_sensor:
            return self._sensor_value(CONF_EC_SENSOR)
        return self._state.get("ec")

    @property
    def target_ph(self) -> float | None:
        """Return the plan's target pH."""
        plan = self.active_plan
        return plan.target_ph if plan and self.is_active else None

    @property
    def target_ec(self) -> float | None:
        """Return the stage's target EC."""
        stage = self.active_stage
        return stage.target_ec if stage else None

    @property
    def last_reading(self) -> datetime | None:
        """Return when a reading was last logged manually."""
        value = self._state.get("last_reading")
        return dt_util.parse_datetime(value) if value else None

    def _out_of_range(
        self, measured: float | None, target: float | None, tolerance: float
    ) -> bool | None:
        if measured is None or target is None:
            return None
        return abs(measured - target) > tolerance

    @property
    def ph_out_of_range(self) -> bool | None:
        """Return whether pH is outside target ± tolerance."""
        return self._out_of_range(
            self.measured_ph,
            self.target_ph,
            self.option(CONF_PH_TOLERANCE, DEFAULT_PH_TOLERANCE),
        )

    @property
    def ec_out_of_range(self) -> bool | None:
        """Return whether EC is outside target ± tolerance."""
        return self._out_of_range(
            self.measured_ec,
            self.target_ec,
            self.option(CONF_EC_TOLERANCE, DEFAULT_EC_TOLERANCE),
        )

    @property
    def reading_overdue(self) -> bool | None:
        """Return whether a manual water reading is due."""
        if self.has_ph_sensor and self.has_ec_sensor:
            return None
        if not self.is_active:
            return False
        interval = timedelta(
            days=self.option(CONF_READING_INTERVAL_DAYS, DEFAULT_READING_INTERVAL_DAYS)
        )
        last = self.last_reading
        if last is None:
            started = self.grow_started
            if started is None:
                return False
            last = dt_util.start_of_local_day(started)
        return dt_util.now() - last >= interval

    # -- tasks ---------------------------------------------------------

    @property
    def task_items(self) -> list[TaskItem]:
        """Return the current stage's tasks with due dates."""
        stage, started = self.active_stage, self.stage_started
        if stage is None or started is None:
            return []
        run = self._state.get("stage_run", "")
        completed = set(self._state["completed"])
        dismissed = set(self._state["dismissed"])
        items = []
        for task in stage.tasks:
            uid = f"task_{run}_{task.id}"
            if uid in dismissed:
                continue
            items.append(
                TaskItem(
                    uid=uid,
                    task=task,
                    due=started + timedelta(days=task.day - 1),
                    completed=uid in completed,
                )
            )
        return items

    @property
    def custom_items(self) -> list[dict[str, Any]]:
        """Return user-added to-do items."""
        return self._state["custom_items"]

    def tasks_due(self, on: date | None = None) -> list[TaskItem]:
        """Return open tasks due on or before the given day."""
        on = on or dt_util.now().date()
        return [t for t in self.task_items if not t.completed and t.due <= on]

    # ------------------------------------------------------------------
    # Commands
    # ------------------------------------------------------------------

    def _plan_or_raise(self, plan_ref: str) -> Plan:
        """Find a plan by subentry id or (case-insensitive) name."""
        if plan_ref in self.plans:
            return self.plans[plan_ref]
        for plan in self.plans.values():
            if plan.name.casefold() == plan_ref.casefold():
                return plan
        raise ServiceValidationError(
            translation_domain=DOMAIN,
            translation_key="unknown_plan",
            translation_placeholders={"plan": plan_ref},
        )

    def _stage_or_raise(self, plan: Plan, stage_ref: str | int) -> Stage:
        """Find a stage by id, name or 1-based number."""
        if isinstance(stage_ref, int) or str(stage_ref).isdigit():
            index = int(stage_ref) - 1
            if 0 <= index < len(plan.stages):
                return plan.stages[index]
        else:
            for stage in plan.stages:
                if stage_ref in (stage.id, stage.name) or (
                    stage.name.casefold() == str(stage_ref).casefold()
                ):
                    return stage
        raise ServiceValidationError(
            translation_domain=DOMAIN,
            translation_key="unknown_stage",
            translation_placeholders={"stage": str(stage_ref), "plan": plan.name},
        )

    @callback
    def _enter_stage(self, stage: Stage, started: date) -> None:
        self._state["stage_id"] = stage.id
        self._state["stage_started"] = started.isoformat()
        self._state["stage_run"] = uuid.uuid4().hex[:8]
        self._state["completed"] = []
        self._state["dismissed"] = []

    @callback
    def _clear_grow(self) -> None:
        for key in ("plan_id", "stage_id", "stage_started", "grow_started", "stage_run"):
            self._state.pop(key, None)
        self._state["completed"] = []
        self._state["dismissed"] = []
        self._state["last_desired"] = {}

    async def async_start_grow(
        self,
        plan_ref: str,
        stage_ref: str | int | None = None,
        start_date: date | None = None,
    ) -> None:
        """Start a plan, optionally at a later stage or backdated."""
        plan = self._plan_or_raise(plan_ref)
        if not plan.stages:
            raise ServiceValidationError(
                translation_domain=DOMAIN,
                translation_key="plan_has_no_stages",
                translation_placeholders={"plan": plan.name},
            )
        stage = plan.stages[0] if stage_ref is None else self._stage_or_raise(plan, stage_ref)
        started = start_date or dt_util.now().date()
        self._state["plan_id"] = plan.id
        self._state["grow_started"] = started.isoformat()
        self._enter_stage(stage, started)
        await self._async_after_stage_change(previous=None)

    async def async_end_grow(self) -> None:
        """Stop the running grow. Devices are left as they are."""
        plan = self.active_plan
        self._clear_grow()
        self._save()
        self._reschedule_transition()
        self._notify()
        self.hass.bus.async_fire(
            EVENT_GROW_ENDED,
            {"config_entry_id": self.entry.entry_id, "plan": plan.name if plan else None},
        )

    async def async_set_stage(self, stage_ref: str | int, start_date: date | None = None) -> None:
        """Jump to a stage of the running plan."""
        plan = self._require_active()
        previous = self.active_stage
        stage = self._stage_or_raise(plan, stage_ref)
        self._enter_stage(stage, start_date or dt_util.now().date())
        await self._async_after_stage_change(previous)

    async def async_advance_stage(self) -> None:
        """Move to the next stage."""
        plan = self._require_active()
        index = self.stage_index or 0
        if index + 1 >= len(plan.stages):
            raise ServiceValidationError(translation_domain=DOMAIN, translation_key="last_stage")
        await self.async_set_stage(plan.stages[index + 1].id)

    async def async_previous_stage(self) -> None:
        """Move back to the previous stage."""
        plan = self._require_active()
        index = self.stage_index or 0
        if index == 0:
            raise ServiceValidationError(translation_domain=DOMAIN, translation_key="first_stage")
        await self.async_set_stage(plan.stages[index - 1].id)

    async def async_restart_stage(self) -> None:
        """Restart the current stage from day 1."""
        self._require_active()
        stage = self.active_stage
        assert stage is not None
        await self.async_set_stage(stage.id)

    def _require_active(self) -> Plan:
        plan = self.active_plan
        if plan is None or not self.is_active:
            raise ServiceValidationError(
                translation_domain=DOMAIN, translation_key="no_active_grow"
            )
        return plan

    async def _async_after_stage_change(self, previous: Stage | None) -> None:
        self._state["last_desired"] = {}
        self._save()
        plan, stage = self.active_plan, self.active_stage
        assert plan is not None and stage is not None
        self.hass.bus.async_fire(
            EVENT_STAGE_CHANGED,
            {
                "config_entry_id": self.entry.entry_id,
                "plan": plan.name,
                "stage": stage.name,
                "stage_number": (self.stage_index or 0) + 1,
                "stage_count": len(plan.stages),
                "previous_stage": previous.name if previous else None,
                "expected_outcome": stage.outcome,
            },
        )
        await self.async_sync(force=True)

    async def async_set_schedule_enabled(self, enabled: bool) -> None:
        """Enable or disable device control."""
        self._state["schedule_enabled"] = enabled
        self._save()
        if enabled:
            await self.async_sync(force=True)
        else:
            self._notify()

    async def async_log_reading(self, ph: float | None = None, ec: float | None = None) -> None:
        """Record a manual water reading."""
        if ph is not None:
            self._state["ph"] = ph
        if ec is not None:
            self._state["ec"] = ec
        self._state["last_reading"] = dt_util.now().isoformat()
        self._save()
        self._notify()

    # -- to-do ---------------------------------------------------------

    async def async_set_task_completed(self, uid: str, completed: bool) -> None:
        """Mark a plan task done or not done."""
        done = set(self._state["completed"])
        if completed:
            done.add(uid)
        else:
            done.discard(uid)
        self._state["completed"] = sorted(done)
        self._save()
        self._notify()

    async def async_dismiss_task(self, uid: str) -> None:
        """Hide a plan task for this stage run."""
        self._state["dismissed"] = sorted({*self._state["dismissed"], uid})
        self._save()
        self._notify()

    async def async_upsert_custom_item(self, item: dict[str, Any]) -> None:
        """Create or update a user-added to-do item."""
        items = [i for i in self.custom_items if i["uid"] != item["uid"]]
        existing = next((i for i in self.custom_items if i["uid"] == item["uid"]), None)
        if existing is not None:
            items.insert(self.custom_items.index(existing), item)
        else:
            items.append(item)
        self._state["custom_items"] = items
        self._save()
        self._notify()

    async def async_delete_custom_items(self, uids: set[str]) -> None:
        """Delete user-added to-do items."""
        self._state["custom_items"] = [i for i in self.custom_items if i["uid"] not in uids]
        self._save()
        self._notify()

    # ------------------------------------------------------------------
    # Device sync
    # ------------------------------------------------------------------

    async def async_sync(self, force: bool = False) -> None:
        """Bring devices in line with the schedule.

        Without force, only devices whose desired state changed since the last
        evaluation are switched; with force, every managed device is asserted.
        """
        last: dict[str, bool] = self._state["last_desired"]
        changed = False
        for device in self.devices:
            want = self.desired(device.id)
            if want is None:
                if last.pop(device.id, None) is not None:
                    changed = True
                continue
            if not force and last.get(device.id) == want:
                continue
            last[device.id] = want
            changed = True
            if self.schedule_enabled:
                await self._async_switch(device, want)
        if changed:
            self._save()
        self._reschedule_transition()
        self._notify()

    async def _async_switch(self, device: GrowDevice, on: bool) -> None:
        state = self.hass.states.get(device.entity_id)
        if state is None or state.state == STATE_UNAVAILABLE:
            _LOGGER.warning("%s is unavailable; cannot switch it", device.entity_id)
            return
        if state.state == (STATE_ON if on else STATE_OFF):
            return
        _LOGGER.debug("Turning %s %s", device.entity_id, "on" if on else "off")
        try:
            await self.hass.services.async_call(
                device.entity_id.split(".", 1)[0],
                SERVICE_TURN_ON if on else SERVICE_TURN_OFF,
                {ATTR_ENTITY_ID: device.entity_id},
                blocking=True,
            )
        except HomeAssistantError as err:
            _LOGGER.error("Failed to switch %s: %s", device.entity_id, err)

    @callback
    def _reschedule_transition(self) -> None:
        if self._transition_unsub:
            self._transition_unsub()
            self._transition_unsub = None
        stage = self.active_stage
        if stage is None:
            return
        now = dt_util.now()
        upcoming = [
            t
            for device in self.devices
            if (t := next_transition(stage.schedule_for(device.id), now)) is not None
        ]
        if upcoming:
            self._transition_unsub = async_track_point_in_time(
                self.hass, self._async_transition_tick, min(upcoming)
            )

    async def _async_transition_tick(self, _now: datetime) -> None:
        self._transition_unsub = None
        await self.async_sync()

    async def _async_safety_tick(self, _now: datetime) -> None:
        """Catch clock jumps or missed timers; never re-asserts unchanged state."""
        await self.async_sync()

    async def _async_midnight_tick(self, _now: datetime) -> None:
        await self._async_maybe_auto_advance()
        self._notify()

    async def _async_maybe_auto_advance(self) -> None:
        if not self.option(CONF_AUTO_ADVANCE, DEFAULT_AUTO_ADVANCE):
            return
        plan, stage, day = self.active_plan, self.active_stage, self.stage_day
        if plan is None or stage is None or day is None:
            return
        index = self.stage_index or 0
        if day > stage.days and index + 1 < len(plan.stages):
            started = (self.stage_started or dt_util.now().date()) + timedelta(days=stage.days)
            await self.async_set_stage(plan.stages[index + 1].id, start_date=started)

    async def _async_reminder_tick(self, _now: datetime) -> None:
        due = self.tasks_due()
        needs_reading = bool(self.reading_overdue)
        if not due and not needs_reading:
            return
        today = dt_util.now().date()
        plan, stage = self.active_plan, self.active_stage
        self.hass.bus.async_fire(
            EVENT_TASKS_DUE,
            {
                "config_entry_id": self.entry.entry_id,
                "plan": plan.name if plan else None,
                "stage": stage.name if stage else None,
                "tasks": [
                    {
                        "title": item.task.title,
                        "task_type": item.task.task_type,
                        "note": item.task.note,
                        "due": item.due.isoformat(),
                        "overdue": item.due < today,
                    }
                    for item in due
                ],
                "reading_overdue": needs_reading,
            },
        )

    @callback
    def _async_sensor_changed(self, _event: Event) -> None:
        self._notify()
