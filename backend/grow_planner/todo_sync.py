"""Mirrors the system's task instances into a Home Assistant to-do list.

The app owns the tasks; the to-do list is a view that can also check things off.
`reconcile()` is idempotent and safe to run after every change on either side:

- an open instance gets a to-do item (mapped by uid in `rt["todo_map"]`)
- an item checked off in HA completes its instance, which schedules the next one of
  a repeating task (and the next pass adds that item)
- an instance completed in the panel is checked off in HA
- an item whose instance is gone (pruned, deleted) is removed from HA
- an item created in HA is adopted as a one-off custom task, only if the system opts in
  (`todo_adopt`), and never one that was already on the list before

The list may be someone's everyday reminders list, so the sync only ever touches items it
created itself (the ones in `rt["todo_map"]`). Everything else it sees is left alone.

Deleting an item in HA does not delete the task: it is added back. Delete tasks in
the panel, which is also how a repeating task is stopped.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import logging
from typing import Protocol

from .engine import GrowError, GrowSystem

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class TodoItem:
    """A to-do list item as Home Assistant reports it."""

    uid: str
    summary: str
    completed: bool
    due: str | None = None
    description: str = ""


class TodoPort(Protocol):
    """Access to one to-do list."""

    async def list_items(self) -> list[TodoItem]:
        """Return every item."""

    async def add_item(self, summary: str, due: str | None, description: str) -> None:
        """Add an open item."""

    async def set_completed(self, uid: str, completed: bool) -> None:
        """Check an item off or reopen it."""

    async def remove_item(self, uid: str) -> None:
        """Delete an item."""


def _summary(task: dict[str, str | None], tagged: bool) -> str:
    """Return the to-do text: with several grows, tasks say which one they are for."""
    title = str(task["title"])
    return f"{task['grow']}: {title}" if tagged and task["grow"] else title


class TodoSync:
    """Keeps one to-do list in step with one grow system."""

    def __init__(self, system: GrowSystem, port: TodoPort) -> None:
        """Create the sync."""
        self.system = system
        self.port = port

    @property
    def _foreign(self) -> set[str]:
        """Return the uids of items that were on the list before we looked, or are not ours."""
        entity = self.system.data.get("todo_entity")
        record = self.system.rt.get("todo_foreign")
        if not isinstance(record, dict) or record.get("entity") != entity:
            record = {"entity": entity, "uids": []}
            self.system.rt["todo_foreign"] = record
        return set(record["uids"])

    def _remember_foreign(self, uids: set[str]) -> None:
        self.system.rt["todo_foreign"]["uids"] = sorted(uids)

    @property
    def _map(self) -> dict[str, str]:
        return self.system.rt.setdefault("todo_map", {})

    async def reconcile(self) -> None:
        """Bring the list and the system in line."""
        system = self.system
        items = {i.uid: i for i in await self.port.list_items()}
        mapping = self._map
        foreign = self._foreign
        if not mapping and not foreign:
            # First look at this list: whatever is on it already is not ours.
            foreign = set(items)
        instances = {i["id"]: i for i in system.rt["instances"]}
        shown = {t["id"]: t for t in system.task_items()}

        # 1. Pull completions made in HA (this may create new instances).
        for instance_id, uid in list(mapping.items()):
            item = items.get(uid)
            inst = instances.get(instance_id)
            if item is None or inst is None:
                continue
            if item.completed and not inst.get("completed_on"):
                try:
                    await system.complete_task(instance_id)
                except GrowError:
                    _LOGGER.debug("Could not complete %s", instance_id)
            elif not item.completed and inst.get("completed_on"):
                await self.port.set_completed(uid, True)

        # Completing may have added instances; look again.
        instances = {i["id"]: i for i in system.rt["instances"]}
        shown = {t["id"]: t for t in system.task_items()}

        # 2. Forget mappings whose item or instance has gone.
        for instance_id, uid in list(mapping.items()):
            if instance_id not in instances:
                if uid in items:
                    await self.port.remove_item(uid)
                del mapping[instance_id]
            elif uid not in items:
                del mapping[instance_id]  # deleted in HA: it is added back below

        # 3. Push instances HA doesn't have yet.
        tagged = len(system.grows) > 1
        for instance_id, task in shown.items():
            if instance_id in mapping or task["done"]:
                continue
            summary = _summary(task, tagged)
            before = set(items)
            await self.port.add_item(summary, task["due"], task["note"])
            items = {i.uid: i for i in await self.port.list_items()}
            # Our item is the new one; never claim an item that was already there.
            match = next(
                (
                    i
                    for i in items.values()
                    if i.uid not in before
                    and not i.completed
                    and i.summary == summary
                    and (i.due or None) == (task["due"] or None)
                ),
                None,
            )
            if match is not None:
                mapping[instance_id] = match.uid

        # 4. Adopt items made in HA, if asked to; otherwise just note that they aren't ours.
        # Items seen while adopting is off are never imported later, so switching it on
        # doesn't pull in the whole existing list.
        taken = set(mapping.values())
        adopt = bool(system.data.get("todo_adopt"))
        for item in items.values():
            if item.uid in taken:
                continue
            if not adopt or item.completed or item.uid in foreign:
                foreign.add(item.uid)
                continue
            due = date.fromisoformat(item.due[:10]) if item.due else None
            instance_id = await system.add_custom_task(item.summary, due, item.description)
            mapping[instance_id] = item.uid
        self._remember_foreign(foreign & set(items))
        system._on_save()
