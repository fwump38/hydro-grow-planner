"""Home Assistant websocket client.

Inside an app this talks to `ws://supervisor/core/websocket` with the Supervisor
token; for local development give it a URL and a long-lived access token.
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
import logging
from typing import Any

import aiohttp

from .ports import EntityState
from .todo_sync import TodoItem

_LOGGER = logging.getLogger(__name__)

StateCallback = Callable[[str, EntityState | None], None]
RECONNECT_DELAY = 5.0


class HAError(Exception):
    """Home Assistant rejected a command or the connection is down."""


def _entity_state(raw: dict[str, Any] | None) -> EntityState | None:
    if not raw:
        return None
    attributes = raw.get("attributes") or {}
    return EntityState(
        raw["state"], attributes.get("unit_of_measurement"), attributes.get("friendly_name")
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

    async def fire_event(self, event_type: str, data: dict[str, Any]) -> None:
        """Fire an event on the HA bus."""
        await self.command({"type": "fire_event", "event_type": event_type, "event_data": data})
        _LOGGER.info("Fired event %s", event_type)

    async def get_states(self) -> list[dict[str, Any]]:
        """Return every entity state."""
        return await self.command({"type": "get_states"})

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

    # -- to-do list (implements todo_sync.TodoPort) ----------------------------------------

    def todo(self, entity_id: str) -> TodoList:
        """Return a to-do list port for one entity."""
        return TodoList(self, entity_id)

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


class TodoList:
    """One Home Assistant to-do list (see todo_sync.TodoPort)."""

    def __init__(self, client: HAClient, entity_id: str) -> None:
        """Wrap a list entity."""
        self.client = client
        self.entity_id = entity_id

    async def list_items(self) -> list[TodoItem]:
        """Return every item."""
        result = await self.client.command({"type": "todo/item/list", "entity_id": self.entity_id})
        return [
            TodoItem(
                uid=i["uid"],
                summary=i["summary"],
                completed=i.get("status") == "completed",
                due=i.get("due"),
                description=i.get("description") or "",
            )
            for i in result["items"]
        ]

    async def add_item(self, summary: str, due: str | None, description: str) -> None:
        """Add an open item."""
        data: dict[str, Any] = {"item": summary}
        if due:
            data["due_date"] = due
        if description:
            data["description"] = description
        await self.client.call_service("todo", "add_item", data, {"entity_id": self.entity_id})

    async def set_completed(self, uid: str, completed: bool) -> None:
        """Check an item off or reopen it."""
        await self.client.call_service(
            "todo",
            "update_item",
            {"item": uid, "status": "completed" if completed else "needs_action"},
            {"entity_id": self.entity_id},
        )

    async def remove_item(self, uid: str) -> None:
        """Delete an item."""
        await self.client.call_service(
            "todo", "remove_item", {"item": [uid]}, {"entity_id": self.entity_id}
        )
