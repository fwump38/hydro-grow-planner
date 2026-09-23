"""Constants for Hydro Grow Planner."""

from __future__ import annotations

from typing import Final

DOMAIN: Final = "hydro_grow_planner"

SUBENTRY_TYPE_PLAN: Final = "plan"

# Config entry data
CONF_DEVICES: Final = "devices"
CONF_DEVICE_ID: Final = "id"
CONF_DEVICE_NAME: Final = "name"
CONF_DEVICE_LIGHT: Final = "light"
CONF_ENTITY_ID: Final = "entity_id"
CONF_PH_SENSOR: Final = "ph_sensor"
CONF_EC_SENSOR: Final = "ec_sensor"
CONF_TEMPERATURE_SENSOR: Final = "temperature_sensor"
CONF_HUMIDITY_SENSOR: Final = "humidity_sensor"

# Config entry options
CONF_READING_INTERVAL_DAYS: Final = "reading_interval_days"
CONF_REMINDER_TIME: Final = "reminder_time"

DEFAULT_READING_INTERVAL_DAYS: Final = 3
DEFAULT_REMINDER_TIME: Final = "08:00:00"

# Plan subentry data
CONF_PLAN_NAME: Final = "name"
CONF_PH_MIN: Final = "ph_min"
CONF_PH_MAX: Final = "ph_max"
CONF_TEMP_MIN: Final = "temp_min"
CONF_TEMP_MAX: Final = "temp_max"
CONF_TEMP_UNIT: Final = "temp_unit"
CONF_HUMIDITY_MIN: Final = "humidity_min"
CONF_HUMIDITY_MAX: Final = "humidity_max"
CONF_NOTES: Final = "notes"
CONF_STAGES: Final = "stages"

# Device schedule modes
MODE_MANUAL: Final = "manual"
MODE_OFF: Final = "off"
MODE_ALWAYS_ON: Final = "always_on"
MODE_TIME_WINDOW: Final = "time_window"
MODE_INTERVAL: Final = "interval"
SCHEDULE_MODES: Final = [
    MODE_MANUAL,
    MODE_OFF,
    MODE_ALWAYS_ON,
    MODE_TIME_WINDOW,
    MODE_INTERVAL,
]

STAGE_TYPES: Final = [
    "germination",
    "sprouting",
    "seedling",
    "vegetative",
    "flowering",
    "fruiting",
    "ripening",
    "harvest",
    "other",
]

TASK_TYPES: Final = [
    "reminder",
    "refill",
    "flush_refill",
    "plant_training",
    "trimming",
    "take_picture",
    "add_nutrients",
    "harvest",
]

NO_PLAN: Final = "none"

# Events
EVENT_STAGE_CHANGED: Final = f"{DOMAIN}_stage_changed"
EVENT_TASKS_DUE: Final = f"{DOMAIN}_tasks_due"
EVENT_GROW_ENDED: Final = f"{DOMAIN}_grow_ended"

# Services
SERVICE_START_GROW: Final = "start_grow"
SERVICE_END_GROW: Final = "end_grow"
SERVICE_SET_STAGE: Final = "set_stage"
SERVICE_ADVANCE_STAGE: Final = "advance_stage"
SERVICE_PREVIOUS_STAGE: Final = "previous_stage"
SERVICE_LOG_READING: Final = "log_reading"
SERVICE_SYNC_DEVICES: Final = "sync_devices"

ATTR_CONFIG_ENTRY_ID: Final = "config_entry_id"
ATTR_PLAN: Final = "plan"
ATTR_STAGE: Final = "stage"
ATTR_START_DATE: Final = "start_date"
ATTR_NIGHT_LIGHTING: Final = "night_lighting"
ATTR_PH: Final = "ph"
ATTR_EC: Final = "ec"

STORAGE_VERSION: Final = 1
