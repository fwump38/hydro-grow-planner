"""Tests for the to-do mirror, against an in-memory to-do list."""

from __future__ import annotations

from datetime import timedelta
from itertools import count

from grow_planner.todo_sync import TodoItem, TodoSync

from .conftest import Harness


class FakeTodo:
    """Behaves like HA's local to-do list."""

    def __init__(self) -> None:
        self.items: dict[str, TodoItem] = {}
        self._ids = count(1)

    async def list_items(self) -> list[TodoItem]:
        return list(self.items.values())

    async def add_item(self, summary: str, due: str | None, description: str) -> None:
        uid = f"u{next(self._ids)}"
        self.items[uid] = TodoItem(uid, summary, False, due, description)

    async def set_completed(self, uid: str, completed: bool) -> None:
        old = self.items[uid]
        self.items[uid] = TodoItem(uid, old.summary, completed, old.due, old.description)

    async def remove_item(self, uid: str) -> None:
        del self.items[uid]

    def open_summaries(self) -> list[str]:
        return sorted(i.summary for i in self.items.values() if not i.completed)


async def setup(h: Harness) -> tuple[TodoSync, FakeTodo]:
    todo = FakeTodo()
    sync = TodoSync(h.system, todo)
    await h.system.start_grow("Leafy Greens", stage_ref=3)
    await sync.reconcile()
    return sync, todo


async def test_open_tasks_are_pushed_once(h: Harness) -> None:
    sync, todo = await setup(h)
    assert "Move the grow lights" in todo.open_summaries()
    before = len(todo.items)
    await sync.reconcile()
    await sync.reconcile()
    assert len(todo.items) == before  # idempotent


async def test_checking_off_in_ha_spawns_the_next_one(h: Harness) -> None:
    sync, todo = await setup(h)
    uid = next(i.uid for i in todo.items.values() if i.summary == "Move the grow lights")
    await todo.set_completed(uid, True)
    await sync.reconcile()
    await sync.reconcile()
    lights = [i for i in todo.items.values() if i.summary == "Move the grow lights"]
    assert sorted(i.completed for i in lights) == [False, True]
    new = next(i for i in lights if not i.completed)
    assert new.due == (h.system.today + timedelta(days=3)).isoformat()


async def test_completing_in_the_panel_checks_it_off_in_ha(h: Harness) -> None:
    sync, todo = await setup(h)
    task = next(t for t in h.system.task_items() if t["title"] == "Add nutrients")
    await h.system.complete_task(task["id"])
    await sync.reconcile()
    done = [i for i in todo.items.values() if i.summary == "Add nutrients" and i.completed]
    assert len(done) == 1
    assert len([i for i in todo.items.values() if i.summary == "Add nutrients"]) == 2


async def test_items_made_in_ha_are_adopted_as_custom_tasks(h: Harness) -> None:
    sync, todo = await setup(h)
    await todo.add_item("Order nutrients", "2026-09-25", "pH down too")
    await sync.reconcile()
    task = next(t for t in h.system.task_items() if t["title"] == "Order nutrients")
    assert task["custom"] and task["due"] == "2026-09-25" and task["note"] == "pH down too"
    count_after = len(todo.items)
    await sync.reconcile()
    assert len(todo.items) == count_after  # not adopted twice


async def test_deleted_in_ha_is_added_back(h: Harness) -> None:
    sync, todo = await setup(h)
    uid = next(i.uid for i in todo.items.values() if i.summary == "Add nutrients")
    await todo.remove_item(uid)
    await sync.reconcile()
    assert "Add nutrients" in todo.open_summaries()


async def test_deleting_in_the_panel_removes_the_item(h: Harness) -> None:
    sync, todo = await setup(h)
    task = next(t for t in h.system.task_items() if t["title"] == "Add nutrients")
    h.system.delete_task(task["id"])
    await sync.reconcile()
    assert "Add nutrients" not in todo.open_summaries()


async def test_stage_change_swaps_the_stage_tasks_in_ha(h: Harness) -> None:
    sync, todo = await setup(h)  # Vegetative
    assert "Add nutrients" in todo.open_summaries()
    await h.system.set_stage(1)  # Sprouting has no nutrient task
    await sync.reconcile()
    summaries = todo.open_summaries()
    assert "Check water volume" in summaries
    assert "Check if ready for Seedling" in summaries
    assert "Add nutrients" not in summaries
    assert "Check if ready to finish the grow" not in summaries
