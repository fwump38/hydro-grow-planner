"""Mirrors the system's task instances into a Home Assistant to-do list.

The app owns the tasks; the to-do list is a view that can also check things off.
`reconcile()` is idempotent and safe to run after every change on either side:

- an open instance that is overdue or due within `TODO_HORIZON_DAYS` gets a to-do item (mapped by
  uid in `rt["todo_map"]`); later ones are added as they come near
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
from datetime import date, timedelta
import logging
from typing import Protocol

from .engine import GrowError, GrowSystem

_LOGGER = logging.getLogger(__name__)

# Tasks due further ahead than this stay off the list (matches the panel's "Next 7 days").
TODO_HORIZON_DAYS = 7
# Passes to wait for a just-added item to show up before adding it again.
MAX_UNSEEN_PASSES = 5


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
        # Instances added but not yet seen on the list -> passes waited for them.
        self._unseen: dict[str, int] = {}

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
        if not mapping and not foreign and not self._unseen:
            # First look at this list: whatever is on it already is not ours. (Not while we
            # are still waiting for items we just added to show up: those are ours.)
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

        # 2b. Only the upcoming tasks live on the list, as in the panel's "Next 7 days":
        # open items that are still further out are taken off again (they come back
        # when they near).
        horizon = (system.today + timedelta(days=TODO_HORIZON_DAYS)).isoformat()
        for instance_id, uid in list(mapping.items()):
            task = shown.get(instance_id)
            item = items.get(uid)
            if task and not task["done"] and task["due"] > horizon and item and not item.completed:
                await self.port.remove_item(uid)
                del mapping[instance_id]
                del items[uid]

        # 3. Push upcoming instances HA doesn't have yet.
        tagged = len(system.grows) > 1

        def claim(instance_id: str) -> bool:
            """Map an instance to an unclaimed item that is already on the list."""
            task = shown[instance_id]
            summary = _summary(task, tagged)
            taken = set(mapping.values())
            found = next(
                (
                    i
                    for i in items.values()
                    if i.uid not in taken
                    and i.uid not in foreign
                    and not i.completed
                    and i.summary == summary
                    and (i.due or "")[:10] == (task["due"] or "")[:10]
                ),
                None,
            )
            if found is None:
                return False
            mapping[instance_id] = found.uid
            self._unseen.pop(instance_id, None)
            return True

        def claim_unseen() -> None:
            # Some lists (iCloud Reminders) are slow to report a new item, so an item we
            # added earlier can turn up while we are busy with another one.
            for instance_id in [i for i in self._unseen if i in shown and i not in mapping]:
                claim(instance_id)

        for instance_id, task in shown.items():
            if instance_id in mapping or task["done"] or task["due"] > horizon:
                continue
            if claim(instance_id):
                continue
            if self._unseen.get(instance_id, 0) in range(1, MAX_UNSEEN_PASSES + 1):
                self._unseen[instance_id] += 1  # wait for the list to show what we added
                continue
            summary = _summary(task, tagged)
            before = set(items)
            await self.port.add_item(summary, task["due"], task["note"])
            items = {i.uid: i for i in await self.port.list_items()}
            claim_unseen()
            # Our item is the new one; never claim an item that was already there.
            # Lists report `due` in their own format (a date or a datetime), so compare days.
            taken = set(mapping.values())
            new = [i for i in items.values() if i.uid not in before and i.uid not in taken]
            match = next(
                (
                    i
                    for i in new
                    if not i.completed
                    and i.summary == summary
                    and (i.due or "")[:10] == (task["due"] or "")[:10]
                ),
                None,
            )
            if match is not None:
                mapping[instance_id] = match.uid
                self._unseen.pop(instance_id, None)
            else:
                _LOGGER.warning(
                    "Added %r (due %s) to %s but it was not on the list when read straight back "
                    "(%d items); waiting for it to appear",
                    summary,
                    task["due"],
                    system.data.get("todo_entity"),
                    len(items),
                )
                self._unseen[instance_id] = 1
        claim_unseen()

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
