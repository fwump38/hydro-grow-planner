"""Constants for Hydro Grow Planner."""

from __future__ import annotations

from typing import Final

APP_SLUG: Final = "hydro_grow_planner"

NO_PLAN: Final = "none"

DEFAULT_READING_INTERVAL_DAYS: Final = 3
DEFAULT_REMINDER_TIME: Final = "08:00:00"

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

# How a plan is harvested: everything at once, then start over ("once"), or a little at
# a time while the plants keep growing ("continuous": cut-and-come-again, picking fruit).
HARVEST_ONCE: Final = "once"
HARVEST_CONTINUOUS: Final = "continuous"
HARVEST_STYLES: Final = [HARVEST_ONCE, HARVEST_CONTINUOUS]

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

# Events fired on the Home Assistant bus (documented in the README).
EVENT_PREFIX: Final = f"{APP_SLUG}_"
EVENT_TASKS_DUE: Final = f"{EVENT_PREFIX}tasks_due"
EVENT_TASK_CREATED: Final = f"{EVENT_PREFIX}task_created"
EVENT_TASK_COMPLETED: Final = f"{EVENT_PREFIX}task_completed"
EVENT_STAGE_COMPLETE_DUE: Final = f"{EVENT_PREFIX}stage_complete_due"
EVENT_READING_OVERDUE: Final = f"{EVENT_PREFIX}reading_overdue"
EVENT_OUT_OF_RANGE: Final = f"{EVENT_PREFIX}out_of_range"
EVENT_BACK_IN_RANGE: Final = f"{EVENT_PREFIX}back_in_range"
EVENT_STAGE_CHANGED: Final = f"{EVENT_PREFIX}stage_changed"
EVENT_GROW_STARTED: Final = f"{EVENT_PREFIX}grow_started"
EVENT_GROW_ENDED: Final = f"{EVENT_PREFIX}grow_ended"

# EC is stored and compared in mS/cm. Each unit maps to a factor from mS/cm and a
# number of decimals to display.
EC_MS_CM: Final = "mS/cm"
EC_US_CM: Final = "µS/cm"
EC_CF: Final = "CF"
EC_PPM_500: Final = "ppm 500"
EC_PPM_700: Final = "ppm 700"
EC_UNITS: Final = [EC_MS_CM, EC_US_CM, EC_CF, EC_PPM_500, EC_PPM_700]
DEFAULT_EC_UNIT: Final = EC_MS_CM
