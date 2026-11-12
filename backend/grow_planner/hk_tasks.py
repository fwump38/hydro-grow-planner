"""Shows the system's tasks in Home Keeper (https://github.com/prestomation/ha-home-keeper).

Grow Planner works out *when* things are due (stage days, repeats, upkeep); Home Keeper
is where they are shown, done, snoozed, synced to a to-do list and notified about. The
add-on talks to it through its `home_keeper.*` services.

`reconcile()` is idempotent and safe to run after every change on either side:

- every open task instance becomes a managed one-off Home Keeper task with a due date
  (mapped in `rt["hk_map"]`); a repeating task has one open instance at a time, and
  completing it schedules the next
- a task checked off in Home Keeper completes its instance, which schedules the next one
- a task whose instance is gone (stage change, deleted, pruned) is removed from Home Keeper
- a task deleted in Home Keeper is added back; to stop a repeat, delete it in Grow Planner
- system upkeep (change the water, clean the pump...) is a native Home Keeper *floating* task,
  one per upkeep item (`rt["hk_upkeep"]`), so Home Keeper keeps its history and interval
  statistics. Home Keeper counts the interval from the last completion; the app creates the
  task once something is growing, pauses it (disables it) while nothing is, and when one task
  "covers" others (a deep clean covers a water change) completes those too
- "smart" tasks (record a reading, EC or pH out of range) are triggered tasks, one per
  condition: armed when the condition starts, cleared when it ends. Completing one while
  the condition still holds leaves it quiet until the condition clears and returns.

Only tasks whose `source.grow_planner.system_id` is this system's are ever touched.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import logging
from typing import Any, Protocol

from .engine import GrowError, GrowSystem

_LOGGER = logging.getLogger(__name__)

SOURCE_KEY = "grow_planner"
MANAGED_BY = {
    "integration": "hydro_grow_planner",
    "display_name": "Grow Planner",
    "icon": "mdi:sprout",
}
# Tasks fall due at this time of day (Home Keeper wants a datetime, the plan only a day).
DUE_TIME = "09:00:00"


@dataclass(frozen=True, slots=True)
class HKTask:
    """A Home Keeper task, reduced to what the sync uses."""

    id: str
    name: str
    next_due: str | None
    source: dict[str, Any]
    recurrence_type: str = ""
    last_completed: str | None = None

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> HKTask:
        """Build from a `list_tasks` record."""
        return cls(
            id=str(raw.get("task_id") or raw.get("id")),
            name=str(raw.get("name") or ""),
            next_due=raw.get("next_due"),
            source=raw.get("source") or {},
            recurrence_type=str(raw.get("recurrence_type") or ""),
            last_completed=raw.get("last_completed"),
        )

    @property
    def mine(self) -> dict[str, Any]:
        """Our part of `source`."""
        mine = self.source.get(SOURCE_KEY)
        return mine if isinstance(mine, dict) else {}


class HKPort(Protocol):
    """Access to Home Keeper's services."""

    async def list_tasks(self) -> list[HKTask]:
        """Return every task. Raises if Home Keeper is not available."""

    async def add_task(self, data: dict[str, Any]) -> str:
        """Create a task and return its id."""

    async def update_task(self, task_id: str, data: dict[str, Any]) -> None:
        """Change a task."""

    async def delete_task(self, task_id: str) -> None:
        """Delete a task."""

    async def trigger_task(self, task_id: str) -> None:
        """Arm a triggered task."""

    async def complete_task(self, task_id: str, completed_at: str | None = None) -> None:
        """Complete a task as Grow Planner (this clears a triggered task)."""


def _summary(task: dict[str, Any], tagged: bool) -> str:
    """Return the task name: with several grows, tasks say which one they are for."""
    title = str(task["title"])
    return f"{task['grow']}: {title}" if tagged and task["grow"] else title


def _due(day: str) -> str:
    return f"{day}T{DUE_TIME}"


class HKSync:
    """Keeps Home Keeper in step with one grow system."""

    def __init__(self, system: GrowSystem, port: HKPort) -> None:
        """Create the sync."""
        self.system = system
        self.port = port
        # Whether Home Keeper answered the last time; shown in the panel.
        self.available: bool | None = None
        # Completions announced by Home Keeper's events: task id -> ISO time.
        self._completed: dict[str, str] = {}

    def note_completion(self, task_id: str, completed_at: str | None) -> None:
        """Remember that Home Keeper completed a task (from its event)."""
        if task_id and completed_at:
            self._completed[task_id] = completed_at

    @property
    def _map(self) -> dict[str, str]:
        return self.system.rt.setdefault("hk_map", {})

    @property
    def _upkeep(self) -> dict[str, dict[str, Any]]:
        return self.system.rt.setdefault("hk_upkeep", {})

    @property
    def _smart(self) -> dict[str, dict[str, Any]]:
        return self.system.rt.setdefault("hk_smart", {})

    def _owned(self, task: HKTask) -> bool:
        return task.mine.get("system_id") == self.system.id

    async def reconcile(self) -> None:
        """Bring Home Keeper and the system in line."""
        system = self.system
        try:
            found = await self.port.list_tasks()
        except Exception as err:
            if self.available is not False:
                _LOGGER.warning("Home Keeper is not available: %s", err)
            self.available = system.home_keeper_available = False
            return
        self.available = system.home_keeper_available = True
        tasks = {t.id: t for t in found if self._owned(t)}
        mapping = self._map

        await self._pull_completions(tasks, mapping)
        shown = {t["id"]: t for t in system.task_items(include_done=False)}

        # Remove what has gone (stage change, deleted here, pruned) or was deleted in Home Keeper.
        for instance_id, hk_id in list(mapping.items()):
            if instance_id not in shown:
                if hk_id in tasks:
                    await self.port.delete_task(hk_id)
                    del tasks[hk_id]
                del mapping[instance_id]
            elif hk_id not in tasks:
                del mapping[instance_id]  # deleted in Home Keeper: added back below
        # Tasks of ours that nothing maps to (left over from a crash) go too.
        known = set(mapping.values())
        for hk_id, task in list(tasks.items()):
            if hk_id not in known and task.mine.get("kind", "task") == "task":
                await self.port.delete_task(hk_id)
                del tasks[hk_id]

        tagged = len(system.grows) > 1
        for instance_id, item in shown.items():
            hk_id = mapping.get(instance_id)
            if hk_id is None:
                mapping[instance_id] = await self.port.add_task(
                    {
                        "name": _summary(item, tagged),
                        "notes": item["note"],
                        "recurrence_type": "one-off",
                        "due": _due(item["due"]),
                        "source": {
                            SOURCE_KEY: {
                                "system_id": system.id,
                                "instance_id": instance_id,
                                "kind": "task",
                            }
                        },
                        "managed_by": MANAGED_BY,
                    }
                )
            elif (tasks[hk_id].next_due or "")[:10] != item["due"]:
                await self.port.update_task(hk_id, {"due": _due(item["due"])})

        await self._reconcile_upkeep(tasks)
        await self._reconcile_smart(tasks)
        self._completed.clear()
        system._on_save()

    async def _pull_completions(self, tasks: dict[str, HKTask], mapping: dict[str, str]) -> None:
        """Complete the instances whose Home Keeper task was checked off."""
        system = self.system
        open_ids = {t["id"] for t in system.task_items(include_done=False)}
        for instance_id, hk_id in list(mapping.items()):
            task = tasks.get(hk_id)
            if task is None or task.next_due is not None or instance_id not in open_ids:
                continue  # missing, still open, or already done here
            try:
                await system.complete_task(instance_id)
            except GrowError:
                _LOGGER.debug("Could not complete %s", instance_id)

    def _completions(self, tasks: dict[str, HKTask]) -> list[tuple[str, date]]:
        """Return (upkeep id, day) for upkeep tasks Home Keeper completed."""
        found = []
        for upkeep_id, entry in self._upkeep.items():
            hk_id = entry.get("hk_id")
            task = tasks.get(hk_id) if hk_id else None
            # The date we created the task with is where its clock starts, not a completion.
            stamps = [
                t
                for t in (self._completed.get(hk_id or ""), task and task.last_completed)
                if t and t != entry.get("seed")
            ]
            if stamps:
                found.append((upkeep_id, date.fromisoformat(max(stamps)[:10])))
        return found

    async def _reconcile_upkeep(self, tasks: dict[str, HKTask]) -> None:
        """Keep one floating Home Keeper task per upkeep item."""
        system = self.system
        state = self._upkeep
        defs = {m["id"]: m for m in system.upkeep_defs()}

        for upkeep_id, day in self._completions(tasks):
            definition = defs.get(upkeep_id)
            if definition is None or not system.upkeep_done(upkeep_id, day):
                continue
            # Doing this one also did what it covers: complete those in Home Keeper too.
            for covered in definition["covers"]:
                if system.upkeep_done(covered, day):
                    hk_id = state.get(covered, {}).get("hk_id")
                    if hk_id in tasks:
                        await self.port.complete_task(hk_id, f"{day.isoformat()}T{DUE_TIME}")

        active = system.is_active
        for upkeep_id, definition in defs.items():
            entry = state.setdefault(upkeep_id, {})
            signature = f"{definition['title']}|{definition['note']}|{definition['every']}"
            hk_id = entry.get("hk_id")
            if hk_id not in tasks:
                anchor = system.upkeep_anchor(upkeep_id)
                if anchor is None:
                    continue  # nothing has grown yet: no clock to run
                seed = f"{anchor.isoformat()}T{DUE_TIME}"
                entry.update(
                    seed=seed,
                    hk_id=await self.port.add_task(
                        {
                            "name": definition["title"],
                            "notes": definition["note"],
                            "recurrence_type": "floating",
                            "interval": definition["every"],
                            "unit": "days",
                            "last_completed": seed,
                            "enabled": active,
                            "source": {
                                SOURCE_KEY: {
                                    "system_id": system.id,
                                    "key": upkeep_id,
                                    "kind": "upkeep",
                                }
                            },
                            "managed_by": MANAGED_BY,
                        }
                    ),
                    signature=signature,
                    enabled=active,
                )
                continue
            changes: dict[str, Any] = {}
            if entry.get("signature") != signature:
                changes.update(
                    name=definition["title"],
                    notes=definition["note"],
                    interval=definition["every"],
                    unit="days",
                )
            if entry.get("enabled") != active:
                changes["enabled"] = active  # upkeep waits while nothing is growing
            if changes:
                await self.port.update_task(hk_id, changes)
                entry.update(signature=signature, enabled=active)
        for upkeep_id, entry in list(state.items()):
            if upkeep_id not in defs:  # removed or turned off in the settings
                if entry.get("hk_id") in tasks:
                    await self.port.delete_task(entry["hk_id"])
                del state[upkeep_id]

    async def _reconcile_smart(self, tasks: dict[str, HKTask]) -> None:
        """Arm and clear the condition tasks."""
        state = self._smart
        conditions = self.system.smart_conditions()
        for key, cond in conditions.items():
            entry = state.setdefault(key, {})
            hk_id = entry.get("hk_id")
            if hk_id not in tasks:
                entry["hk_id"] = await self.port.add_task(
                    {
                        "name": cond["title"],
                        "notes": cond["note"],
                        "recurrence_type": "triggered",
                        "source": {
                            SOURCE_KEY: {
                                "system_id": self.system.id,
                                "key": key,
                                "kind": "smart",
                            }
                        },
                        "managed_by": MANAGED_BY,
                    }
                )
                entry["active"] = True
            elif not entry.get("active"):
                # The condition just began again: arm the (dormant) task.
                await self.port.trigger_task(hk_id)
                entry["active"] = True
        for key, entry in list(state.items()):
            if key in conditions:
                continue
            hk_id = entry.get("hk_id")
            if entry.get("active") and hk_id in tasks and tasks[hk_id].next_due is not None:
                await self.port.complete_task(hk_id)  # condition over: clear it
            entry["active"] = False
        # A condition task that was deleted in Home Keeper is forgotten, then re-added above.
        for key, entry in list(state.items()):
            if entry.get("hk_id") not in tasks and key not in conditions:
                del state[key]
