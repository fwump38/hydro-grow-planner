# Changelog

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
