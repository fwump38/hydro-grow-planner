"""Config flow for Hydro Grow Planner.

- Config entry: one grow system (its controlled devices and optional sensors).
- Options flow: alert/reminder settings and device management.
- Config subentry "plan": a grow plan, edited through a menu-driven flow.
"""

from __future__ import annotations

import copy
from typing import Any

from homeassistant.config_entries import (
    SOURCE_USER,
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    ConfigSubentryFlow,
    OptionsFlow,
    SubentryFlowResult,
)
from homeassistant.const import CONF_NAME
from homeassistant.core import callback
from homeassistant.helpers import selector
import voluptuous as vol

from .const import (
    CONF_AUTO_ADVANCE,
    CONF_DEVICE_ID,
    CONF_DEVICE_NAME,
    CONF_DEVICES,
    CONF_EC_SENSOR,
    CONF_EC_TOLERANCE,
    CONF_ENTITY_ID,
    CONF_NOTES,
    CONF_PH_SENSOR,
    CONF_PH_TOLERANCE,
    CONF_PLAN_NAME,
    CONF_READING_INTERVAL_DAYS,
    CONF_REMINDER_TIME,
    CONF_STAGES,
    CONF_TARGET_PH,
    DEFAULT_AUTO_ADVANCE,
    DEFAULT_EC_TOLERANCE,
    DEFAULT_PH_TOLERANCE,
    DEFAULT_READING_INTERVAL_DAYS,
    DEFAULT_REMINDER_TIME,
    DOMAIN,
    MODE_INTERVAL,
    MODE_MANUAL,
    MODE_TIME_WINDOW,
    SCHEDULE_MODES,
    STAGE_TYPES,
    SUBENTRY_TYPE_PLAN,
    TASK_TYPES,
)
from .models import DeviceSchedule, new_id
from .presets import PRESET_ROLES, PRESETS, build_from_preset
from .schedule import describe

CONTROLLABLE_DOMAINS = ["switch", "light", "fan", "input_boolean"]
SKIP = "__skip__"
BLANK = "blank"

# ---------------------------------------------------------------------------
# Shared selectors
# ---------------------------------------------------------------------------

DEVICES_SELECTOR = selector.EntitySelector(
    selector.EntitySelectorConfig(domain=CONTROLLABLE_DOMAINS, multiple=True)
)
SENSOR_SELECTOR = selector.EntitySelector(selector.EntitySelectorConfig(domain="sensor"))
TEXT = selector.TextSelector()
MULTILINE = selector.TextSelector(selector.TextSelectorConfig(multiline=True))
DAYS = selector.NumberSelector(
    selector.NumberSelectorConfig(min=1, max=365, step=1, mode=selector.NumberSelectorMode.BOX)
)
PH = selector.NumberSelector(
    selector.NumberSelectorConfig(min=0, max=14, step=0.1, mode=selector.NumberSelectorMode.BOX)
)
EC = selector.NumberSelector(
    selector.NumberSelectorConfig(
        min=0,
        max=20,
        step=0.1,
        mode=selector.NumberSelectorMode.BOX,
        unit_of_measurement="mS/cm",
    )
)


def _select(options: list[str], key: str) -> selector.SelectSelector:
    return selector.SelectSelector(
        selector.SelectSelectorConfig(
            options=options, translation_key=key, mode=selector.SelectSelectorMode.DROPDOWN
        )
    )


def _choice(options: dict[str, str]) -> selector.SelectSelector:
    """A dropdown of dynamic (untranslated) choices."""
    return selector.SelectSelector(
        selector.SelectSelectorConfig(
            options=[selector.SelectOptionDict(value=k, label=v) for k, v in options.items()],
            mode=selector.SelectSelectorMode.DROPDOWN,
        )
    )


def _seconds_to_duration(seconds: int) -> dict[str, int]:
    hours, rem = divmod(int(seconds), 3600)
    minutes, secs = divmod(rem, 60)
    return {"hours": hours, "minutes": minutes, "seconds": secs}


def _duration_to_seconds(value: dict[str, Any] | None) -> int:
    if not value:
        return 0
    return int(
        value.get("days", 0) * 86400
        + value.get("hours", 0) * 3600
        + value.get("minutes", 0) * 60
        + value.get("seconds", 0)
    )


def _entity_name(hass: Any, entity_id: str) -> str:
    state = hass.states.get(entity_id)
    if state and state.name:
        return state.name
    return entity_id.split(".", 1)[-1].replace("_", " ").title()


def _settings_schema(options: dict[str, Any]) -> vol.Schema:
    return vol.Schema(
        {
            vol.Required(
                CONF_PH_TOLERANCE, default=options.get(CONF_PH_TOLERANCE, DEFAULT_PH_TOLERANCE)
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=0.05, max=3, step=0.05, mode=selector.NumberSelectorMode.BOX
                )
            ),
            vol.Required(
                CONF_EC_TOLERANCE, default=options.get(CONF_EC_TOLERANCE, DEFAULT_EC_TOLERANCE)
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=0.05, max=5, step=0.05, mode=selector.NumberSelectorMode.BOX
                )
            ),
            vol.Required(
                CONF_READING_INTERVAL_DAYS,
                default=options.get(CONF_READING_INTERVAL_DAYS, DEFAULT_READING_INTERVAL_DAYS),
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=1, max=60, step=1, mode=selector.NumberSelectorMode.BOX
                )
            ),
            vol.Required(
                CONF_REMINDER_TIME, default=options.get(CONF_REMINDER_TIME, DEFAULT_REMINDER_TIME)
            ): selector.TimeSelector(),
            vol.Required(
                CONF_AUTO_ADVANCE, default=options.get(CONF_AUTO_ADVANCE, DEFAULT_AUTO_ADVANCE)
            ): selector.BooleanSelector(),
        }
    )


def _names_schema(entity_ids: list[str], names: dict[str, str]) -> vol.Schema:
    """One text field per device, keyed by entity id."""
    return vol.Schema({vol.Required(eid, default=names[eid]): TEXT for eid in entity_ids})


# ---------------------------------------------------------------------------
# Config flow: the grow system
# ---------------------------------------------------------------------------


class GrowConfigFlow(ConfigFlow, domain=DOMAIN):
    """Create a grow system."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize."""
        self._data: dict[str, Any] = {}
        self._entities: list[str] = []

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> GrowOptionsFlow:
        """Return the options flow."""
        return GrowOptionsFlow()

    @classmethod
    @callback
    def async_get_supported_subentry_types(
        cls, config_entry: ConfigEntry
    ) -> dict[str, type[ConfigSubentryFlow]]:
        """Plans are subentries."""
        return {SUBENTRY_TYPE_PLAN: PlanSubentryFlow}

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Name the system and pick its devices."""
        errors: dict[str, str] = {}
        if user_input is not None:
            self._async_abort_entries_match({CONF_NAME: user_input[CONF_NAME]})
            if not user_input.get(CONF_DEVICES):
                errors[CONF_DEVICES] = "no_devices"
            else:
                self._data = {
                    CONF_NAME: user_input[CONF_NAME],
                    CONF_PH_SENSOR: user_input.get(CONF_PH_SENSOR),
                    CONF_EC_SENSOR: user_input.get(CONF_EC_SENSOR),
                }
                self._entities = user_input[CONF_DEVICES]
                return await self.async_step_device_names()

        return self.async_show_form(
            step_id="user",
            data_schema=self.add_suggested_values_to_schema(
                vol.Schema(
                    {
                        vol.Required(CONF_NAME): TEXT,
                        vol.Required(CONF_DEVICES): DEVICES_SELECTOR,
                        vol.Optional(CONF_PH_SENSOR): SENSOR_SELECTOR,
                        vol.Optional(CONF_EC_SENSOR): SENSOR_SELECTOR,
                    }
                ),
                user_input or {CONF_NAME: "Grow System"},
            ),
            errors=errors,
        )

    async def async_step_device_names(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Give each device a short role name (e.g. "Side lights")."""
        if user_input is not None:
            self._data[CONF_DEVICES] = [
                {
                    CONF_DEVICE_ID: new_id(),
                    CONF_DEVICE_NAME: user_input[eid].strip() or _entity_name(self.hass, eid),
                    CONF_ENTITY_ID: eid,
                }
                for eid in self._entities
            ]
            return self.async_create_entry(
                title=self._data[CONF_NAME],
                data=self._data,
                options={
                    CONF_PH_TOLERANCE: DEFAULT_PH_TOLERANCE,
                    CONF_EC_TOLERANCE: DEFAULT_EC_TOLERANCE,
                    CONF_READING_INTERVAL_DAYS: DEFAULT_READING_INTERVAL_DAYS,
                    CONF_REMINDER_TIME: DEFAULT_REMINDER_TIME,
                    CONF_AUTO_ADVANCE: DEFAULT_AUTO_ADVANCE,
                },
            )
        names = {eid: _entity_name(self.hass, eid) for eid in self._entities}
        return self.async_show_form(
            step_id="device_names", data_schema=_names_schema(self._entities, names)
        )


# ---------------------------------------------------------------------------
# Options flow: settings and devices
# ---------------------------------------------------------------------------


class GrowOptionsFlow(OptionsFlow):
    """Edit settings and devices of a grow system."""

    def __init__(self) -> None:
        """Initialize."""
        self._new_entities: list[str] = []
        self._device_id: str | None = None

    @property
    def _devices(self) -> list[dict[str, Any]]:
        return list(self.config_entry.data.get(CONF_DEVICES, []))

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Top-level menu."""
        return self.async_show_menu(
            step_id="init",
            menu_options=["settings", "sensors", "add_devices", "rename_device", "remove_device"],
        )

    async def async_step_settings(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Tolerances, reminders, auto-advance."""
        if user_input is not None:
            return self.async_create_entry(data={**self.config_entry.options, **user_input})
        return self.async_show_form(
            step_id="settings", data_schema=_settings_schema(dict(self.config_entry.options))
        )

    async def async_step_sensors(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """pH/EC sensors (leave empty to log readings by hand)."""
        if user_input is not None:
            self.hass.config_entries.async_update_entry(
                self.config_entry,
                data={
                    **self.config_entry.data,
                    CONF_PH_SENSOR: user_input.get(CONF_PH_SENSOR),
                    CONF_EC_SENSOR: user_input.get(CONF_EC_SENSOR),
                },
            )
            return self.async_create_entry(data=dict(self.config_entry.options))
        return self.async_show_form(
            step_id="sensors",
            data_schema=self.add_suggested_values_to_schema(
                vol.Schema(
                    {
                        vol.Optional(CONF_PH_SENSOR): SENSOR_SELECTOR,
                        vol.Optional(CONF_EC_SENSOR): SENSOR_SELECTOR,
                    }
                ),
                {
                    k: v
                    for k, v in self.config_entry.data.items()
                    if k in (CONF_PH_SENSOR, CONF_EC_SENSOR) and v
                },
            ),
        )

    async def async_step_add_devices(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Add controlled devices. Existing plans leave new devices unmanaged."""
        errors: dict[str, str] = {}
        if user_input is not None:
            existing = {d[CONF_ENTITY_ID] for d in self._devices}
            self._new_entities = [e for e in user_input[CONF_DEVICES] if e not in existing]
            if not self._new_entities:
                errors[CONF_DEVICES] = "no_new_devices"
            else:
                return await self.async_step_new_device_names()
        return self.async_show_form(
            step_id="add_devices",
            data_schema=vol.Schema({vol.Required(CONF_DEVICES): DEVICES_SELECTOR}),
            errors=errors,
        )

    async def async_step_new_device_names(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Name the new devices."""
        if user_input is not None:
            devices = self._devices + [
                {
                    CONF_DEVICE_ID: new_id(),
                    CONF_DEVICE_NAME: user_input[eid].strip() or _entity_name(self.hass, eid),
                    CONF_ENTITY_ID: eid,
                }
                for eid in self._new_entities
            ]
            return self._save_devices(devices)
        names = {eid: _entity_name(self.hass, eid) for eid in self._new_entities}
        return self.async_show_form(
            step_id="new_device_names", data_schema=_names_schema(self._new_entities, names)
        )

    async def async_step_rename_device(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Rename a device or point it at a different entity."""
        if user_input is not None:
            devices = [
                {
                    **d,
                    CONF_DEVICE_NAME: user_input[CONF_DEVICE_NAME],
                    CONF_ENTITY_ID: user_input[CONF_ENTITY_ID],
                }
                if d[CONF_DEVICE_ID] == user_input[CONF_DEVICE_ID]
                else d
                for d in self._devices
            ]
            return self._save_devices(devices)
        if not self._devices:
            return self.async_abort(reason="no_devices")
        return self.async_show_form(
            step_id="rename_device",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_DEVICE_ID): _choice(
                        {
                            d[CONF_DEVICE_ID]: f"{d[CONF_DEVICE_NAME]} ({d[CONF_ENTITY_ID]})"
                            for d in self._devices
                        }
                    ),
                    vol.Required(CONF_DEVICE_NAME): TEXT,
                    vol.Required(CONF_ENTITY_ID): selector.EntitySelector(
                        selector.EntitySelectorConfig(domain=CONTROLLABLE_DOMAINS)
                    ),
                }
            ),
        )

    async def async_step_remove_device(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Stop controlling a device."""
        if user_input is not None:
            remove = set(user_input[CONF_DEVICES])
            return self._save_devices([d for d in self._devices if d[CONF_DEVICE_ID] not in remove])
        if not self._devices:
            return self.async_abort(reason="no_devices")
        return self.async_show_form(
            step_id="remove_device",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_DEVICES): selector.SelectSelector(
                        selector.SelectSelectorConfig(
                            options=[
                                selector.SelectOptionDict(
                                    value=d[CONF_DEVICE_ID], label=d[CONF_DEVICE_NAME]
                                )
                                for d in self._devices
                            ],
                            multiple=True,
                        )
                    )
                }
            ),
        )

    def _save_devices(self, devices: list[dict[str, Any]]) -> ConfigFlowResult:
        self.hass.config_entries.async_update_entry(
            self.config_entry, data={**self.config_entry.data, CONF_DEVICES: devices}
        )
        return self.async_create_entry(data=dict(self.config_entry.options))


# ---------------------------------------------------------------------------
# Subentry flow: a grow plan
# ---------------------------------------------------------------------------


class PlanSubentryFlow(ConfigSubentryFlow):
    """Create and edit a grow plan.

    Edits are accumulated in memory and written once, on "Save plan".
    """

    def __init__(self) -> None:
        """Initialize."""
        self._plan: dict[str, Any] = {}
        self._preset: str | None = None
        self._stage_id: str | None = None
        self._task_id: str | None = None
        self._stage_draft: dict[str, Any] = {}
        self._schedule_index = 0

    # -- helpers ------------------------------------------------------

    @property
    def _devices(self) -> list[dict[str, Any]]:
        return list(self._get_entry().data.get(CONF_DEVICES, []))

    @property
    def _stages(self) -> list[dict[str, Any]]:
        return self._plan.setdefault(CONF_STAGES, [])

    def _stage(self) -> dict[str, Any]:
        return next(s for s in self._stages if s["id"] == self._stage_id)

    def _stage_choices(self) -> dict[str, str]:
        return {
            s["id"]: f"{i}. {s['name']} ({s['days']} d)"
            for i, s in enumerate(self._stages, start=1)
        }

    def _name_taken(self, name: str) -> bool:
        current = self.context.get("subentry_id")
        return any(
            sub.data.get(CONF_PLAN_NAME, "").casefold() == name.casefold()
            for sub_id, sub in self._get_entry().subentries.items()
            if sub.subentry_type == SUBENTRY_TYPE_PLAN and sub_id != current
        )

    def _is_new(self) -> bool:
        return self.source == SOURCE_USER

    def _summary(self) -> str:
        """Markdown summary of the plan for the menu description."""
        devices = {d[CONF_DEVICE_ID]: d[CONF_DEVICE_NAME] for d in self._devices}
        lines = []
        if self._plan.get(CONF_TARGET_PH) is not None:
            lines.append(f"Target pH: {self._plan[CONF_TARGET_PH]}")
        if not self._stages:
            lines.append("_No stages yet._")
        for i, stage in enumerate(self._stages, start=1):
            ec = f", EC {stage['target_ec']}" if stage.get("target_ec") is not None else ""
            lines.append(
                f"**{i}. {stage['name']}** — {stage['days']} days{ec}, "
                f"{len(stage.get('tasks', []))} tasks"
            )
            for device_id, name in devices.items():
                sched = DeviceSchedule.from_dict(stage.get("schedules", {}).get(device_id))
                if sched.mode != MODE_MANUAL:
                    lines.append(f"  - {name}: {describe(sched)}")
        return "\n".join(lines)

    # -- entry points -------------------------------------------------

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> SubentryFlowResult:
        """New plan: name it and optionally start from a preset."""
        errors: dict[str, str] = {}
        if user_input is not None:
            name = user_input[CONF_PLAN_NAME].strip()
            if self._name_taken(name):
                errors[CONF_PLAN_NAME] = "name_taken"
            else:
                preset = user_input.get("preset", BLANK)
                if preset != BLANK:
                    self._preset = preset
                    self._plan = {CONF_PLAN_NAME: name}
                    return await self.async_step_map_roles()
                self._plan = {CONF_PLAN_NAME: name, CONF_NOTES: "", CONF_STAGES: []}
                return await self.async_step_menu()
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_PLAN_NAME): TEXT,
                    vol.Required("preset", default=BLANK): _select([BLANK, *PRESETS], "preset"),
                }
            ),
            errors=errors,
        )

    async def async_step_map_roles(
        self, user_input: dict[str, Any] | None = None
    ) -> SubentryFlowResult:
        """Map the preset's device roles onto this system's devices."""
        assert self._preset is not None
        if user_input is not None:
            role_map = {
                role: (None if value == SKIP else value) for role, value in user_input.items()
            }
            name = self._plan[CONF_PLAN_NAME]
            self._plan = build_from_preset(self._preset, role_map, new_id)
            self._plan[CONF_PLAN_NAME] = name
            return await self.async_step_menu()

        choices = {SKIP: "—", **{d[CONF_DEVICE_ID]: d[CONF_DEVICE_NAME] for d in self._devices}}
        schema: dict[Any, Any] = {}
        for role, label in PRESET_ROLES.items():
            guess = next(
                (
                    d[CONF_DEVICE_ID]
                    for d in self._devices
                    if label.casefold() in d[CONF_DEVICE_NAME].casefold()
                    or role in d[CONF_ENTITY_ID]
                ),
                SKIP,
            )
            schema[vol.Required(role, default=guess)] = _choice(choices)
        return self.async_show_form(step_id="map_roles", data_schema=vol.Schema(schema))

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> SubentryFlowResult:
        """Edit an existing plan."""
        self._plan = copy.deepcopy(dict(self._get_reconfigure_subentry().data))
        return await self.async_step_menu()

    # -- main menu ----------------------------------------------------

    async def async_step_menu(self, user_input: dict[str, Any] | None = None) -> SubentryFlowResult:
        """What to edit next."""
        options = ["details", "add_stage"]
        if self._stages:
            options += ["edit_stage", "tasks"]
        if len(self._stages) > 1:
            options.append("move_stage")
        if self._stages:
            options.append("remove_stage")
        options.append("save")
        return self.async_show_menu(
            step_id="menu",
            menu_options=options,
            description_placeholders={
                "name": self._plan.get(CONF_PLAN_NAME, ""),
                "summary": self._summary(),
            },
        )

    async def async_step_save(self, user_input: dict[str, Any] | None = None) -> SubentryFlowResult:
        """Write the plan."""
        if not self._stages:
            return self.async_show_menu(
                step_id="menu",
                menu_options=["details", "add_stage"],
                description_placeholders={
                    "name": self._plan.get(CONF_PLAN_NAME, ""),
                    "summary": "⚠️ Add at least one stage before saving.",
                },
            )
        title = self._plan[CONF_PLAN_NAME]
        if self._is_new():
            return self.async_create_entry(title=title, data=self._plan)
        return self.async_update_and_abort(
            self._get_entry(), self._get_reconfigure_subentry(), title=title, data=self._plan
        )

    async def async_step_details(
        self, user_input: dict[str, Any] | None = None
    ) -> SubentryFlowResult:
        """Plan name, target pH, notes."""
        errors: dict[str, str] = {}
        if user_input is not None:
            name = user_input[CONF_PLAN_NAME].strip()
            if self._name_taken(name):
                errors[CONF_PLAN_NAME] = "name_taken"
            else:
                self._plan[CONF_PLAN_NAME] = name
                self._plan[CONF_TARGET_PH] = user_input.get(CONF_TARGET_PH)
                self._plan[CONF_NOTES] = user_input.get(CONF_NOTES, "")
                return await self.async_step_menu()
        return self.async_show_form(
            step_id="details",
            data_schema=self.add_suggested_values_to_schema(
                vol.Schema(
                    {
                        vol.Required(CONF_PLAN_NAME): TEXT,
                        vol.Optional(CONF_TARGET_PH): PH,
                        vol.Optional(CONF_NOTES): MULTILINE,
                    }
                ),
                {k: v for k, v in self._plan.items() if v is not None},
            ),
            errors=errors,
        )

    # -- stages -------------------------------------------------------

    def _stage_schema(self) -> vol.Schema:
        return vol.Schema(
            {
                vol.Required("name"): TEXT,
                vol.Required("stage_type"): _select(STAGE_TYPES, "stage_type"),
                vol.Required("days"): DAYS,
                vol.Optional("target_ec"): EC,
                vol.Optional("outcome"): MULTILINE,
            }
        )

    @staticmethod
    def _schedule_schema() -> vol.Schema:
        return vol.Schema(
            {
                vol.Required("mode"): _select(SCHEDULE_MODES, "schedule_mode"),
                vol.Optional("on_time"): selector.TimeSelector(),
                vol.Optional("off_time"): selector.TimeSelector(),
                vol.Optional("interval_on"): selector.DurationSelector(),
                vol.Optional("interval_every"): selector.DurationSelector(),
            }
        )

    async def async_step_add_stage(
        self, user_input: dict[str, Any] | None = None
    ) -> SubentryFlowResult:
        """New stage: basics."""
        if user_input is not None:
            self._stage_id = None
            self._stage_draft = {
                "id": new_id(),
                "schedules": {},
                "tasks": [],
                **_stage_fields(user_input),
            }
            self._schedule_index = 0
            return await self.async_step_stage_schedule()
        suggested = {
            "stage_type": STAGE_TYPES[min(len(self._stages) + 1, len(STAGE_TYPES) - 1)],
            "days": 7,
        }
        return self.async_show_form(
            step_id="add_stage",
            data_schema=self.add_suggested_values_to_schema(self._stage_schema(), suggested),
        )

    async def async_step_edit_stage(
        self, user_input: dict[str, Any] | None = None
    ) -> SubentryFlowResult:
        """Pick a stage to edit."""
        if user_input is not None:
            self._stage_id = user_input["stage"]
            return await self.async_step_stage_basics()
        return self.async_show_form(
            step_id="edit_stage",
            data_schema=vol.Schema({vol.Required("stage"): _choice(self._stage_choices())}),
        )

    async def async_step_stage_basics(
        self, user_input: dict[str, Any] | None = None
    ) -> SubentryFlowResult:
        """Edit a stage's basics."""
        stage = self._stage()
        if user_input is not None:
            self._stage_draft = {**copy.deepcopy(stage), **_stage_fields(user_input)}
            self._schedule_index = 0
            return await self.async_step_stage_schedule()
        return self.async_show_form(
            step_id="stage_basics",
            data_schema=self.add_suggested_values_to_schema(
                self._stage_schema(), {k: v for k, v in stage.items() if v is not None}
            ),
            description_placeholders={"stage": stage["name"]},
        )

    async def async_step_stage_schedule(
        self, user_input: dict[str, Any] | None = None
    ) -> SubentryFlowResult:
        """One device's schedule for the stage being added/edited.

        Shown once per device; the device name is in the step description.
        """
        draft = self._stage_draft
        devices = self._devices
        errors: dict[str, str] = {}
        if user_input is not None:
            sched, error = _parse_schedule(user_input)
            if error:
                errors["base"] = error
            else:
                device_id = devices[self._schedule_index][CONF_DEVICE_ID]
                draft.setdefault("schedules", {})[device_id] = sched
                self._schedule_index += 1

        if not errors and self._schedule_index >= len(devices):
            return await self._async_commit_stage()

        device = devices[self._schedule_index]
        sched = DeviceSchedule.from_dict(draft.get("schedules", {}).get(device[CONF_DEVICE_ID]))
        # Re-show the submitted values only when they were rejected.
        suggested = (
            user_input
            if errors and user_input
            else {
                "mode": sched.mode,
                "on_time": sched.on_time,
                "off_time": sched.off_time,
                "interval_on": _seconds_to_duration(sched.interval_on),
                "interval_every": _seconds_to_duration(sched.interval_every),
            }
        )
        return self.async_show_form(
            step_id="stage_schedule",
            data_schema=self.add_suggested_values_to_schema(self._schedule_schema(), suggested),
            description_placeholders={
                "stage": draft.get("name", ""),
                "device": device[CONF_DEVICE_NAME],
                "entity_id": device[CONF_ENTITY_ID],
                "position": str(self._schedule_index + 1),
                "count": str(len(devices)),
            },
            errors=errors,
        )

    async def _async_commit_stage(self) -> SubentryFlowResult:
        draft = self._stage_draft
        if self._stage_id is None:
            self._stages.append(draft)
        else:
            index = next(i for i, s in enumerate(self._stages) if s["id"] == self._stage_id)
            self._stages[index] = draft
        self._stage_draft = {}
        return await self.async_step_menu()

    async def async_step_move_stage(
        self, user_input: dict[str, Any] | None = None
    ) -> SubentryFlowResult:
        """Move a stage to a new position."""
        if user_input is not None:
            stages = self._stages
            stage = next(s for s in stages if s["id"] == user_input["stage"])
            stages.remove(stage)
            position = int(user_input["position"]) - 1
            stages.insert(max(0, min(position, len(stages))), stage)
            return await self.async_step_menu()
        return self.async_show_form(
            step_id="move_stage",
            data_schema=vol.Schema(
                {
                    vol.Required("stage"): _choice(self._stage_choices()),
                    vol.Required("position"): _choice(
                        {str(i): str(i) for i in range(1, len(self._stages) + 1)}
                    ),
                }
            ),
        )

    async def async_step_remove_stage(
        self, user_input: dict[str, Any] | None = None
    ) -> SubentryFlowResult:
        """Remove a stage."""
        if user_input is not None:
            self._plan[CONF_STAGES] = [s for s in self._stages if s["id"] != user_input["stage"]]
            return await self.async_step_menu()
        return self.async_show_form(
            step_id="remove_stage",
            data_schema=vol.Schema({vol.Required("stage"): _choice(self._stage_choices())}),
        )

    # -- tasks --------------------------------------------------------

    async def async_step_tasks(
        self, user_input: dict[str, Any] | None = None
    ) -> SubentryFlowResult:
        """Pick the stage whose tasks to edit."""
        if user_input is not None:
            self._stage_id = user_input["stage"]
            return await self.async_step_task_menu()
        return self.async_show_form(
            step_id="tasks",
            data_schema=vol.Schema({vol.Required("stage"): _choice(self._stage_choices())}),
        )

    async def async_step_task_menu(
        self, user_input: dict[str, Any] | None = None
    ) -> SubentryFlowResult:
        """Task actions for one stage."""
        stage = self._stage()
        tasks = sorted(stage.get("tasks", []), key=lambda t: t["day"])
        listing = "\n".join(f"- Day {t['day']}: {t['title']}" for t in tasks) or "_No tasks yet._"
        options = ["add_task"]
        if tasks:
            options += ["edit_task", "remove_task"]
        options.append("menu")
        return self.async_show_menu(
            step_id="task_menu",
            menu_options=options,
            description_placeholders={"stage": stage["name"], "tasks": listing},
        )

    def _task_schema(self) -> vol.Schema:
        return vol.Schema(
            {
                vol.Required("day"): DAYS,
                vol.Required("task_type"): _select(TASK_TYPES, "task_type"),
                vol.Required("title"): TEXT,
                vol.Optional("note"): MULTILINE,
            }
        )

    async def async_step_add_task(
        self, user_input: dict[str, Any] | None = None
    ) -> SubentryFlowResult:
        """Add a task to the stage."""
        if user_input is not None:
            self._stage().setdefault("tasks", []).append(
                {"id": new_id(), **_task_fields(user_input)}
            )
            return await self.async_step_task_menu()
        return self.async_show_form(
            step_id="add_task",
            data_schema=self.add_suggested_values_to_schema(
                self._task_schema(), {"day": 1, "task_type": "reminder"}
            ),
            description_placeholders={"stage": self._stage()["name"]},
        )

    def _task_choices(self) -> dict[str, str]:
        tasks = sorted(self._stage().get("tasks", []), key=lambda t: t["day"])
        return {t["id"]: f"Day {t['day']}: {t['title']}" for t in tasks}

    async def async_step_edit_task(
        self, user_input: dict[str, Any] | None = None
    ) -> SubentryFlowResult:
        """Pick a task to edit."""
        if user_input is not None:
            self._task_id = user_input["task"]
            return await self.async_step_task_details()
        return self.async_show_form(
            step_id="edit_task",
            data_schema=vol.Schema({vol.Required("task"): _choice(self._task_choices())}),
        )

    async def async_step_task_details(
        self, user_input: dict[str, Any] | None = None
    ) -> SubentryFlowResult:
        """Edit a task."""
        tasks = self._stage()["tasks"]
        task = next(t for t in tasks if t["id"] == self._task_id)
        if user_input is not None:
            task.update(_task_fields(user_input))
            return await self.async_step_task_menu()
        return self.async_show_form(
            step_id="task_details",
            data_schema=self.add_suggested_values_to_schema(self._task_schema(), task),
        )

    async def async_step_remove_task(
        self, user_input: dict[str, Any] | None = None
    ) -> SubentryFlowResult:
        """Remove tasks."""
        if user_input is not None:
            remove = set(user_input["tasks"])
            stage = self._stage()
            stage["tasks"] = [t for t in stage.get("tasks", []) if t["id"] not in remove]
            return await self.async_step_task_menu()
        return self.async_show_form(
            step_id="remove_task",
            data_schema=vol.Schema(
                {
                    vol.Required("tasks"): selector.SelectSelector(
                        selector.SelectSelectorConfig(
                            options=[
                                selector.SelectOptionDict(value=k, label=v)
                                for k, v in self._task_choices().items()
                            ],
                            multiple=True,
                        )
                    )
                }
            ),
        )


def _stage_fields(user_input: dict[str, Any]) -> dict[str, Any]:
    return {
        "name": user_input["name"].strip(),
        "stage_type": user_input["stage_type"],
        "days": int(user_input["days"]),
        "target_ec": user_input.get("target_ec"),
        "outcome": user_input.get("outcome", ""),
    }


def _task_fields(user_input: dict[str, Any]) -> dict[str, Any]:
    return {
        "day": int(user_input["day"]),
        "task_type": user_input["task_type"],
        "title": user_input["title"].strip(),
        "note": user_input.get("note", ""),
    }


def _parse_schedule(values: dict[str, Any]) -> tuple[dict[str, Any], str | None]:
    """Validate one device section; return (schedule, error key)."""
    mode = values.get("mode", MODE_MANUAL)
    sched: dict[str, Any] = {"mode": mode}
    if mode == MODE_TIME_WINDOW:
        on, off = values.get("on_time"), values.get("off_time")
        if not on or not off:
            return sched, "window_required"
        if on == off:
            return sched, "window_empty"
        sched.update(on_time=on, off_time=off)
    elif mode == MODE_INTERVAL:
        on = _duration_to_seconds(values.get("interval_on"))
        every = _duration_to_seconds(values.get("interval_every"))
        if on <= 0 or every <= 0:
            return sched, "interval_required"
        if on >= every:
            return sched, "interval_too_long"
        sched.update(interval_on=on, interval_every=every)
    return sched, None
