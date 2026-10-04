"""Run the app: `python -m grow_planner`."""

from __future__ import annotations

import asyncio
import contextlib
from datetime import datetime
import logging
import os
from pathlib import Path
from typing import Any

import aiohttp
from aiohttp import web

from .api import INGRESS_PEER, build_web_app
from .app import App
from .ha_ws import HAClient
from .mqtt import MqttClient
from .settings import Settings, load
from .store import ReadingsLog, Store

_LOGGER = logging.getLogger("grow_planner")

SUPERVISOR_MQTT_URL = "http://supervisor/services/mqtt"


def local_now() -> datetime:
    """Return the current time in the system (Home Assistant's) timezone."""
    return datetime.now().astimezone()


async def fetch_supervisor_mqtt(session: aiohttp.ClientSession, token: str) -> dict[str, Any]:
    """Ask the Supervisor for the MQTT broker (needs `services: [mqtt:need]`)."""
    async with session.get(
        SUPERVISOR_MQTT_URL, headers={"Authorization": f"Bearer {token}"}
    ) as response:
        response.raise_for_status()
        return (await response.json())["data"]


async def run(settings: Settings) -> None:
    """Wire everything together and run until cancelled."""
    store = Store(settings.data_dir / "state.json")
    store.load()
    readings = ReadingsLog(settings.data_dir / "readings.sqlite")

    async with aiohttp.ClientSession() as session:
        ha = HAClient(settings.ha_ws_url, settings.ha_token, session)

        mqtt: MqttClient | None = None
        host, port = settings.mqtt_host, settings.mqtt_port
        user, password, tls = settings.mqtt_user, settings.mqtt_password, settings.mqtt_tls
        if settings.in_supervisor:
            info = await fetch_supervisor_mqtt(session, settings.ha_token)
            host, port = info["host"], int(info["port"])
            user, password, tls = info.get("username"), info.get("password"), bool(info.get("ssl"))

        app = App(store, ha, readings, None, local_now)
        if host:
            _LOGGER.info("MQTT broker: %s:%s", host, port)
            mqtt = MqttClient(host, port, user, password, app.on_mqtt_command, tls)
            app.mqtt = mqtt
        else:
            _LOGGER.warning("No MQTT broker configured: Home Assistant entities are disabled")
        app.load()

        web_app = build_web_app(
            app,
            Path(__file__).parent / "static",
            frozenset({INGRESS_PEER}) if settings.in_supervisor else frozenset(),
        )
        runner = web.AppRunner(web_app)
        await runner.setup()
        await web.TCPSite(runner, "0.0.0.0", settings.port).start()
        _LOGGER.info("Listening on port %s", settings.port)

        app.start()
        tasks = [asyncio.create_task(ha.run(app.on_ha_state, app.on_ha_connected))]
        if mqtt is not None:
            tasks.append(asyncio.create_task(mqtt.run()))
        try:
            await asyncio.gather(*tasks)
        finally:
            for task in tasks:
                task.cancel()
            await app.stop()
            await runner.cleanup()
            readings.close()


def main() -> None:
    """Entry point."""
    settings = load(os.environ)
    logging.basicConfig(
        level=settings.log_level.upper(),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    with contextlib.suppress(KeyboardInterrupt):
        asyncio.run(run(settings))


if __name__ == "__main__":
    main()
