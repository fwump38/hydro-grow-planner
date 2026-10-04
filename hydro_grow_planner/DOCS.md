# Hydro Grow Planner

Open **Grow Planner** from the sidebar. Everything is set up in the panel.

## Requirements

The **MQTT** integration with a broker (for example the *Mosquitto broker* app). The app finds the
broker through the Supervisor; there is nothing to configure here.

## Configuration

| Option | Meaning |
|---|---|
| `log_level` | `debug`, `info`, `warning` or `error`. |

Grow systems, devices, sensors, plans and templates are managed in the panel and stored in the app's
data folder (included in Home Assistant backups).

## Notifications

The app fires events instead of sending notifications. See **Settings → Events** in the panel for
every event, its payload and a *Send test* button, and the project README for example automations.

## Support

<https://github.com/fwump38/hydro-grow-planner/issues>
