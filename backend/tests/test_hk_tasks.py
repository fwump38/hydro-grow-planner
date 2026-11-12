"""Tests for the Home Keeper sync, against an in-memory Home Keeper."""

from __future__ import annotations

from datetime import timedelta
from itertools import count
from typing import Any

from grow_planner.hk_tasks import HKSync, HKTask
from grow_planner.snapshot import snapshot

from .conftest import Harness


class FakeHK:
    """Behaves like Home Keeper's task services, as far as the sync cares."""

    def __init__(self) -> None:
        self.tasks: dict[str, dict[str, Any]] = {}
        self._ids = count(1)
        self.down = False
        self.calls: list[str] = []

    async def list_tasks(self) -> list[HKTask]:
        if self.down:
            raise RuntimeError("Home Keeper is not installed")
        return [
            HKTask(
                t["id"],
                t["name"],
                t["next_due"],
                t["source"],
                t["recurrence_type"],
                t.get("last_completed"),
            )
            for t in self.tasks.values()
        ]

    async def add_task(self, data: dict[str, Any]) -> str:
        self.calls.append("add")
        task_id = f"t{next(self._ids)}"
        self.tasks[task_id] = {
            "id": task_id,
            "name": data["name"],
            "notes": data.get("notes", ""),
            "recurrence_type": data["recurrence_type"],
            "next_due": data.get("due") or "2026-09-20T09:00:00",  # triggered: armed now
            "source": data.get("source") or {},
            "managed_by": data.get("managed_by"),
            "interval": data.get("interval"),
            "enabled": data.get("enabled", True),
            "last_completed": data.get("last_completed"),
        }
        return task_id

    async def update_task(self, task_id: str, data: dict[str, Any]) -> None:
        self.calls.append("update")
        if "due" in data:
            self.tasks[task_id]["next_due"] = data["due"]
        self.tasks[task_id].update({k: v for k, v in data.items() if k != "due"})

    async def delete_task(self, task_id: str) -> None:
        self.calls.append("delete")
        del self.tasks[task_id]

    async def trigger_task(self, task_id: str) -> None:
        self.calls.append("trigger")
        self.tasks[task_id]["next_due"] = "2026-09-20T09:00:00"

    async def complete_task(self, task_id: str, completed_at: str | None = None) -> None:
        self.calls.append("complete")
        task = self.tasks[task_id]
        if task["recurrence_type"] == "floating":
            task["last_completed"] = completed_at or "2026-09-20T09:00:00"
        else:
            task["next_due"] = None

    # -- what a person does in Home Keeper --

    def check_off(self, name: str) -> None:
        self.by_name(name)["next_due"] = None

    def by_name(self, name: str) -> dict[str, Any]:
        return next(t for t in self.tasks.values() if t["name"] == name)

    def open_names(self) -> list[str]:
        return sorted(t["name"] for t in self.tasks.values() if t["next_due"] is not None)


async def setup(h: Harness, stage_ref: int = 3) -> tuple[HKSync, FakeHK]:
    hk = FakeHK()
    sync = HKSync(h.system, hk)
    await h.start("Leafy Greens", stage_ref=stage_ref)
    await sync.reconcile()
    return sync, hk


async def test_open_tasks_become_managed_one_offs_once(h: Harness) -> None:
    sync, hk = await setup(h)
    assert "Move the grow lights" in hk.open_names()
    task = hk.by_name("Move the grow lights")
    assert task["recurrence_type"] == "one-off"
    assert task["managed_by"]["integration"] == "hydro_grow_planner"
    assert task["source"]["grow_planner"]["system_id"] == h.system.id
    before = len(hk.tasks)
    await sync.reconcile()
    await sync.reconcile()
    assert len(hk.tasks) == before  # idempotent
    assert sync.available is True


async def test_checking_off_in_home_keeper_schedules_the_next_one(h: Harness) -> None:
    sync, hk = await setup(h)
    hk.check_off("Move the grow lights")
    await sync.reconcile()
    await sync.reconcile()
    lights = [t for t in hk.tasks.values() if t["name"] == "Move the grow lights"]
    assert len(lights) == 1 and lights[0]["next_due"] is not None  # the next occurrence
    assert lights[0]["next_due"][:10] == (h.system.today + timedelta(days=3)).isoformat()


async def test_deleted_in_home_keeper_is_added_back(h: Harness) -> None:
    sync, hk = await setup(h)
    task_id = hk.by_name("Move the grow lights")["id"]
    del hk.tasks[task_id]
    await sync.reconcile()
    assert "Move the grow lights" in hk.open_names()


async def test_deleting_here_removes_the_home_keeper_task(h: Harness) -> None:
    sync, hk = await setup(h)
    item = next(t for t in h.system.task_items() if t["title"] == "Move the grow lights")
    h.system.delete_task(item["id"])
    await sync.reconcile()
    assert "Move the grow lights" not in hk.open_names()


async def test_stage_change_swaps_the_stage_tasks(h: Harness) -> None:
    sync, hk = await setup(h)  # Vegetative
    assert "Move the grow lights" in hk.open_names()
    await h.system.set_stage(1)  # Sprouting
    await sync.reconcile()
    names = hk.open_names()
    assert "Check water volume" in names
    assert "Check if ready for Seedling" in names
    assert "Move the grow lights" in names  # day-1 task of the new stage
    assert "Check if ready to finish the grow" not in names


async def test_other_tasks_in_home_keeper_are_never_touched(h: Harness) -> None:
    hk = FakeHK()
    await hk.add_task({"name": "Change furnace filter", "recurrence_type": "floating"})
    await hk.add_task(
        {
            "name": "Someone else's",
            "recurrence_type": "one-off",
            "source": {"grow_planner": {"system_id": "another-system", "kind": "task"}},
        }
    )
    sync = HKSync(h.system, hk)
    await h.start("Leafy Greens", stage_ref=3)
    await sync.reconcile()
    await sync.reconcile()
    assert {"Change furnace filter", "Someone else's"} <= set(hk.open_names())


async def test_without_home_keeper_nothing_breaks_and_it_is_reported(h: Harness) -> None:
    hk = FakeHK()
    hk.down = True
    sync = HKSync(h.system, hk)
    await h.start("Leafy Greens", stage_ref=3)
    await sync.reconcile()
    assert sync.available is False
    hk.down = False
    await sync.reconcile()
    assert sync.available is True and hk.open_names()


async def test_task_names_say_the_grow_only_when_there_are_several(h: Harness) -> None:
    from .test_grows import two_zones

    two_zones(h)
    hk = FakeHK()
    sync = HKSync(h.system, hk)
    await h.start("Leafy Greens", name="Layers 1+2", stage_ref=3)
    await sync.reconcile()
    assert not any(n.startswith("Layers 1+2:") for n in hk.open_names())
    await h.start("Herbs", name="Layers 3+4")
    await sync.reconcile()
    # Names are fixed when a task is created, so only the new grow's tasks carry its name.
    assert any(n.startswith("Layers 3+4: ") for n in hk.open_names())


# -- smart (condition) tasks -------------------------------------------------------------


async def test_a_reading_task_appears_when_none_is_recent_and_clears_on_a_reading(
    h: Harness,
) -> None:
    sync, hk = await setup(h)
    await h.system.record_reading(ph=6.0)  # a grow started mid-cycle has none yet
    await sync.reconcile()
    assert "Record a pH and EC reading" not in hk.open_names()
    h.clock.advance(days=3)
    await sync.reconcile()
    assert "Record a pH and EC reading" in hk.open_names()
    assert hk.by_name("Record a pH and EC reading")["recurrence_type"] == "triggered"
    await h.system.record_reading(ph=6.0)
    await sync.reconcile()
    assert "Record a pH and EC reading" not in hk.open_names()
    assert len([t for t in hk.tasks.values() if t["name"] == "Record a pH and EC reading"]) == 1


async def test_done_while_the_condition_holds_stays_quiet_until_it_returns(h: Harness) -> None:
    sync, hk = await setup(h)
    await h.system.record_reading(ph=6.0)
    h.clock.advance(days=3)
    await sync.reconcile()
    hk.check_off("Record a pH and EC reading")
    await sync.reconcile()
    await sync.reconcile()
    assert "Record a pH and EC reading" not in hk.open_names()  # still overdue, but not nagged
    await h.system.record_reading(ph=6.0)
    await sync.reconcile()
    h.clock.advance(days=3)
    await sync.reconcile()
    assert "Record a pH and EC reading" in hk.open_names()  # armed again, same task
    assert len([t for t in hk.tasks.values() if t["name"] == "Record a pH and EC reading"]) == 1


async def test_ec_out_of_range_creates_a_task_that_clears_when_back_in_range(h: Harness) -> None:
    sync, hk = await setup(h)  # Vegetative: EC 1.2-2.0 mS/cm
    await h.system.record_reading(ec=0.4)
    await h.system.evaluate_alerts()
    h.clock.advance(minutes=11)  # alerts only count once they have lasted 10 minutes
    await h.system.evaluate_alerts()
    await sync.reconcile()
    assert "EC is low: add nutrients" in hk.open_names()
    await h.system.record_reading(ec=1.5)
    await h.system.evaluate_alerts()
    h.clock.advance(minutes=11)
    await h.system.evaluate_alerts()
    await sync.reconcile()
    assert "EC is low: add nutrients" not in hk.open_names()


async def test_temperature_out_of_range_makes_no_task(h: Harness) -> None:
    sync, hk = await setup(h)
    h.system.set_state("sensor.t", None)
    names_before = hk.open_names()
    await sync.reconcile()
    assert hk.open_names() == names_before
    assert not any("emperature" in n for n in names_before)


# -- upkeep: native floating tasks -----------------------------------------------------------


def upkeep_task(hk: FakeHK, title: str) -> dict[str, Any]:
    task = hk.by_name(title)
    assert (
        task["recurrence_type"] == "floating" and task["source"]["grow_planner"]["kind"] == "upkeep"
    )
    return task


async def test_upkeep_is_a_floating_task_counted_from_the_system_start(h: Harness) -> None:
    sync, hk = await setup(h)
    task = upkeep_task(hk, "Change the reservoir water")
    assert task["interval"] == 90 and task["enabled"] is True
    assert task["last_completed"] == f"{h.system.system_started}T09:00:00"
    assert task["managed_by"]["integration"] == "hydro_grow_planner"
    before = len(hk.tasks)
    await sync.reconcile()
    assert len(hk.tasks) == before  # idempotent


async def test_no_upkeep_tasks_before_anything_grows(h: Harness) -> None:
    hk = FakeHK()
    await HKSync(h.system, hk).reconcile()
    assert hk.tasks == {}


async def test_upkeep_waits_while_nothing_is_growing_and_resumes(h: Harness) -> None:
    sync, hk = await setup(h)
    gid = h.system.grows[0].id
    await h.system.end_grow(gid)
    await sync.reconcile()
    assert upkeep_task(hk, "Deep-clean the system")["enabled"] is False
    await h.start("Leafy Greens")
    await sync.reconcile()
    assert upkeep_task(hk, "Deep-clean the system")["enabled"] is True
    assert len([t for t in hk.tasks.values() if t["name"] == "Deep-clean the system"]) == 1


async def test_completing_upkeep_in_home_keeper_is_recorded(h: Harness) -> None:
    sync, hk = await setup(h)
    h.clock.advance(days=100)
    done = h.system.today
    task = upkeep_task(hk, "Change the reservoir water")
    task["last_completed"] = f"{done}T08:30:00"  # Home Keeper's own record of it
    await sync.reconcile()
    assert h.system.upkeep_done_on("reservoir_change") == done
    [row] = [m for m in snapshot(h.system)["maintenance"] if m["id"] == "reservoir_change"]
    assert row["next_due"] == (done + timedelta(days=90)).isoformat()


async def test_an_announced_completion_is_picked_up_from_the_event(h: Harness) -> None:
    sync, hk = await setup(h)  # a Home Keeper that does not report last_completed in lists
    h.clock.advance(days=100)
    task = upkeep_task(hk, "Clean the pump and drains")
    sync.note_completion(task["id"], f"{h.system.today}T08:30:00")
    await sync.reconcile()
    assert h.system.upkeep_done_on("pump_clean") == h.system.today


async def test_a_deep_clean_also_completes_what_it_covers(h: Harness) -> None:
    sync, hk = await setup(h)
    h.clock.advance(days=185)
    day = h.system.today
    upkeep_task(hk, "Deep-clean the system")["last_completed"] = f"{day}T10:00:00"
    await sync.reconcile()
    for title in ("Change the reservoir water", "Clean the pump and drains"):
        assert upkeep_task(hk, title)["last_completed"] == f"{day}T09:00:00"
    # ...but not the meters.
    assert h.system.upkeep_done_on("calibrate_meters") is None
    calls = len(hk.calls)
    await sync.reconcile()  # the echo of our own completions does nothing more
    assert hk.calls[calls:] == []


async def test_changing_upkeep_settings_updates_the_tasks(h: Harness) -> None:
    from grow_planner.core.maintenance import default_maintenance

    sync, hk = await setup(h)
    tasks = default_maintenance()
    for task in tasks:
        if task["id"] == "deep_clean":
            task["every"] = 21
        if task["id"] == "pump_clean":
            task["enabled"] = False
    tasks.append({"title": "Replace the air stone", "every": 90, "note": "Soft and clogged."})
    h.system.update_config(maintenance=tasks)
    await sync.reconcile()
    assert upkeep_task(hk, "Deep-clean the system")["interval"] == 21
    assert "Clean the pump and drains" not in {t["name"] for t in hk.tasks.values()}
    assert upkeep_task(hk, "Replace the air stone")["interval"] == 90
    h.system.update_config(maintenance=[])
    await sync.reconcile()
    assert not [t for t in hk.tasks.values() if t["source"]["grow_planner"]["kind"] == "upkeep"]


async def test_upkeep_deleted_in_home_keeper_is_added_back(h: Harness) -> None:
    sync, hk = await setup(h)
    task = upkeep_task(hk, "Calibrate the pH meter")
    del hk.tasks[task["id"]]
    await sync.reconcile()
    assert upkeep_task(hk, "Calibrate the pH meter")["id"] != task["id"]
