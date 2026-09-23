# Hydro Grow Planner

[![HACS Custom](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://hacs.xyz/docs/faq/custom_repositories)
[![Validate](https://github.com/fwump38/hydro-grow-planner/actions/workflows/validate.yml/badge.svg)](https://github.com/fwump38/hydro-grow-planner/actions/workflows/validate.yml)

A Home Assistant integration for running hydroponic grows from a **grow plan**: an ordered set of
stages, each with its own light/pump schedule, target EC, expected outcome and day-by-day tasks.
It tracks where you are in the grow, switches your devices on schedule, puts each stage's tasks on a
to-do list with due dates, and flags pH/EC readings that drift out of range.

It was built to replace the app for an Elfsys tower (three outlets: side lights, center lights, water
pump), but works with any set of switches, lights, fans or input booleans.

## Installation

### HACS (recommended)

1. In HACS, open the menu → **Custom repositories**, add
   `https://github.com/fwump38/hydro-grow-planner` with type **Integration**.
2. Install **Hydro Grow Planner** and restart Home Assistant.
3. Go to **Settings → Devices & services → Add integration → Hydro Grow Planner**.

### Manual

Copy `custom_components/hydro_grow_planner` into your `config/custom_components/` folder and restart.

Requires Home Assistant 2025.8 or newer.

## Setup

**1. Add a grow system.** Give it a name, pick the devices the plan should drive, and optionally pH, EC,
room temperature and room humidity sensors. Leave pH/EC empty to log readings by hand. Then give each device a short name, such
as "Side lights", and tick which devices are **lights** (they follow the Night lighting switch).

**2. Add a grow plan.** On the integration's page, choose **Add grow plan**. Start blank or from one
of the built-in presets: Bell Pepper, Leafy Greens, Lettuce, Pepper, Spinach and Tomato, taken from
the Elfsys Grow Cloud app's templates. Each preset has every stage, the light and pump schedules,
the expected outcomes, the pH and room-temperature ranges, each stage's EC range, and the full task
list with notes. Elfsys gives no humidity guidance, so humidity ranges start empty. When
you use a preset, you match its roles (center lights, side lights, water pump) to your devices.

**3. Edit the plan** at any time with the plan's ⋮ → **Reconfigure** menu:

| Menu | What it does |
|---|---|
| Name, pH, temperature, humidity and notes | Plan-level ranges: pH, room temperature (in your Home Assistant unit) and room humidity. |
| Add / Edit a stage | Name, type, estimated days, EC range, expected outcome, then one schedule form per device. |
| Edit tasks | Add, edit or remove tasks for a stage. Each task has a type, title, method and note, and runs on one or more days of the stage (e.g. `1, 4, 7`), optionally repeating every *N* days until a given day or the end of the stage. |
| Reorder / Remove a stage | Stage order is the plan's order. |
| Save plan | Nothing is written until you save. |

Each device has one of these modes in each stage:

| Mode | Behaviour |
|---|---|
| Not managed | The device is left alone. |
| Off / Always on | Held off or on for the whole stage. |
| Time window | On between two times. Windows can cross midnight, e.g. 22:00–04:00. |
| Interval | On for *X* every *Y*, repeating from midnight. For example, 15 min every 3 h is on at 00:00, 03:00, 06:00, and so on. |

**4. Start a grow** by choosing the plan in the **Plan** select, or with the `start_grow` action. That
action can also start at a later stage or backdate the start.

## How device control works

The integration switches a device only when its **scheduled state changes**. For example, it turns
the lights on when the window opens and off when it closes. If you flip a device by hand, your change
stays until the next scheduled change. Nothing re-asserts the schedule every minute.

A full re-sync happens when Home Assistant starts, when a grow starts, when the stage changes, when
**Schedule control** is switched back on, and when you press **Sync devices**.

Turn off **Schedule control** to keep tracking the grow without touching any device.

Turn on **Night lighting** to run the lights at night. Every light's on/off window moves by 12
hours, so a 06:00–21:00 window becomes 18:00–09:00. Devices that aren't marked as lights, such as
the pump, keep their schedules. You can switch it at any time, or set it when starting a grow.

## Entities

For each grow system:

| Entity | Purpose |
|---|---|
| `select` Plan / Stage | Start, switch or end a grow. Jump to a stage. |
| `button` Next / Previous / Restart stage, Sync devices, Water checked | Stage control and device sync. *Water checked* stamps a manual reading without changing the values. |
| `switch` Schedule control, Night lighting | Enable or disable device switching; run the lights at night. |
| `todo` Tasks | The current stage's tasks. Each day a task runs on is its own item, due on *stage start + day − 1*. You can also add your own items here. |
| `sensor` Active plan, Current stage, Stage day, Stage days remaining, Stage progress, Grow day, Grow started, Expected end, pH min/max, EC min/max, Tasks due, Next task | Status. *Current stage* has the full stage details, including each device's schedule, as attributes. |
| `number` Measured pH / EC | Manual readings. Only created when no sensor is configured. |
| `binary_sensor` pH / EC out of range, Water reading overdue | Problems. pH is compared with the plan's range and EC with the stage's range. |
| `binary_sensor` Temperature / Humidity out of range | Only created when a room temperature or humidity sensor is configured. The current value and the range are attributes. |
| `binary_sensor` *Device* scheduled | Whether the schedule wants that device on right now. Compare it with the device to spot a manual override. |

**Previous stage** (or picking the earlier stage in the Stage select) undoes an advance. The earlier
stage comes back with its original start date and checked-off tasks, so a stage you advanced too
soon picks up where it left off. If there's nothing to undo, for example after starting a grow at
stage 2, the previous stage starts today instead.

Stages never change on their own. A stage's estimated days are for planning only. On its last
estimated day the task list gets a **Check if ready for *next stage*** item, with the stage's expected
outcome as its note. When the plants look ready, press **Next stage**. Checking the item off doesn't
change the stage.

## Actions

`hydro_grow_planner.start_grow` (optionally with `night_lighting`), `end_grow`, `set_stage`,
`advance_stage`, `previous_stage`, `log_reading`, `sync_devices`. The `config_entry_id` field is optional if you have only one grow system. `plan` and
`stage` take names, and `stage` also accepts a 1-based number.

```yaml
action: hydro_grow_planner.log_reading
data:
  ph: 6.1
  ec: 1.2
```

## Events and notifications

The integration doesn't send notifications itself. Instead it fires events, so you can route them
however you like:

| Event | When | Data |
|---|---|---|
| `hydro_grow_planner_tasks_due` | Daily at the reminder time, if any tasks are due or overdue, or a reading is overdue | `plan`, `stage`, `tasks` (a list of `title`, `task_type`, `note`, `due`, `overdue`), `reading_overdue` |
| `hydro_grow_planner_stage_changed` | A grow starts or its stage changes | `plan`, `stage`, `stage_number`, `stage_count`, `previous_stage`, `expected_outcome` |
| `hydro_grow_planner_grow_ended` | A grow is ended | `plan` |

```yaml
triggers:
  - trigger: event
    event_type: hydro_grow_planner_tasks_due
actions:
  - action: notify.mobile_app_phone
    data:
      title: "🌱 {{ trigger.event.data.plan }} · {{ trigger.event.data.stage }}"
      message: >-
        {% for t in trigger.event.data.tasks %}{{ t.title }}{{ ' (overdue)' if t.overdue }}
        {% endfor %}{{ 'Check pH/EC.' if trigger.event.data.reading_overdue }}
```

For out-of-range water or room climate, trigger on the problem sensors. The `for:` delay keeps a
reading that hovers at the edge of its range from sending repeated alerts:

```yaml
triggers:
  - trigger: state
    entity_id:
      - binary_sensor.tower_ph_out_of_range
      - binary_sensor.tower_ec_out_of_range
      - binary_sensor.tower_temperature_out_of_range
      - binary_sensor.tower_humidity_out_of_range
    to: "on"
    for: "00:15:00"
actions:
  - action: notify.mobile_app_phone
    data:
      title: "🌱 {{ trigger.to_state.name }}"
      message: >-
        {{ trigger.to_state.attributes.value }}{{ trigger.to_state.attributes.unit | default('') }}
        (range {{ trigger.to_state.attributes.min }}–{{ trigger.to_state.attributes.max }})
```

## Development

```bash
uv venv --python 3.14 && uv pip install -r requirements_test.txt
.venv/bin/pytest
.venv/bin/ruff check . && .venv/bin/ruff format --check .
```

`strings.json` is the source for the English translations. Copy it to `translations/en.json` after
you edit it. CI checks that the two files match.
