# Hydro Grow Planner

[![Validate](https://github.com/fwump38/hydro-grow-planner/actions/workflows/validate.yml/badge.svg)](https://github.com/fwump38/hydro-grow-planner/actions/workflows/validate.yml)

A Home Assistant **app** for running a hydroponic grow from a plan: stages, each with its own light
and pump schedule, target ranges and day-by-day tasks. It switches your devices on schedule, keeps
a task list that actually repeats, watches pH, EC, temperature and humidity against the plan, and
tells your automations when something needs attention.

It has its own sidebar panel (no cramped config-flow forms) and publishes entities to Home
Assistant over MQTT for your own automations and history.

Built for an Elfsys tower (side lights, center lights, water pump), but it works with any
switches, lights, fans or input booleans.

> **Coming from the old Hydro Grow Planner integration?** This replaces it. There is no importer:
> remove the integration, install the app and set things up again. The built-in templates are the
> same, and starting mid-grow is now a first-class option.

## Install

[![Open your Home Assistant instance and show the add app repository dialog with this repository pre-filled.](https://my.home-assistant.io/badges/supervisor_add_addon_repository.svg)](https://my.home-assistant.io/redirect/supervisor_add_addon_repository/?repository_url=https%3A%2F%2Fgithub.com%2Ffwump38%2Fhydro-grow-planner)

1. **Settings → Apps → Install app → ⋮ → Repositories**, add
   `https://github.com/fwump38/hydro-grow-planner`.
2. Install **Hydro Grow Planner** and start it.
3. Open **Grow Planner** from the sidebar.

You need the **MQTT** integration with a broker such as the *Mosquitto broker* app. The app finds the
broker itself.

## First run

1. **Settings → Devices:** add the lights and pump (any switch, light, fan or input boolean), and tick
   which are grow lights. Optionally add pH, EC, room temperature and humidity sensors; without a
   sensor you record the value by hand.
2. **Settings → Water readings:** choose your **EC unit** (below).
3. **Settings → Tasks:** pick a Home Assistant to-do list to mirror tasks into (add a *Local To-do*
   list first).
4. **Overview → Start a grow.** Pick a template, say which of your devices plays each role, then say
   **which stage you're at and when it started**, and review exactly what will happen.

## What you get

**Overview**: the stage timeline, each device with a 24-hour bar of its schedule and a manual
toggle, pH/EC/temperature/humidity against their targets, a pH/EC box with a **Record** button, and
your tasks grouped as overdue / today / next 7 days.

Nothing you type into the pH/EC box is saved until you press **Record**, so nudging the number up
and down doesn't create a history of in-between readings.

**Plan editor**: a single page with Save/Discard. Per device you pick a mode (not managed, off,
always on, time window, cycle) and only that mode's fields appear, with a live 24-hour preview.
Tasks are edited inline. Edits are validated, and errors show next to the field.

**Templates**: browse the built-in templates (Bell Pepper, Leafy Greens, Lettuce, Pepper, Spinach,
Tomato, from the Elfsys Grow Cloud app) stage by stage, duplicate one to edit it, save any of your
plans as a template, and import/export JSON.

Every built-in template has a pH, temperature and humidity range and an EC range for every stage, so
the out-of-range alerts are useful from day one. *Leafy Greens* uses generic values that suit most
leafy greens and herbs (pH 5.8–6.5, 65–75 °F, 40–70 % humidity so herbs fit too, EC 0.0–2.0 mS/cm by stage).

### Starting mid-grow

Choose the stage you're in and the date it started (or "today is day N"). The grow's start date is
worked out from the earlier stages. One-off tasks whose day has passed are skipped (or added as
overdue, your choice); repeating tasks get their first occurrence today.

### Tasks that repeat

A repeating task ("Move the grow lights, every 3 days") reappears **N days after you check it off**,
so late completion pushes the next one back instead of piling up copies. Check items off in the
panel or in Home Assistant; both work. Tasks you add yourself can repeat too.

Stages never advance on their own. When a stage reaches its planned length you get a "ready to
move on?" prompt and a task; a person decides.

### EC units

Plans and alerts use **mS/cm**. Pick the unit your meter uses and everything you enter and see is
converted: mS/cm, µS/cm, CF, ppm 500 (TDS/NaCl) or ppm 700 (442/KCl). A 700 ppm (500 scale) reading is
checked as 1.4 mS/cm. For an EC sensor the unit is detected (a bare "ppm" needs you to pick 500 or 700).

## Home Assistant entities

Created over MQTT discovery, one device per grow system. Entity IDs follow the system name, e.g.
`sensor.grow_system_stage_day` for a system called *Grow System*.

| Kind | Entities |
|---|---|
| Sensors | plan, stage, stage day, days remaining, progress, grow day, grow started, expected end, tasks due, next task, measured pH / EC (with long-term statistics), pH and EC min/max |
| Binary sensors | each device's scheduled state, pH / EC / temperature / humidity out of range, water reading overdue |
| Controls | plan and stage selects, schedule control and night lighting switches, next / previous / restart stage, sync devices, water checked |
| Numbers | Record pH / Record EC, only when there's no sensor (commit on Enter) |

They go *unavailable* if the app stops. EC entities use your chosen unit.

## Notifications

The app doesn't send notifications itself, because everyone notifies differently. It fires events on
the Home Assistant bus; turn them into notifications however you like. Every payload also has
`system_id` and `system`.

| Event | When |
|---|---|
| `hydro_grow_planner_tasks_due` | Once a day at the reminder time, if tasks are due or overdue. Payload: `plan`, `stage`, `count`, `tasks[]` (`title`, `task_type`, `note`, `due`, `overdue`, `recurring`) |
| `hydro_grow_planner_stage_complete_due` | Once, when a stage reaches its planned length: `stage`, `next_stage`, `expected_outcome` |
| `hydro_grow_planner_reading_overdue` | Once, when no reading was recorded within the interval: `last_reading`, `interval_days` |
| `hydro_grow_planner_out_of_range` / `_back_in_range` | A metric stayed out of (or back in) range for 10 minutes: `metric` (`ph`, `ec`, `temperature`, `humidity`), `value`, `min`, `max`, `unit` |
| `hydro_grow_planner_task_created` / `_task_completed` | A repeating or custom task gets a new occurrence / is checked off: `task`, `due` / `next_due` |
| `hydro_grow_planner_stage_changed`, `_grow_started`, `_grow_ended` | Lifecycle |

**Settings → Events** in the panel lists these with example payloads and a **Send test** button. To watch
them, use Developer tools → Events → *Listen to events* with one exact event name, or `*` for all
events (then use the filter box). A prefix pattern like `hydro_grow_planner_*` does **not** match.
The app's log also prints `Fired event …` for each one it sends.

### Examples

Daily to-do digest to your phone:

```yaml
automation:
  - alias: Grow tasks due
    triggers:
      - trigger: event
        event_type: hydro_grow_planner_tasks_due
    actions:
      - action: notify.mobile_app_YOUR_PHONE
        data:
          title: "Grow tasks ({{ trigger.event.data.count }})"
          message: >
            {% for t in trigger.event.data.tasks %}• {{ t.title }}{{ ' (overdue)' if t.overdue }}
            {% endfor %}
```

pH or EC drifted out of range:

```yaml
automation:
  - alias: Grow water out of range
    triggers:
      - trigger: event
        event_type: hydro_grow_planner_out_of_range
    conditions:
      - condition: template
        value_template: "{{ trigger.event.data.metric in ['ph', 'ec'] }}"
    actions:
      - action: notify.mobile_app_YOUR_PHONE
        data:
          title: "{{ trigger.event.data.metric | upper }} out of range"
          message: >
            {{ trigger.event.data.value }} {{ trigger.event.data.unit or '' }}
            (target {{ trigger.event.data.min }}–{{ trigger.event.data.max }})
```

Stage ready to check:

```yaml
automation:
  - alias: Grow stage ready
    triggers:
      - trigger: event
        event_type: hydro_grow_planner_stage_complete_due
    actions:
      - action: notify.mobile_app_YOUR_PHONE
        data:
          message: >
            {{ trigger.event.data.stage }} has run its planned time. Ready for
            {{ trigger.event.data.next_stage or 'the end of the grow' }}?
```

Or import the **blueprint** in `blueprints/grow_planner_notify.yaml`, which handles tasks due, stage
ready and reading overdue; you choose the action that sends the message (it can use `{{ title }}`
and `{{ message }}`).

## Development

```
backend/    Python 3.13, aiohttp: engine, MQTT, Home Assistant websocket, API (pytest)
frontend/   Preact + TypeScript panel (Vite, vitest); builds into backend/grow_planner/static
hydro_grow_planner/   the app: config.yaml, Dockerfile, s6 service
```

```sh
uv venv --python 3.13 && uv pip install -r backend/requirements-dev.txt
.venv/bin/pytest                         # backend tests
cd frontend && npm ci && npm test && npm run build
cd backend && ../.venv/bin/python dev_server.py   # panel with a fake Home Assistant, seeded data
```

To run against your real Home Assistant without installing the app:

```sh
HA_URL=http://homeassistant.local:8123 HA_TOKEN=<long-lived token> \
MQTT_HOST=homeassistant.local MQTT_USER=… MQTT_PASSWORD=… \
  .venv/bin/python -m grow_planner     # from backend/, after building the panel
```

Releases: bump `version` in `hydro_grow_planner/config.yaml`, tag `vX.Y.Z`; CI builds and publishes the
multi-arch image the Supervisor pulls.
