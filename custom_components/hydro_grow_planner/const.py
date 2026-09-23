"""Constants for Hydro Grow Planner."""

from __future__ import annotations

from typing import Final

DOMAIN: Final = "hydro_grow_planner"

SUBENTRY_TYPE_PLAN: Final = "plan"

# Config entry data
CONF_DEVICES: Final = "devices"
CONF_DEVICE_ID: Final = "id"
CONF_DEVICE_NAME: Final = "name"
CONF_ENTITY_ID: Final = "entity_id"
CONF_PH_SENSOR: Final = "ph_sensor"
CONF_EC_SENSOR: Final = "ec_sensor"

# Config entry options
CONF_PH_TOLERANCE: Final = "ph_tolerance"
CONF_EC_TOLERANCE: Final = "ec_tolerance"
CONF_READING_INTERVAL_DAYS: Final = "reading_interval_days"
CONF_REMINDER_TIME: Final = "reminder_time"
CONF_AUTO_ADVANCE: Final = "auto_advance"

DEFAULT_PH_TOLERANCE: Final = 0.3
DEFAULT_EC_TOLERANCE: Final = 0.3
DEFAULT_READING_INTERVAL_DAYS: Final = 3
DEFAULT_REMINDER_TIME: Final = "08:00:00"
DEFAULT_AUTO_ADVANCE: Final = False

# Plan subentry data
CONF_PLAN_NAME: Final = "name"
CONF_TARGET_PH: Final = "target_ph"
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
    "plant_training",
    "trimming",
    "top_up",
    "flush_refill",
    "add_nutrients",
    "take_picture",
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
SERVICE_LOG_READING: Final = "log_reading"
SERVICE_SYNC_DEVICES: Final = "sync_devices"

ATTR_CONFIG_ENTRY_ID: Final = "config_entry_id"
ATTR_PLAN: Final = "plan"
ATTR_STAGE: Final = "stage"
ATTR_START_DATE: Final = "start_date"
ATTR_PH: Final = "ph"
ATTR_EC: Final = "ec"

STORAGE_VERSION: Final = 1
