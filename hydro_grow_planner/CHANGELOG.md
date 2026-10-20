# Changelog

## 0.7.0

- **Fixed the to-do list filling up with duplicates.** Some lists (iCloud Reminders in particular) don't report a
  new item straight away, so the sync didn't recognise what it had just added and added it again on every pass,
  which could leave thousands of copies of the same few tasks, many due today. The sync now claims an item that
  is already there instead of adding another, and waits a few passes for a new one to show up.
- **Only upcoming tasks are mirrored to the to-do list**: those overdue or due in the next 7 days, like the
  panel's *Overdue*, *Today* and *Next 7 days*. Later tasks are added as they come near, and open items that
  are further out are taken off the list again.
- **If your list already has duplicates**, clear them on the list's side (delete them, don't check them off:
  that would complete the task). The app keeps its own tasks and puts back the upcoming ones on its next sync.

## 0.6.0

- **Zones and device roles.** Give each device a role (center light, side light, pump) and put lights into
  zones such as *Layers 1+2* in Settings. Starting a grow is now two steps: pick a template and a zone, and the
  lights and shared pump are filled in for you. Zones in use by a running grow are marked and free up when it
  ends. Existing devices get a role guessed from their name.
- **Guided setup for a new system**: name it, group its lights into zones, then add its devices with their
  roles. It also opens when you add another system, or from *Set up zones…* when you try to start a grow in
  a system that has none. The old tick-the-devices screen is gone.
- **Plans are gone: a grow keeps its own copy of its template.** Starting a grow no longer creates a separate
  plan to manage. The grow holds the template's schedules, tasks and targets; change them with **Overview →
  Edit plan…** (it affects only that grow) and keep a good one with *Save as template*. The *Plan* tab is
  removed. Plans you had saved move into the grows running them; any plan no grow was using becomes a custom
  template, so nothing is lost.
  - Removed the per-grow *Plan* select entity in Home Assistant (it switched plans or ended the grow).
    End or change a grow in the panel instead.
- **Fixed the Start a grow dialog running off the screen** with many devices; it now scrolls.

## 0.5.1

- **Safe to point at a shared to-do list** (e.g. your iCloud Reminders list). The sync only adds, checks
  off and removes the items it created; items already on the list are never adopted, changed or removed,
  even if they share a name with a task.
- **Importing items you add on the list is now opt-in** (*Turn items I add to this list into tasks* in
  Settings). It was always on before; turn it on again if you relied on it. It only imports items added
  after you switch it on.

## 0.5.0

- **Harvest style.** A plan is now either harvested all at once, or a little at a time while it keeps growing.
  A little-at-a-time plan gets a repeating Harvest task (how much, and from where) in the stage where harvesting
  starts, added on save if it lacks one. Its last-stage check asks whether the plants are spent instead of
  "ready to finish?".
  - All built-in templates are harvested a little at a time. **Lettuce** and **Spinach** gain a *Harvest* stage
    (42 and 28 days), **Leafy Greens** and **Mixed Herbs** harvest in their long Vegetative stage, and **Tomato**,
    **Pepper** and **Bell Pepper** get a 90-day Fruiting stage (was 42) with a pick-ripe-fruit task. Plans you
    already made from them are unchanged.
- **System upkeep tasks** that belong to the system rather than a plan, with defaults for a deep flow (DFT)
  kit: change the water (90 days, since about 10 gal stays balanced for months), clean the pump and drains (56),
  calibrate the pH meter (30) and deep-clean (180). Edit, switch off or add your own in Settings. They run on the system's running time
  (new *System day* and *Next maintenance* sensors).
- **Switching a grow's plan keeps its start date** (new "keep counting" option, on by default, also for the
  plan select entity), so *grow day* and upkeep timing stay right.

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
