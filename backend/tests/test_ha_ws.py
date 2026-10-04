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
            elif kind == "todo/item/list":
                result = {
                    "items": [
                        {"uid": "a", "summary": "Do it", "status": "completed", "due": "2026-09-20"}
                    ]
                }
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
        await client.fire_event("hydro_grow_planner_tasks_due", {"count": 2})
        calls = {m["type"]: m for m in fake.received}
        assert calls["call_service"]["target"] == {"entity_id": "switch.s"}
        assert calls["call_service"]["service_data"] == {}
        assert calls["fire_event"]["event_data"] == {"count": 2}
        with pytest.raises(HAError, match="boom"):
            await client.call_service("switch", "explode", {})
    finally:
        task.cancel()
        await session.close()


async def test_todo_list_port(fake: FakeServer) -> None:
    client, task, session = await connect(fake, {})
    try:
        await asyncio.wait_for(client.connected.wait(), 5)
        todo = client.todo("todo.grow")
        (item,) = await todo.list_items()
        assert item.uid == "a" and item.completed and item.due == "2026-09-20"
        await todo.add_item("Move lights", "2026-09-23", "note")
        await todo.set_completed("a", True)
        await todo.remove_item("a")
        services = [m for m in fake.received if m["type"] == "call_service"]
        assert [s["service"] for s in services] == ["add_item", "update_item", "remove_item"]
        assert services[0]["service_data"] == {
            "item": "Move lights",
            "due_date": "2026-09-23",
            "description": "note",
        }
        assert services[0]["target"] == {"entity_id": "todo.grow"}
        assert services[2]["service_data"] == {"item": ["a"]}
    finally:
        task.cancel()
        await session.close()


async def test_commands_fail_fast_when_disconnected() -> None:
    async with aiohttp.ClientSession() as session:
        client = HAClient("ws://127.0.0.1:1/websocket", "x", session)
        with pytest.raises(HAError):
            await client.fire_event("x", {})


async def test_bad_token_never_connects(fake: FakeServer, monkeypatch) -> None:
    monkeypatch.setattr("grow_planner.ha_ws.RECONNECT_DELAY", 0.05)
    states: dict = {}
    client, task, session = await connect(fake, states, token="wrong")
    try:
        await asyncio.sleep(0.3)
        assert not client.connected.is_set()
    finally:
        task.cancel()
        await session.close()
