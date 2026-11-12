"""Home Assistant websocket client.

Inside an app this talks to `ws://supervisor/core/websocket` with the Supervisor
token; for local development give it a URL and a long-lived access token.
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from datetime import datetime
import logging
from typing import Any

import aiohttp

from .hk_tasks import HKTask
from .ports import EntityState

_LOGGER = logging.getLogger(__name__)

StateCallback = Callable[[str, EntityState | None], None]
RECONNECT_DELAY = 5.0


class HAError(Exception):
    """Home Assistant rejected a command or the connection is down."""


def _entity_state(raw: dict[str, Any] | None) -> EntityState | None:
    if not raw:
        return None
    attributes = raw.get("attributes") or {}
    stamp = raw.get("last_reported") or raw.get("last_updated")
    try:
        updated = datetime.fromisoformat(stamp) if stamp else None
    except ValueError:
        updated = None
    return EntityState(
        raw["state"],
        attributes.get("unit_of_measurement"),
        attributes.get("friendly_name"),
        updated,
    )


class HAClient:
    """A reconnecting websocket connection to Home Assistant."""

    def __init__(self, url: str, token: str, session: aiohttp.ClientSession) -> None:
        """`url` is the websocket URL, e.g. ws://supervisor/core/websocket."""
        self.url = url
        self.token = token
        self._session = session
        self._ws: aiohttp.ClientWebSocketResponse | None = None
        self._ids = 0
        self._pending: dict[int, asyncio.Future[Any]] = {}
        self._subscriptions: dict[int, Callable[[dict[str, Any]], None]] = {}
        self.connected = asyncio.Event()

    # -- commands ------------------------------------------------------------------------

    async def command(self, payload: dict[str, Any]) -> Any:
        """Send a command and return its result."""
        ws = self._ws
        if ws is None or ws.closed:
            raise HAError("Not connected to Home Assistant")
        self._ids += 1
        msg_id = self._ids
        future: asyncio.Future[Any] = asyncio.get_running_loop().create_future()
        self._pending[msg_id] = future
        try:
            await ws.send_json({"id": msg_id, **payload})
            return await asyncio.wait_for(future, timeout=30)
        finally:
            self._pending.pop(msg_id, None)

    async def call_service(
        self,
        domain: str,
        service: str,
        data: dict[str, Any],
        target: dict[str, Any] | None = None,
    ) -> None:
        """Call a service. `entity_id` in `data` is moved into the target."""
        data = dict(data)
        if target is None and "entity_id" in data:
            target = {"entity_id": data.pop("entity_id")}
        payload: dict[str, Any] = {
            "type": "call_service",
            "domain": domain,
            "service": service,
            "service_data": data,
        }
        if target:
            payload["target"] = target
        await self.command(payload)

    async def call_service_response(
        self, domain: str, service: str, data: dict[str, Any]
    ) -> dict[str, Any]:
        """Call a service that returns data and return that response."""
        result = await self.command(
            {
                "type": "call_service",
                "domain": domain,
                "service": service,
                "service_data": data,
                "return_response": True,
            }
        )
        return (result or {}).get("response") or {}

    async def fire_event(self, event_type: str, data: dict[str, Any]) -> None:
        """Fire an event on the HA bus."""
        await self.command({"type": "fire_event", "event_type": event_type, "event_data": data})
        _LOGGER.info("Fired event %s", event_type)

    async def get_states(self) -> list[dict[str, Any]]:
        """Return every entity state."""
        return await self.command({"type": "get_states"})

    async def get_unit_system(self) -> dict[str, str]:
        """Return Home Assistant's unit system (temperature, volume, mass…)."""
        config = await self.command({"type": "get_config"})
        return config.get("unit_system") or {}

    async def subscribe(
        self, payload: dict[str, Any], callback: Callable[[dict[str, Any]], None]
    ) -> None:
        """Subscribe to events; `callback` gets each event message."""
        ws = self._ws
        if ws is None or ws.closed:
            raise HAError("Not connected to Home Assistant")
        self._ids += 1
        msg_id = self._ids
        self._subscriptions[msg_id] = callback
        future: asyncio.Future[Any] = asyncio.get_running_loop().create_future()
        self._pending[msg_id] = future
        await ws.send_json({"id": msg_id, **payload})
        try:
            await asyncio.wait_for(future, timeout=30)
        finally:
            self._pending.pop(msg_id, None)

    # -- Home Keeper (implements hk_tasks.HKPort) ------------------------------------------

    def home_keeper(self) -> HomeKeeper:
        """Return the Home Keeper port."""
        return HomeKeeper(self)

    # -- connection loop -----------------------------------------------------------------------

    async def run(
        self,
        on_state: StateCallback,
        on_connected: Callable[[], Awaitable[None]] | None = None,
    ) -> None:
        """Stay connected forever, feeding entity states to `on_state`."""
        while True:
            try:
                await self._connect_and_read(on_state, on_connected)
            except asyncio.CancelledError:
                raise
            except Exception as err:
                _LOGGER.warning("Home Assistant connection to %s lost: %s", self.url, err)
            self.connected.clear()
            self._fail_pending()
            await asyncio.sleep(RECONNECT_DELAY)

    def _fail_pending(self) -> None:
        for future in self._pending.values():
            if not future.done():
                future.set_exception(HAError("Connection lost"))
        self._pending.clear()
        self._subscriptions.clear()

    async def _connect_and_read(
        self, on_state: StateCallback, on_connected: Callable[[], Awaitable[None]] | None
    ) -> None:
        async with self._session.ws_connect(self.url, heartbeat=30) as ws:
            first = await ws.receive_json()
            if first.get("type") != "auth_required":
                raise HAError(f"Unexpected greeting: {first}")
            await ws.send_json({"type": "auth", "access_token": self.token})
            reply = await ws.receive_json()
            if reply.get("type") != "auth_ok":
                raise HAError("Home Assistant rejected the access token")
            self._ws = ws
            self._ids = 0
            _LOGGER.info("Connected to Home Assistant at %s", self.url)
            reader = asyncio.create_task(self._read(ws))
            try:
                await self.subscribe(
                    {"type": "subscribe_events", "event_type": "state_changed"},
                    lambda msg: self._on_state_changed(msg, on_state),
                )
                for raw in await self.get_states():
                    state = _entity_state(raw)
                    if state is not None:
                        on_state(raw["entity_id"], state)
                self.connected.set()
                if on_connected is not None:
                    await on_connected()
                await reader
            finally:
                reader.cancel()
                self._ws = None

    @staticmethod
    def _on_state_changed(msg: dict[str, Any], on_state: StateCallback) -> None:
        data = msg["event"]["data"]
        on_state(data["entity_id"], _entity_state(data.get("new_state")))

    async def _read(self, ws: aiohttp.ClientWebSocketResponse) -> None:
        async for msg in ws:
            if msg.type != aiohttp.WSMsgType.TEXT:
                continue
            data = msg.json()
            kind = data.get("type")
            if kind == "result":
                future = self._pending.get(data["id"])
                if future is None or future.done():
                    continue
                if data.get("success"):
                    future.set_result(data.get("result"))
                else:
                    error = data.get("error") or {}
                    future.set_exception(HAError(error.get("message", "Command failed")))
            elif kind == "event":
                callback = self._subscriptions.get(data["id"])
                if callback is not None:
                    try:
                        callback(data)
                    except Exception:
                        _LOGGER.exception("Error handling an event")


class HomeKeeper:
    """Home Keeper's task services (see hk_tasks.HKPort)."""

    DOMAIN = "home_keeper"

    def __init__(self, client: HAClient) -> None:
        """Wrap a client."""
        self.client = client

    async def list_tasks(self) -> list[HKTask]:
        """Return every task; raises HAError when Home Keeper is not installed or loaded."""
        response = await self.client.call_service_response(self.DOMAIN, "list_tasks", {})
        return [HKTask.from_dict(t) for t in response.get("tasks", [])]

    async def add_task(self, data: dict[str, Any]) -> str:
        """Create a task and return its id."""
        response = await self.client.call_service_response(self.DOMAIN, "add_task", data)
        task_id = response.get("task_id")
        if not task_id:
            raise HAError("Home Keeper did not return a task id")
        return str(task_id)

    async def update_task(self, task_id: str, data: dict[str, Any]) -> None:
        """Change a task."""
        await self.client.call_service(self.DOMAIN, "update_task", {"task_id": task_id, **data})

    async def delete_task(self, task_id: str) -> None:
        """Delete a task."""
        await self.client.call_service(self.DOMAIN, "delete_task", {"task_id": task_id})

    async def trigger_task(self, task_id: str) -> None:
        """Arm a triggered task."""
        await self.client.call_service(self.DOMAIN, "trigger_task", {"task_id": task_id})

    async def complete_task(self, task_id: str, completed_at: str | None = None) -> None:
        """Complete a task as Grow Planner."""
        data = {"task_id": task_id, "origin": "hydro_grow_planner"}
        if completed_at:
            data["completed_at"] = completed_at
        await self.client.call_service(self.DOMAIN, "complete_task", data)
