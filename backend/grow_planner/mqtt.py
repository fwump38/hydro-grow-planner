"""MQTT connection: publishes discovery + state and receives entity commands."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
import json
import logging
from typing import Any

import aiomqtt

from .mqtt_entities import DISCOVERY_PREFIX, STATUS_TOPIC, TOPIC_PREFIX

_LOGGER = logging.getLogger(__name__)

Message = tuple[str, str, bool]  # topic, payload, retain
CommandCallback = Callable[[str, str, str], Awaitable[None]]  # system_id, key, payload
RECONNECT_DELAY = 5.0


class Outbox:
    """Remembers what is published so only changes are sent.

    Discovery configs that disappeared (a device was removed, a sensor was added so
    the manual number is no longer needed) are cleared with an empty retained
    payload, which removes the entity from Home Assistant.
    """

    def __init__(self) -> None:
        """Start empty."""
        self._configs: dict[str, str] = {}
        self._states: dict[str, str] = {}
        self._owned: dict[str, set[str]] = {}  # system_id -> config topics

    def update(
        self, system_id: str, configs: dict[str, dict[str, Any]], states: dict[str, str]
    ) -> list[Message]:
        """Return the messages needed to bring the broker up to date."""
        messages: list[Message] = []
        encoded = {topic: json.dumps(payload, sort_keys=True) for topic, payload in configs.items()}
        for topic in self._owned.get(system_id, set()) - set(encoded):
            messages.append((topic, "", True))
            self._forget(topic)
        for topic, payload in encoded.items():
            if self._configs.get(topic) != payload:
                self._configs[topic] = payload
                messages.append((topic, payload, True))
        self._owned[system_id] = set(encoded)
        for topic, payload in states.items():
            if self._states.get(topic) != payload:
                self._states[topic] = payload
                messages.append((topic, payload, True))
        return messages

    def remove_system(self, system_id: str) -> list[Message]:
        """Return the messages that delete a system's entities."""
        topics = self._owned.pop(system_id, set())
        for topic in topics:
            self._forget(topic)
        prefix = f"{TOPIC_PREFIX}/{system_id}/"
        for topic in [t for t in self._states if t.startswith(prefix)]:
            del self._states[topic]
        return [(topic, "", True) for topic in sorted(topics)]

    def _forget(self, config_topic: str) -> None:
        """Drop a discovery config and the state topics it pointed at."""
        payload = json.loads(self._configs.pop(config_topic, "{}"))
        for key in ("state_topic", "json_attributes_topic"):
            if topic := payload.get(key):
                self._states.pop(topic, None)

    def everything(self) -> list[Message]:
        """Return every message, e.g. after a reconnect (configs first)."""
        return [(t, p, True) for t, p in self._configs.items()] + [
            (t, p, True) for t, p in self._states.items()
        ]


def parse_command_topic(topic: str) -> tuple[str, str] | None:
    """Split `hydro_grow_planner/<system>/<key>/set` into (system_id, key)."""
    parts = topic.split("/")
    if len(parts) == 4 and parts[0] == TOPIC_PREFIX and parts[3] == "set":
        return parts[1], parts[2]
    return None


class MqttClient:
    """Keeps a broker connection and sends whatever is queued."""

    def __init__(
        self,
        host: str,
        port: int,
        username: str | None,
        password: str | None,
        on_command: CommandCallback,
        tls: bool = False,
    ) -> None:
        """Create the client; call run() to connect."""
        self._where = f"{host}:{port}"
        self._kwargs: dict[str, Any] = {
            "hostname": host,
            "port": port,
            "username": username or None,
            "password": password or None,
            "will": aiomqtt.Will(STATUS_TOPIC, "offline", retain=True),
        }
        if tls:
            import ssl

            self._kwargs["tls_context"] = ssl.create_default_context()
        self._on_command = on_command
        self.outbox = Outbox()
        self._queue: asyncio.Queue[Message] = asyncio.Queue()
        self.connected = asyncio.Event()

    def publish_system(
        self, system_id: str, configs: dict[str, dict[str, Any]], states: dict[str, str]
    ) -> None:
        """Queue whatever changed for a system."""
        for message in self.outbox.update(system_id, configs, states):
            self._queue.put_nowait(message)

    def remove_system(self, system_id: str) -> None:
        """Queue removal of a system's entities."""
        for message in self.outbox.remove_system(system_id):
            self._queue.put_nowait(message)

    async def run(self) -> None:
        """Stay connected forever."""
        while True:
            try:
                await self._session()
            except asyncio.CancelledError:
                raise
            except aiomqtt.MqttError as err:
                _LOGGER.warning("MQTT connection to %s lost: %s", self._where, err)
            self.connected.clear()
            await asyncio.sleep(RECONNECT_DELAY)

    async def _session(self) -> None:
        async with aiomqtt.Client(**self._kwargs) as client:
            await client.publish(STATUS_TOPIC, "online", retain=True)
            await client.subscribe(f"{TOPIC_PREFIX}/+/+/set")
            # Everything is resent: the broker may have lost retained state.
            while not self._queue.empty():
                self._queue.get_nowait()
            for topic, payload, retain in self.outbox.everything():
                await client.publish(topic, payload, retain=retain)
            self.connected.set()
            _LOGGER.info("Connected to the MQTT broker at %s", self._where)
            sender = asyncio.create_task(self._send(client))
            try:
                async for message in client.messages:
                    await self._dispatch(str(message.topic), message.payload)
            finally:
                sender.cancel()

    async def _send(self, client: aiomqtt.Client) -> None:
        while True:
            topic, payload, retain = await self._queue.get()
            await client.publish(topic, payload, retain=retain)

    async def _dispatch(self, topic: str, payload: Any) -> None:
        parsed = parse_command_topic(topic)
        if parsed is None:
            return
        text = payload.decode() if isinstance(payload, bytes | bytearray) else str(payload)
        try:
            await self._on_command(parsed[0], parsed[1], text)
        except Exception:
            _LOGGER.exception("Command %s failed", topic)


__all__ = ["DISCOVERY_PREFIX", "MqttClient", "Outbox", "parse_command_topic"]
