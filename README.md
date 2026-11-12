# Hydro Grow Planner

[![Validate](https://github.com/fwump38/hydro-grow-planner/actions/workflows/validate.yml/badge.svg)](https://github.com/fwump38/hydro-grow-planner/actions/workflows/validate.yml)

A Home Assistant **app** for running a hydroponic grow from a plan: stages, each with its own light
and pump schedule, target ranges and day-by-day tasks. It switches your devices on schedule, keeps
hands its tasks to [Home Keeper](https://github.com/prestomation/ha-home-keeper), watches pH, EC, temperature and humidity against the plan, and
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
3. **Install [Home Keeper](https://github.com/prestomation/ha-home-keeper)** (HACS, then add it under
   Settings → Devices & services). It is required: all tasks appear there. See [Tasks](#tasks-in-home-keeper).
4. **Overview → Start a grow.** Pick a template, say which of your devices plays each role, then say
   **which stage you're at and when it started**, and review exactly what will happen.
5. Running more than one grow on the same tower? See [Several grows at once](#several-grows-at-once).

## What you get

**Overview**: the stage timeline, each device with a 24-hour bar of its schedule and a manual
toggle, pH/EC/temperature/humidity against their targets, a pH/EC box with a **Record** button, and
and a Tasks card saying how many are due (the tasks themselves are in Home Keeper).

Nothing you type into the pH/EC box is saved until you press **Record**, so nudging the number up
and down doesn't create a history of in-between readings.

**Editing a grow's plan**: **Overview → Edit plan…** on a grow opens a single page with Save/Discard. Each grow keeps its own copy of the template it started from, so changes affect only that grow.
Per device Per device you pick a mode (not managed, off,
always on, time window, cycle) and only that mode's fields appear, with a live 24-hour preview.
Tasks are edited inline. Edits are validated, and errors show next to the field.

**Templates**: browse the built-in templates (Bell Pepper, Leafy Greens, Lettuce, Pepper, Spinach,
Tomato, from the Elfsys Grow Cloud app, plus *Mixed Herbs*) stage by stage, duplicate one to edit it,
save a grow's plan as a template, and import/export JSON.

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

Some jobs belong to the system, not to a plan. **Settings → System upkeep** defines a repeating task list that
applies whatever is growing. Each one is a native Home Keeper *repeating* task, so Home Keeper keeps its
history and interval statistics and you can snooze or skip it there.
The defaults suit a deep flow (DFT) kit like the Elfsys one, which holds about 7 gal
with two layers and about 10 gal with four. Growers' rule of thumb is that more water stays balanced longer:
weekly under 2 gal, monthly for 2–5 gal, before flowering and after harvest for 5–10 gal, and mostly top up and
re-balance above that. So the defaults are: change the water every 90 days (sooner if pH swings or EC creeps up,
and shorter for a 2-layer kit), clean the pump and drains (56), calibrate the pH meter (30) and deep-clean the
system (180, and whenever you end a grow). These are starting points, not Elfsys guidance; edit the intervals or
instructions, turn tasks off, or add your own. Doing the deep clean also completes the water-change and pump-clean
tasks in Home Keeper, restarting their clocks.

Upkeep is timed by how long the **system** has been running, not by any one plan: the **System day** counts
from the oldest running grow's start date. That date is kept when you switch a grow to another plan
mid-grow (the wizard asks, on by default) and is backdated when you start a grow that began earlier, so a
grow you add on day 45 gets everything that's already due. After that each task repeats `N` days after you
check it off. When nothing is growing the tasks are paused (disabled in Home Keeper, with their history kept) and
resume with the next grow.

### Several grows at once

A tower's layers can run different grows at the same time. **Overview → Add a grow…** starts another one;
give each a name such as *Layers 1+2*. Grows share the **reservoir, pump, sensors and room**, and each has
its own plan, stage, start date, tasks and night-lighting switch.

- **Zones and roles:** in **Settings** give each device a role (center light, side light, pump) and put each
  light in a **zone**, e.g. *Layers 1+2*. Starting a grow is then just a template and a zone: the zone's
  lights and the shared pump are picked up automatically. A zone is greyed out only while a running grow
  uses it, and frees up when that grow ends (you can still share one, with a warning). A new system opens a
  short setup (name, zones, devices); a system without zones asks you to set them up before starting a grow.
- **Shared devices** (normally the pump): when two grows both schedule a device, it is **on whenever either
  wants it on**. Overview shows who schedules each device.
- **pH, EC, temperature and humidity targets** are where the grows' ranges overlap. If they don't overlap
  (say a lettuce and a bok choy EC range), the oldest grow's range is used and the panel says so.
- **Tasks** carry their grow's name in Home Keeper once there is more than one grow.
- Each grow gets its own stage prompt and its own set of entities; events say which grow (`grow`,
  `grow_id`).

### Starting mid-grow

Choose the stage you're in and the date it started (or "today is day N"). The grow's start date is
worked out from the earlier stages. One-off tasks whose day has passed are skipped (or added as
overdue, your choice); repeating tasks get their first occurrence today.

### Tasks in Home Keeper

Grow Planner works out *when* things are due and [Home Keeper](https://github.com/prestomation/ha-home-keeper)
shows them. Each open task becomes a Home Keeper task "Managed by Grow Planner", with its due date, so it
appears in Home Keeper's panel, calendar, dashboard card, notifications and any to-do list you sync it to.
Check it off there; a repeating task ("Move the grow lights, every 3 days") then comes back **N days after you
check it off**, so late completion pushes the next one back instead of piling up copies. A task you delete in
Home Keeper is added back; to stop a repeat, remove it from the plan.

Some tasks only exist while there is something to do:

| Task | Appears when | Clears when |
|---|---|---|
| Record a pH and EC reading | no reading within the reading interval (not with both sensors) | you record one |
| EC is low: add nutrients / EC is high: add water | EC out of range for 10 minutes | it is back in range |
| pH is low / high | pH out of range for 10 minutes | it is back in range |
| Check if ready for the next stage | the stage reaches its planned length | the stage changes |

Checking one of these off while the problem remains keeps it quiet until it has cleared and returned.
Temperature and humidity only fire the out-of-range events (and your notifications); a sensor already
watches them, so there is no task.

Stages never advance on their own. When a stage reaches its planned length you get a "ready to
move on?" prompt and a task; a person decides.

### Units

Temperatures, water volumes and nutrient weights follow the **unit system set in Home Assistant**: metric
(°C, litres, grams) or US customary (°F, gallons, ounces). The app reads it when it connects and picks up a
change without a restart. **Settings → Units** can override any of the three for one system, for example litres
in an otherwise US customary home. EC has its own unit (below). Plans and templates keep the temperature unit
they were written in, and are shown, edited and saved in the unit in use. The tank capacity is kept in litres,
so changing units never changes the tank.

### Adding water and nutrients

**Settings → Tank & nutrients** holds the system's **total water capacity** (in gallons or litres, following the Units setting above), how old an EC
reading may be before the calculator asks for a fresh one (24 h by default), and which **nutrient line** to use.

**Overview → Add water & nutrients** works out what to add when you top up the tank. Enter how much water you
are adding; the tank is assumed to be topped up toward full, so it already held *capacity − added*. It takes the
current EC (a sensor reading, or the last one you recorded), and **asks you to measure again if the reading is
too old**; an EC typed there is used instead and can be recorded with one click. The target is the middle of the
running grows' combined EC range (or a target you enter). Because new water carries no EC, the tank's EC is
diluted first, and the nutrients make up the rest of the way, so a top-up of weak water doesn't over-dose.

The result is the **total for the water you're adding** and the **amount per gallon (or litre) added**, in ml
with the weight in grams beneath it. Each product's share comes from the line's dose chart. With several grows in
different stages, each grow's stage picks a column of the chart and the columns are blended with equal weight.
EC is assumed to rise in proportion to the dose, and the water you add is assumed to have no EC of its own.

*Elfsys Plant Mana* (PM-1, PM-2, PM-3, PM-ES with the Elfsys feeding chart) is built in. To use another brand,
choose **Add my own nutrients** (or **Copy … to edit**) and enter its products, their density (g/ml) and the
chart from its bottle: ml per US gallon for each feeding stage and the EC that mix gives.

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
| Per grow | plan, stage, stage day, days remaining, progress, grow day, grow started and expected end sensors; a stage select; a night lighting switch; next / previous / restart stage buttons. Named after the grow, e.g. `sensor.grow_system_layers_1_2_stage_day` |
| Numbers | Record pH / Record EC, only when there's no sensor (commit on Enter) |

They go *unavailable* if the app stops. EC entities use your chosen unit.

## Notifications

The app doesn't send notifications itself, because everyone notifies differently. It fires events on
the Home Assistant bus; turn them into notifications however you like. Every payload also has
`system_id` and `system`; events about a grow also have `grow_id` and `grow`.

| Event | When |
|---|---|
| `hydro_grow_planner_stage_complete_due` | Once, when a stage reaches its planned length: `stage`, `next_stage`, `expected_outcome` |
| `hydro_grow_planner_reading_overdue` | Once, when no reading was recorded within the interval: `last_reading`, `interval_days` |
| `hydro_grow_planner_out_of_range` / `_back_in_range` | A metric stayed out of (or back in) range for 10 minutes: `metric` (`ph`, `ec`, `temperature`, `humidity`), `value`, `min`, `max`, `unit` |
| `hydro_grow_planner_stage_changed`, `_grow_started`, `_grow_ended` | Lifecycle |

**Settings → Events** in the panel lists these with example payloads and a **Send test** button. To watch
them, use Developer tools → Events → *Listen to events* with one exact event name, or `*` for all
events (then use the filter box). A prefix pattern like `hydro_grow_planner_*` does **not** match.
The app's log also prints `Fired event …` for each one it sends.

### Examples

Task reminders and digests come from Home Keeper (its notifications, or its "Task became overdue" automation trigger).

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

Or import the **blueprint** in `blueprints/grow_planner_notify.yaml`, which handles stage
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
