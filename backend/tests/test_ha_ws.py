"""Tests for the websocket client, against a small fake Home Assistant."""

from __future__ import annotations

import asyncio
from typing import Any

import aiohttp
from aiohttp import web
import pytest

from grow_planner.ha_ws import HAClient, HAError
from grow_planner.ports import EntityState

TOKEN = "secret"


class FakeServer:
    def __init__(self) -> None:
        self.received: list[dict[str, Any]] = []
        self.ws: web.WebSocketResponse | None = None
        self.accept_token = TOKEN

    async def handler(self, request: web.Request) -> web.WebSocketResponse:
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        self.ws = ws
        await ws.send_json({"type": "auth_required"})
        auth = await ws.receive_json()
        if auth["access_token"] != self.accept_token:
            await ws.send_json({"type": "auth_invalid"})
            await ws.close()
            return ws
        await ws.send_json({"type": "auth_ok"})
        async for msg in ws:
            data = msg.json()
            self.received.append(data)
            kind = data["type"]
            if kind == "get_states":
                result: Any = [
                    {
                        "entity_id": "sensor.t",
                        "state": "21",
                        "attributes": {"unit_of_measurement": "°C"},
                    },
                    {"entity_id": "switch.s", "state": "off", "attributes": {}},
                ]
            elif kind == "call_service" and data["service"] == "list_tasks":
                result = {
                    "context": {},
                    "response": {
                        "tasks": [
                            {
                                "task_id": "a",
                                "name": "Do it",
                                "next_due": None,
                                "source": {"grow_planner": {"system_id": "s"}},
                                "recurrence_type": "one-off",
                            }
                        ]
                    },
                }
            elif kind == "call_service" and data["service"] == "add_task":
                result = {"context": {}, "response": {"task_id": "new"}}
            elif kind == "call_service" and data["service"] == "explode":
                await ws.send_json(
                    {
                        "id": data["id"],
                        "type": "result",
                        "success": False,
                        "error": {"message": "boom"},
                    }
                )
                continue
            else:
                result = None
            await ws.send_json(
                {"id": data["id"], "type": "result", "success": True, "result": result}
            )
        return ws


@pytest.fixture
async def fake(aiohttp_server):
    server = FakeServer()
    app = web.Application()
    app.router.add_get("/websocket", server.handler)
    runner = await aiohttp_server(app)
    server.url = f"ws://127.0.0.1:{runner.port}/websocket"
    return server


async def connect(fake: FakeServer, states: dict, token: str = TOKEN):
    session = aiohttp.ClientSession()
    client = HAClient(fake.url, token, session)

    def on_state(entity_id: str, state: EntityState | None) -> None:
        if state is None:
            states.pop(entity_id, None)
        else:
            states[entity_id] = state

    task = asyncio.create_task(client.run(on_state))
    return client, task, session


async def test_auth_initial_states_and_live_updates(fake: FakeServer) -> None:
    states: dict[str, EntityState] = {}
    client, task, session = await connect(fake, states)
    try:
        await asyncio.wait_for(client.connected.wait(), 5)
        assert states["sensor.t"] == EntityState("21", "°C")
        assert states["switch.s"] == EntityState("off", None)

        assert fake.ws is not None
        await fake.ws.send_json(
            {
                "id": 1,
                "type": "event",
                "event": {
                    "event_type": "state_changed",
                    "data": {
                        "entity_id": "switch.s",
                        "new_state": {"state": "on", "attributes": {}},
                    },
                },
            }
        )
        await asyncio.sleep(0.05)
        assert states["switch.s"].state == "on"
    finally:
        task.cancel()
        await session.close()


async def test_commands(fake: FakeServer) -> None:
    client, task, session = await connect(fake, {})
    try:
        await asyncio.wait_for(client.connected.wait(), 5)
        await client.call_service("switch", "turn_on", {"entity_id": "switch.s"})
        await client.fire_event("hydro_grow_planner_out_of_range", {"metric": "ph"})
        calls = {m["type"]: m for m in fake.received}
        assert calls["call_service"]["target"] == {"entity_id": "switch.s"}
        assert calls["call_service"]["service_data"] == {}
        assert calls["fire_event"]["event_data"] == {"metric": "ph"}
        with pytest.raises(HAError, match="boom"):
            await client.call_service("switch", "explode", {})
    finally:
        task.cancel()
        await session.close()


async def test_home_keeper_port(fake: FakeServer) -> None:
    client, task, session = await connect(fake, {})
    try:
        await asyncio.wait_for(client.connected.wait(), 5)
        hk = client.home_keeper()
        (item,) = await hk.list_tasks()
        assert item.id == "a" and item.next_due is None and item.mine == {"system_id": "s"}
        assert await hk.add_task({"name": "Move lights", "recurrence_type": "one-off"}) == "new"
        await hk.update_task("a", {"due": "2026-09-23T09:00:00"})
        await hk.trigger_task("a")
        await hk.complete_task("a")
        await hk.delete_task("a")
        services = [m for m in fake.received if m["type"] == "call_service"]
        assert [s["service"] for s in services] == [
            "list_tasks",
            "add_task",
            "update_task",
            "trigger_task",
            "complete_task",
            "delete_task",
        ]
        assert all(s["domain"] == "home_keeper" for s in services)
        assert services[0]["return_response"] and services[1]["return_response"]
        assert services[2]["service_data"] == {"task_id": "a", "due": "2026-09-23T09:00:00"}
        assert services[4]["service_data"] == {"task_id": "a", "origin": "hydro_grow_planner"}
    finally:
        task.cancel()
        await session.close()
