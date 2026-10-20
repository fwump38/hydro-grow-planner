"""Tests for the to-do mirror, against an in-memory to-do list."""

from __future__ import annotations

from datetime import timedelta
from itertools import count

from grow_planner.todo_sync import TODO_HORIZON_DAYS, TodoItem, TodoSync

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


async def setup(
    h: Harness, existing: list[tuple[str, str | None]] | None = None, adopt: bool = False
) -> tuple[TodoSync, FakeTodo]:
    todo = FakeTodo()
    for summary, due in existing or []:
        await todo.add_item(summary, due, "")
    h.system.data["todo_entity"] = "todo.grow"
    h.system.data["todo_adopt"] = adopt
    sync = TodoSync(h.system, todo)
    await h.start("Leafy Greens", stage_ref=3)
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
    sync, todo = await setup(h, adopt=True)
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


async def test_items_made_in_ha_are_left_alone_by_default(h: Harness) -> None:
    sync, todo = await setup(h)
    await todo.add_item("Buy milk", None, "")
    await sync.reconcile()
    assert all(t["title"] != "Buy milk" for t in h.system.task_items())
    assert "Buy milk" in todo.open_summaries()


async def test_existing_items_are_never_touched_or_claimed(h: Harness) -> None:
    # A shared reminders list: one item shares a name and date with a task of ours.
    today = h.system.today.isoformat()
    sync, todo = await setup(
        h, existing=[("Buy milk", None), ("Add nutrients", today), ("Old chore", "2020-01-01")]
    )
    mine = {i.uid for i in todo.items.values() if i.uid not in ("u1", "u2", "u3")}
    assert len(mine) > 0
    for uid in ("u1", "u2", "u3"):
        await todo.set_completed(uid, True)  # the owner ticks their own items off
    await sync.reconcile()
    await sync.reconcile()
    assert {i.summary for i in todo.items.values() if i.uid in ("u1", "u2", "u3")} == {
        "Buy milk",
        "Add nutrients",
        "Old chore",
    }
    assert all(t["title"] not in ("Buy milk", "Old chore") for t in h.system.task_items())
    assert "Add nutrients" in {i.summary for i in todo.items.values() if i.uid in mine}
    # Deleting a task removes only its own item.
    task = next(t for t in h.system.task_items() if t["title"] == "Move the grow lights")
    h.system.delete_task(task["id"])
    await sync.reconcile()
    assert {"u1", "u2", "u3"} <= set(todo.items)
    assert "Move the grow lights" not in todo.open_summaries()


async def test_turning_adoption_on_does_not_import_the_backlog(h: Harness) -> None:
    sync, todo = await setup(h, existing=[("Buy milk", None)])
    h.system.data["todo_adopt"] = True
    await sync.reconcile()
    assert all(t["title"] != "Buy milk" for t in h.system.task_items())
    await todo.add_item("Order nutrients", None, "")
    await sync.reconcile()
    assert any(t["title"] == "Order nutrients" for t in h.system.task_items())


async def test_only_upcoming_tasks_are_on_the_list(h: Harness) -> None:
    sync, todo = await setup(h)
    horizon = (h.system.today + timedelta(days=TODO_HORIZON_DAYS)).isoformat()
    far = [t for t in h.system.task_items() if t["due"] > horizon]
    assert far, "the fixture should have tasks beyond the window"
    assert all((i.due or "") <= horizon for i in todo.items.values())
    assert len(todo.items) < len(h.system.task_items())


async def test_tasks_are_added_as_they_come_near(h: Harness) -> None:
    sync, todo = await setup(h)
    on_list = set(todo.items)
    h.clock.advance(days=60)
    await sync.reconcile()
    assert set(todo.items) - on_list, "tasks that came within the window should be added"


async def test_datetime_due_from_the_list_does_not_duplicate(h: Harness) -> None:
    class DatetimeTodo(FakeTodo):
        async def add_item(self, summary: str, due: str | None, description: str) -> None:
            await super().add_item(summary, f"{due}T00:00:00" if due else None, description)

    todo = DatetimeTodo()
    h.system.data["todo_entity"] = "todo.grow"
    sync = TodoSync(h.system, todo)
    await h.start("Leafy Greens", stage_ref=3)
    await sync.reconcile()
    before = len(todo.items)
    await sync.reconcile()
    await sync.reconcile()
    assert len(todo.items) == before


async def test_slow_list_does_not_duplicate(h: Harness) -> None:
    class SlowTodo(FakeTodo):
        """Does not report a new item until the next time the list is read."""

        def __init__(self) -> None:
            super().__init__()
            self.hidden: dict[str, TodoItem] = {}

        async def list_items(self) -> list[TodoItem]:
            shown = list(self.items.values())
            self.items.update(self.hidden)
            self.hidden = {}
            return shown

        async def add_item(self, summary: str, due: str | None, description: str) -> None:
            uid = f"u{next(self._ids)}"
            self.hidden[uid] = TodoItem(uid, summary, False, due, description)

    todo = SlowTodo()
    h.system.data["todo_entity"] = "todo.grow"
    sync = TodoSync(h.system, todo)
    await h.start("Leafy Greens", stage_ref=3)
    for _ in range(5):
        await sync.reconcile()
    summaries = [i.summary for i in todo.items.values()]
    assert len(summaries) == len(set(summaries))


async def test_first_pass_on_a_lagging_list_does_not_double_add(h: Harness) -> None:
    class LaggyTodo(FakeTodo):
        """A new item is not reported until the list has been read twice more."""

        def __init__(self) -> None:
            super().__init__()
            self.age: dict[str, int] = {}

        async def list_items(self) -> list[TodoItem]:
            for uid in self.age:
                self.age[uid] += 1
            return [i for i in self.items.values() if self.age.get(i.uid, 99) > 2]

        async def add_item(self, summary: str, due: str | None, description: str) -> None:
            await super().add_item(summary, due, description)
            self.age[f"u{next(self._ids) - 1}"] = 0

    todo = LaggyTodo()
    h.system.data["todo_entity"] = "todo.grow"
    sync = TodoSync(h.system, todo)
    await h.start("Leafy Greens", stage_ref=3)
    for _ in range(8):
        await sync.reconcile()
    summaries = [i.summary for i in todo.items.values()]
    assert len(summaries) == len(set(summaries))
