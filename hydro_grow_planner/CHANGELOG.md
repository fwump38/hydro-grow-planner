# Changelog

## 0.4.1

- Add an app icon and logo.

## 0.4.0

- **Several grows at once.** A system can run more than one plan, e.g. one for layers 1+2 and another for
  layers 3+4. They share the reservoir, pump, sensors and room; each has its own plan, stage, start date,
  tasks and lights. Add one with **Overview → Add a grow…**. Existing grows carry over unchanged.
  - A device two grows schedule (normally the pump) is on whenever either wants it on.
  - pH, EC, temperature and humidity targets are where the grows' ranges overlap; if they don't, the oldest
    grow's range is used and the panel says so.
- **Night lighting is per grow**, not per system.
- **Tasks are tagged with their grow**, in the panel and in the to-do list (once there is more than one grow).
  Tasks you add can be for one grow or all.
- **A template role can drive several devices.** The wizard lets you tick more than two lights, and skips
  lights another grow already runs.
- New **Mixed Herbs** template for basil, cilantro, scallions/chives and bok choy on one reservoir.
- The pH box accepts two decimals (6.25).
- **Breaking:** plan, stage, grow day, and the plan/stage selects, night lighting switch and stage buttons are
  now per-grow entities named after the grow (e.g. `sensor.grow_system_layers_1_2_stage_day`); the old
  single-grow entity IDs are removed. Update automations that use them. API: `/grow/*`, `/stage*` and
  `/night-lighting` became `/grows`, `/grows/{id}` and `/grows/{id}/stage*`. Events gain `grow` and
  `grow_id`.

## 0.3.2

- Leafy Greens template: the pump now runs 15 min every 3 h in Vegetative like every other stage
  (it was always on).
- Leafy Greens template: lights follow the Lettuce/Spinach pattern (side lights only while sprouting,
  center lights only as seedlings, both for 14 h in Vegetative) instead of 15 h of light while
  sprouting and 17 h in Vegetative.
- Leafy Greens template: humidity target widened to 40–70 % (herbs prefer drier air than lettuce).
- A plan you already started keeps the schedule it was created with; edit it under Plan to apply the
  new values.

## 0.3.1

- Publish the app image under the plain version tag the Supervisor pulls (0.3.0 was tagged `v0.3.0`, which it can't find).

## 0.3.0

Rebuilt as a Home Assistant app, replacing the custom integration.

- Sidebar panel: overview, plan editor, template browser, start/change-grow wizard, settings.
- Start a grow at any stage and date; tasks and schedules line up with where you are.
- Repeating tasks reappear N days after they're checked off; mirrored to a Home Assistant to-do list.
- pH/EC are recorded with an explicit **Record** button.
- EC in your meter's unit (mS/cm, µS/cm, CF, ppm 500, ppm 700); plans are converted to mS/cm.
- Every built-in template has pH, temperature, humidity and EC ranges; Leafy Greens has generic ones.
- Events for notifications instead of a fixed notify target.
- Entities published over MQTT.
