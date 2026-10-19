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
3. **Settings → Tasks:** pick a Home Assistant to-do list to mirror tasks into: a *Local To-do* list, or
   any other to-do entity such as an iCloud Reminders list. The app only touches items it created itself;
   anything already on the list is left alone. Items you add to the list later become tasks only if you
   tick *Turn items I add to this list into tasks*.
4. **Overview → Start a grow.** Pick a template, say which of your devices plays each role, then say
   **which stage you're at and when it started**, and review exactly what will happen.
5. Running more than one plan on the same tower? See [Several grows at once](#several-grows-at-once).

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
Tomato, from the Elfsys Grow Cloud app, plus *Mixed Herbs*) stage by stage, duplicate one to edit it,
save any of your plans as a template, and import/export JSON.

Every built-in template has a pH, temperature and humidity range and an EC range for every stage, so
the out-of-range alerts are useful from day one. *Leafy Greens* uses generic values that suit most
leafy greens and herbs (pH 5.8–6.5, 65–75 °F, 40–70 % humidity so herbs fit too, EC 0.0–2.0 mS/cm by stage).

*Mixed Herbs* is not from Elfsys. It is Leafy Greens tuned for basil, cilantro, scallions/chives and bok
choy sharing one reservoir: pH 6.0–6.5 (where all of them overlap), 65–75 °F, 40–65 % humidity, a middling
EC, longer sprouting and seedling stages for the slow germinators, and tasks to pinch and harvest, watch for
bolting and re-sow cilantro.

### Harvest style

Every plan is either **all at once** (harvest everything, then start over) or **a little at a time**
(cut-and-come-again lettuce, picking ripe fruit while the plant keeps growing). Set it at the top of the
plan editor. A little-at-a-time plan needs a repeating *Harvest* task (how much, and from where) in the stage
where harvesting starts, and one is added when you save if there isn't one. Plants don't produce forever,
so that stage's length is how long they stay productive; its last "ready?" check then asks whether the
plants are spent (still regrowing? **Restart stage** to keep going; otherwise end the grow and replant).
Nothing ends by itself.

All the built-in templates are harvested a little at a time. These lengths are my estimates for a small
indoor kit, not Elfsys figures:

| Template | Harvest task | Productive for |
|---|---|---|
| Lettuce | a third of the hand-sized outer leaves, every 5 days, in a new 42-day *Harvest* stage | about 10–11 weeks from sowing |
| Spinach | the same, in a 28-day *Harvest* stage (it bolts sooner) | about 10 weeks |
| Leafy Greens | the same, from day 21 of its long Vegetative stage | about 3 months |
| Mixed Herbs | pinch and harvest, up to a third of a plant, weekly | about 3 months |
| Tomato, Pepper, Bell Pepper | pick ripe fruit every 3–5 days, in a Fruiting stage lengthened from 42 to 90 days | about 3 months of fruiting |

### System upkeep

Some jobs belong to the system, not to a plan. **Settings → System upkeep** has a repeating task list that
applies whatever is growing. The defaults suit a deep flow (DFT) kit like the Elfsys one, which holds about 7 gal
with two layers and about 10 gal with four. Growers' rule of thumb is that more water stays balanced longer:
weekly under 2 gal, monthly for 2–5 gal, before flowering and after harvest for 5–10 gal, and mostly top up and
re-balance above that. So the defaults are: change the water every 90 days (sooner if pH swings or EC creeps up,
and shorter for a 2-layer kit), clean the pump and drains (56), calibrate the pH meter (30) and deep-clean the
system (180, and whenever you end a grow). These are starting points, not Elfsys guidance; edit the intervals or
instructions, turn tasks off, or add your own. Doing the deep clean also restarts the water-change and pump-clean
clocks.

Upkeep is timed by how long the **system** has been running, not by any one plan: the **System day** counts
from the oldest running grow's start date. That date is kept when you switch a grow to another plan
mid-grow (the wizard asks, on by default) and is backdated when you start a grow that began earlier, so a
grow you add on day 45 gets everything that's already due. After that each task repeats `N` days after you
check it off. Skipping one (✕) pushes it back a full interval. When nothing is growing the open tasks
stay for you to clean up after the grow, but they stop repeating.

### Several grows at once

A tower's layers can run different plans at the same time. **Overview → Add a grow…** starts another one;
give each a name such as *Layers 1+2*. Grows share the **reservoir, pump, sensors and room**, and each has
its own plan, stage, start date, tasks and night-lighting switch.

- **Lights:** a template role can drive several devices (tick them in the wizard), so a pair of layers on one
  plug is one device. Give each grow its own lights; the wizard skips lights another grow already runs.
- **Shared devices** (normally the pump): when two grows both schedule a device, it is **on whenever either
  wants it on**. Overview shows who schedules each device.
- **pH, EC, temperature and humidity targets** are where the grows' ranges overlap. If they don't overlap
  (say a lettuce and a bok choy EC range), the oldest grow's range is used and the panel says so.
- **Tasks** carry their grow's name, in the panel and in the to-do list once there is more than one grow.
  A task you add yourself can be for one grow or all of them.
- Each grow gets its own stage prompt and its own set of entities; events say which grow (`grow`,
  `grow_id`).

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
| Sensors | tasks due, next task, system day, next maintenance, measured pH / EC (with long-term statistics), pH and EC min/max |
| Binary sensors | each device's scheduled state, pH / EC / temperature / humidity out of range, water reading overdue |
| Controls | schedule control switch, sync devices, water checked |
| Per grow | plan, stage, stage day, days remaining, progress, grow day, grow started and expected end sensors; plan and stage selects; a night lighting switch; next / previous / restart stage buttons. Named after the grow, e.g. `sensor.grow_system_layers_1_2_stage_day` |
| Numbers | Record pH / Record EC, only when there's no sensor (commit on Enter) |

They go *unavailable* if the app stops. EC entities use your chosen unit.

## Notifications

The app doesn't send notifications itself, because everyone notifies differently. It fires events on
the Home Assistant bus; turn them into notifications however you like. Every payload also has
`system_id` and `system`; events about a grow also have `grow_id` and `grow`.

| Event | When |
|---|---|
| `hydro_grow_planner_tasks_due` | Once a day at the reminder time, if tasks are due or overdue. Payload: `plan`, `stage` (only when one grow is running), `count`, `tasks[]` (`title`, `task_type`, `note`, `due`, `overdue`, `recurring`, `grow`) |
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
