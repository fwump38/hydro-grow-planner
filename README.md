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

**1. Add a grow system.** Give it a name, pick the devices the plan should drive, and optionally a pH
and/or EC sensor (leave these empty to log readings by hand). Then give each device a short name, such
as "Side lights".

**2. Add a grow plan.** On the integration's page, choose **Add grow plan**. Start blank or from a
preset. Presets include **Lettuce** and **Leafy greens**, each with 3 stages of light and pump
schedules. When you use a preset, you match its roles (center lights, side lights, water pump) to your
devices.

**3. Edit the plan** at any time with the plan's ⋮ → **Reconfigure** menu:

| Menu | What it does |
|---|---|
| Name, target pH and notes | Plan-level settings. Target pH applies to the whole plan. |
| Add / Edit a stage | Name, type, estimated days, target EC, expected outcome, then one schedule form per device. |
| Edit tasks | Add, edit or remove tasks for a stage. Each task has a day of the stage, a type, a title and a note. |
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

## Entities

For each grow system:

| Entity | Purpose |
|---|---|
| `select` Plan / Stage | Start, switch or end a grow. Jump to a stage. |
| `button` Next / Previous / Restart stage, Sync devices, Water checked | Stage control and device sync. *Water checked* stamps a manual reading without changing the values. |
| `switch` Schedule control | Enable or disable device switching. |
| `todo` Tasks | The current stage's tasks, each due on *stage start + day − 1*. You can also add your own items here. |
| `sensor` Active plan, Current stage, Stage day, Stage days remaining, Stage progress, Grow day, Grow started, Expected end, Target pH, Target EC, Tasks due, Next task | Status. *Current stage* has the full stage details, including each device's schedule, as attributes. |
| `number` Measured pH / EC | Manual readings. Only created when no sensor is configured. |
| `binary_sensor` pH / EC out of range, Water reading overdue | Problems, compared against the targets and the tolerances in the options. |
| `binary_sensor` *Device* scheduled | Whether the schedule wants that device on right now. Compare it with the device to spot a manual override. |

Stages advance only when you advance them, unless you turn on **Advance stages automatically** in the
options. With it on, the next stage starts at midnight once the current stage's estimated days have
passed.

## Actions

`hydro_grow_planner.start_grow`, `end_grow`, `set_stage`, `advance_stage`, `log_reading`,
`sync_devices`. The `config_entry_id` field is optional if you have only one grow system. `plan` and
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

For out-of-range water, trigger on the `pH out of range` or `EC out of range` binary sensors.

## Development

```bash
uv venv --python 3.14 && uv pip install -r requirements_test.txt
.venv/bin/pytest
.venv/bin/ruff check . && .venv/bin/ruff format --check .
```

`strings.json` is the source for the English translations. Copy it to `translations/en.json` after
you edit it. CI checks that the two files match.
