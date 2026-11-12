"""Run the panel against a fake Home Assistant, with two seeded grows (four light plugs, one shared pump).

    cd backend && python dev_server.py          # then open http://localhost:8099
    python dev_server.py --empty                # start with no grow systems

Nothing here talks to a real Home Assistant or MQTT broker: devices are in-memory
switches, and state lives in a temporary directory that is deleted on exit.
"""

from __future__ import annotations

import asyncio
import contextlib
from datetime import date, datetime, timedelta
import logging
from pathlib import Path
import sys
import tempfile
from typing import Any

from aiohttp import web

from grow_planner.api import build_web_app
from grow_planner.app import App
from grow_planner.core.models import new_id
from grow_planner.core.presets import build_from_preset
from grow_planner.hk_tasks import HKTask
from grow_planner.ports import EntityState
from grow_planner.store import ReadingsLog, Store


class FakeHomeKeeper:
    """Just enough of Home Keeper to show the tasks the app pushes."""

    def __init__(self) -> None:
        self.tasks: dict[str, dict[str, Any]] = {}
        self.n = 0

    async def list_tasks(self) -> list[HKTask]:
        return [
            HKTask(t["id"], t["name"], t["next_due"], t["source"], t["recurrence_type"])
            for t in self.tasks.values()
        ]

    async def add_task(self, data: dict[str, Any]) -> str:
        self.n += 1
        task_id = f"t{self.n}"
        self.tasks[task_id] = {
            "id": task_id,
            "name": data["name"],
            "next_due": data.get("due") or datetime.now().isoformat(),
            "source": data.get("source") or {},
            "recurrence_type": data["recurrence_type"],
        }
        return task_id

    async def update_task(self, task_id: str, data: dict[str, Any]) -> None:
        self.tasks[task_id]["next_due"] = data.get("due", self.tasks[task_id]["next_due"])

    async def delete_task(self, task_id: str) -> None:
        self.tasks.pop(task_id, None)

    async def trigger_task(self, task_id: str) -> None:
        self.tasks[task_id]["next_due"] = datetime.now().isoformat()

    async def complete_task(self, task_id: str) -> None:
        self.tasks[task_id]["next_due"] = None


class FakeHA:
    """Switches that behave like switches; events are just logged."""

    def __init__(self) -> None:
        self.app: App | None = None
        self.hk = FakeHomeKeeper()

    async def call_service(self, domain: str, service: str, data: dict[str, Any]) -> None:
        if service in ("turn_on", "turn_off") and self.app is not None:
            self.app.on_ha_state(
                data["entity_id"], EntityState("on" if service == "turn_on" else "off", None, None)
            )

    async def fire_event(self, event_type: str, data: dict[str, Any]) -> None:
        logging.getLogger("dev").info("event %s %s", event_type, data)

    def home_keeper(self) -> FakeHomeKeeper:
        return self.hk

    async def subscribe(self, payload: dict[str, Any], callback: Any) -> None:
        return None


def local_now() -> datetime:
    return datetime.now().astimezone()


async def main(port: int, empty: bool = False) -> None:
    logging.basicConfig(level="INFO")
    tmp = Path(tempfile.mkdtemp(prefix="grow-dev-"))
    ha = FakeHA()
    store = Store(tmp / "state.json", save_delay=0)
    app = App(store, ha, ReadingsLog(tmp / "readings.sqlite"), None, local_now)  # type: ignore[arg-type]
    ha.app = app

    for entity, name, state, unit in [
        ("switch.l12_center", "Layers 1+2 center", "off", None),
        ("switch.l12_sides", "Layers 1+2 sides", "off", None),
        ("switch.l34_center", "Layers 3+4 center", "off", None),
        ("switch.l34_sides", "Layers 3+4 sides", "off", None),
        ("switch.elfsys_water_pump", "Elfsys water pump", "off", None),
        ("switch.garage_fan", "Garage fan", "off", None),
        ("sensor.grow_room_temperature", "Grow room temperature", "71.5", "°F"),
        ("sensor.grow_room_humidity", "Grow room humidity", "46", "%"),
        ("sensor.reservoir_ec", "Reservoir EC", "1450", "µS/cm"),
    ]:
        app.on_ha_state(entity, EntityState(state, unit, name))

    if empty:
        app.start()
        web_app = build_web_app(app, Path(__file__).parent / "grow_planner" / "static")
        runner = web.AppRunner(web_app)
        await runner.setup()
        await web.TCPSite(runner, "127.0.0.1", port).start()
        print(f"Panel (no systems) at http://localhost:{port}", flush=True)
        await asyncio.Event().wait()

    system = app.create_system("Grow System")
    system.update_config(
        devices=[
            {"name": "Layers 1+2 center", "entity_id": "switch.l12_center", "light": True},
            {"name": "Layers 1+2 sides", "entity_id": "switch.l12_sides", "light": True},
            {"name": "Layers 3+4 center", "entity_id": "switch.l34_center", "light": True},
            {"name": "Layers 3+4 sides", "entity_id": "switch.l34_sides", "light": True},
            {"name": "Water pump", "entity_id": "switch.elfsys_water_pump", "light": False},
        ],
        sensors={
            "temperature": "sensor.grow_room_temperature",
            "humidity": "sensor.grow_room_humidity",
        },
        ec_unit="ppm 500",
    )
    ids = {d["name"]: d["id"] for d in system.data["devices"]}
    for key, zone, preset, stage in (
        ("greens", "Layers 1+2", "leafy_greens", "Vegetative"),
        ("herbs", "Layers 3+4", "mixed_herbs", "Seedling"),
    ):
        role_map = {
            "center_lights": ids[f"{zone} center"],
            "side_lights": ids[f"{zone} sides"],
            "water_pump": ids["Water pump"],
        }
        system.set_plan(key, build_from_preset(preset, role_map, new_id))
        await system.start_grow(
            key, stage, date.today() - timedelta(days=9), name=zone, include_past_tasks=False
        )
    await system.record_reading(ph=6.1, ec=760)
    await system.add_custom_task(
        "Order replacement air stones", due=date.today() + timedelta(days=2)
    )
    app.start()

    web_app = build_web_app(app, Path(__file__).parent / "grow_planner" / "static")
    runner = web.AppRunner(web_app)
    await runner.setup()
    await web.TCPSite(runner, "127.0.0.1", port).start()
    print(f"Panel at http://localhost:{port}  (state in {tmp})", flush=True)
    await asyncio.Event().wait()


if __name__ == "__main__":
    with contextlib.suppress(KeyboardInterrupt):
        args = [a for a in sys.argv[1:] if not a.startswith("--")]
        asyncio.run(main(int(args[0]) if args else 8099, "--empty" in sys.argv))
