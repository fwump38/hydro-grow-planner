"""The app: all grow systems plus the adapters that connect them to the world."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
import contextlib
import logging
from typing import Any, Protocol

from .core.models import new_id
from .engine import GrowError, GrowSystem, new_system_data
from .mqtt_entities import build, handle_command
from .ports import Clock, EntityState, HAPort, ReadingsPort
from .snapshot import snapshot
from .store import Store
from .todo_sync import TodoPort, TodoSync

_LOGGER = logging.getLogger(__name__)


class MqttSink(Protocol):
    """What the app needs from the MQTT client."""

    def publish_system(
        self, system_id: str, configs: dict[str, dict[str, Any]], states: dict[str, str]
    ) -> None:
        """Queue discovery and state."""

    def remove_system(self, system_id: str) -> None:
        """Queue removal of a system's entities."""


class HAConnection(HAPort, Protocol):
    """What the app needs from the HA client beyond HAPort."""

    def todo(self, entity_id: str) -> TodoPort:
        """Return a to-do list port."""

    async def subscribe(
        self, payload: dict[str, Any], callback: Callable[[dict[str, Any]], None]
    ) -> None:
        """Subscribe to events."""


class App:
    """Owns the systems and runs their background loops."""

    def __init__(
        self,
        store: Store,
        ha: HAConnection,
        readings: ReadingsPort,
        mqtt: MqttSink | None,
        clock: Clock,
    ) -> None:
        """Create the app; call load() then start()."""
        self.store = store
        self.ha = ha
        self.readings = readings
        self.mqtt = mqtt
        self.clock = clock
        self.systems: dict[str, GrowSystem] = {}
        self.all_states: dict[str, EntityState] = {}
        self._dirty: set[str] = set()
        self._flusher: asyncio.Task[None] | None = None
        self._wake: dict[str, asyncio.Event] = {}
        self._tasks: list[asyncio.Task[Any]] = []
        self._todo_syncs: dict[str, tuple[str, TodoSync]] = {}
        self._todo_lock = asyncio.Lock()
        self._listeners: set[asyncio.Queue[dict[str, Any]]] = set()

    # -- systems ------------------------------------------------------------------------------

    def load(self) -> None:
        """Create a GrowSystem for everything in the store."""
        for data in self.store.systems.values():
            self._adopt(data)

    def _adopt(self, data: dict[str, Any]) -> GrowSystem:
        system = GrowSystem(
            data,
            self.ha,
            self.clock,
            self.readings,
            on_save=self.store.save,
            on_change=lambda: self._on_change(system),
        )
        # Every system reads the one table of entity states, so a device or sensor
        # added later already has a state.
        system.states = self.all_states
        self.systems[system.id] = system
        self._wake[system.id] = asyncio.Event()
        return system

    def create_system(self, name: str) -> GrowSystem:
        """Add an empty grow system."""
        name = name.strip()
        if not name:
            raise GrowError("A system needs a name")
        if any(s.name.casefold() == name.casefold() for s in self.systems.values()):
            raise GrowError(f"There is already a system called {name}")
        data = new_system_data(new_id(), name)
        self.store.systems[data["id"]] = data
        system = self._adopt(data)
        self.store.save()
        self._on_change(system)
        if self._tasks:
            self._tasks.append(asyncio.create_task(self._loop(system)))
        return system

    def delete_system(self, system_id: str) -> None:
        """Remove a system and its entities."""
        if self.systems.pop(system_id, None) is None:
            raise GrowError("Unknown system")
        self._wake.pop(system_id, None)
        self._todo_syncs.pop(system_id, None)
        self.store.systems.pop(system_id, None)
        self.store.save()
        if self.mqtt is not None:
            self.mqtt.remove_system(system_id)
        self._broadcast({"type": "removed", "system_id": system_id})

    def get(self, system_id: str) -> GrowSystem:
        """Return a system or raise GrowError."""
        try:
            return self.systems[system_id]
        except KeyError:
            raise GrowError("Unknown system") from None

    # -- change fan-out ------------------------------------------------------------------------

    def _on_change(self, system: GrowSystem) -> None:
        self._dirty.add(system.id)
        wake = self._wake.get(system.id)
        if wake is not None:
            wake.set()
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            return
        if self._flusher is None or self._flusher.done():
            self._flusher = loop.create_task(self._flush())

    async def _flush(self) -> None:
        await asyncio.sleep(0)  # let a burst of changes settle into one pass
        while self._dirty:
            system_id = self._dirty.pop()
            system = self.systems.get(system_id)
            if system is None:
                continue
            if self.mqtt is not None:
                try:
                    self.mqtt.publish_system(system_id, *build(snapshot(system)))
                except Exception:
                    _LOGGER.exception("Could not publish %s", system.name)
            self._broadcast({"type": "changed", "system_id": system_id})
            await self._reconcile_todo(system)

    async def settle(self) -> None:
        """Wait for pending change fan-out (used by tests and shutdown)."""
        while self._flusher is not None and not self._flusher.done():
            await self._flusher

    async def _reconcile_todo(self, system: GrowSystem) -> None:
        entity = system.data.get("todo_entity")
        if not entity:
            self._todo_syncs.pop(system.id, None)
            return
        cached = self._todo_syncs.get(system.id)
        if cached is None or cached[0] != entity:
            cached = (entity, TodoSync(system, self.ha.todo(entity)))
            self._todo_syncs[system.id] = cached
        async with self._todo_lock:
            try:
                await cached[1].reconcile()
            except Exception:
                _LOGGER.warning("To-do sync with %s failed", entity, exc_info=True)

    # -- live updates for the panel --------------------------------------------------------------

    def subscribe(self) -> asyncio.Queue[dict[str, Any]]:
        """Return a queue that receives change notifications."""
        queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue(maxsize=50)
        self._listeners.add(queue)
        return queue

    def unsubscribe(self, queue: asyncio.Queue[dict[str, Any]]) -> None:
        """Stop notifying a queue."""
        self._listeners.discard(queue)

    def _broadcast(self, message: dict[str, Any]) -> None:
        for queue in self._listeners:
            if queue.full():
                queue.get_nowait()
            queue.put_nowait(message)

    # -- inputs ------------------------------------------------------------------------------------

    def on_ha_state(self, entity_id: str, state: EntityState | None) -> None:
        """Feed an entity state to every system that cares about it."""
        previous = self.all_states.get(entity_id)
        if state is None:
            self.all_states.pop(entity_id, None)
        else:
            self.all_states[entity_id] = state
        if state == previous:
            # Attribute-only updates (e.g. a "last seen" timestamp) change nothing we use.
            return
        for system in self.systems.values():
            system.set_state(entity_id, state)
            sensors = set(system.data["sensors"].values())
            devices = {d["entity_id"] for d in system.data["devices"]}
            if entity_id in sensors:
                self._on_change(system)
                self._tasks_for_alerts(system)
            elif entity_id in devices:
                self._on_change(system)

    def _tasks_for_alerts(self, system: GrowSystem) -> None:
        task = asyncio.get_running_loop().create_task(system.evaluate_alerts())
        task.add_done_callback(self._log_failure)

    @staticmethod
    def _log_failure(task: asyncio.Task[Any]) -> None:
        if not task.cancelled() and (err := task.exception()) is not None:
            _LOGGER.error("Background task failed: %s", err, exc_info=err)

    async def on_mqtt_command(self, system_id: str, key: str, payload: str) -> None:
        """Handle a command from a Home Assistant entity."""
        system = self.systems.get(system_id)
        if system is None:
            return
        try:
            await handle_command(system, key, payload)
        except (GrowError, ValueError) as err:
            _LOGGER.warning("Command %s for %s rejected: %s", key, system.name, err)

    async def on_ha_connected(self) -> None:
        """Run after (re)connecting to Home Assistant."""
        for system in self.systems.values():
            await system.sync(force=True)
            entity = system.data.get("todo_entity")
            if entity:
                await self._subscribe_todo(system, entity)
            self._on_change(system)

    async def _subscribe_todo(self, system: GrowSystem, entity: str) -> None:
        def changed(_event: dict[str, Any]) -> None:
            self._on_change(system)

        try:
            await self.ha.subscribe({"type": "todo/item/subscribe", "entity_id": entity}, changed)
        except Exception:
            _LOGGER.warning("Could not watch %s", entity, exc_info=True)

    # -- background loops ----------------------------------------------------------------------------

    async def _loop(self, system: GrowSystem) -> None:
        while system.id in self.systems:
            try:
                await system.tick()
            except Exception:
                _LOGGER.exception("Tick failed for %s", system.name)
            wake = self._wake.get(system.id)
            if wake is None:
                return
            # Changes made by the tick itself must not wake it again.
            wake.clear()
            delay = max(1.0, (system.next_wakeup() - system.now).total_seconds())
            with contextlib.suppress(TimeoutError):
                await asyncio.wait_for(wake.wait(), delay)
            wake.clear()

    def start(self) -> None:
        """Start the per-system loops (the HA and MQTT loops are run by the caller)."""
        self._tasks = [asyncio.create_task(self._loop(s)) for s in self.systems.values()]

    async def stop(self) -> None:
        """Stop the loops and flush state."""
        for task in self._tasks:
            task.cancel()
        await asyncio.gather(*self._tasks, return_exceptions=True)
        self._tasks = []
        await self.settle()
        self.store.flush()
