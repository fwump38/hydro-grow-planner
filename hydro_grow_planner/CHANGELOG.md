# Changelog

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
