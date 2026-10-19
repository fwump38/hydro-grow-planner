"""Engine scenarios, run against fakes with a controllable clock."""

from __future__ import annotations

from datetime import date, timedelta

import pytest

from grow_planner.core.const import (
    EVENT_BACK_IN_RANGE,
    EVENT_GROW_STARTED,
    EVENT_OUT_OF_RANGE,
    EVENT_READING_OVERDUE,
    EVENT_STAGE_CHANGED,
    EVENT_STAGE_COMPLETE_DUE,
    EVENT_TASK_COMPLETED,
    EVENT_TASK_CREATED,
    EVENT_TASKS_DUE,
)
from grow_planner.engine import GrowError
from grow_planner.ports import EntityState

from .conftest import Harness

TODAY = date(2026, 9, 20)


def titles(h: Harness, include_done: bool = False) -> list[str]:
    return [t["title"] for t in h.system.task_items(include_done)]


def item(h: Harness, title: str) -> dict:
    return next(t for t in h.system.task_items() if t["title"] == title)


# -- grow lifecycle and devices -------------------------------------------------------


async def test_idle_until_started(h: Harness) -> None:
    assert not h.system.is_active
    await h.system.tick()
    assert h.ha.calls == []


async def test_start_grow_switches_devices_to_the_schedule(h: Harness) -> None:
    await h.system.start_grow("Leafy Greens")  # Sprouting at 12:00
    # Sprouting: side lights 06-21 on, center off, pump cycle (off at 12:00).
    assert h.system.actual(h.system.devices[1]) is True
    assert h.system.actual(h.system.devices[0]) is False
    assert h.ha.fired(EVENT_GROW_STARTED)
    assert h.ha.fired(EVENT_STAGE_CHANGED)


async def test_manual_override_lasts_until_the_next_scheduled_change(h: Harness) -> None:
    await h.system.start_grow("Leafy Greens")
    side = h.system.devices[1]
    await h.system.manual_switch(side.id, False)
    h.ha.calls.clear()
    h.clock.advance(minutes=5)
    await h.system.tick()
    assert h.ha.calls == []  # not re-asserted
    h.clock.advance(hours=10)  # 22:05, past the 21:00 off time
    await h.system.tick()
    assert h.system.actual(side) is False
    h.ha.calls.clear()
    await h.system.sync(force=True)
    assert h.ha.calls == []  # already as desired


async def test_forced_sync_reasserts_after_override(h: Harness) -> None:
    await h.system.start_grow("Leafy Greens")
    side = h.system.devices[1]
    await h.system.manual_switch(side.id, False)
    await h.system.sync(force=True)
    assert h.system.actual(side) is True


async def test_schedule_control_off_leaves_devices_alone(h: Harness) -> None:
    await h.system.set_schedule_enabled(False)
    await h.system.start_grow("Leafy Greens")
    assert h.ha.calls == []
    await h.system.set_schedule_enabled(True)
    assert h.ha.calls


async def test_unavailable_device_is_skipped(h: Harness) -> None:
    h.system.set_state("switch.side", EntityState("unavailable"))
    await h.system.start_grow("Leafy Greens")
    assert not any(c[2]["entity_id"] == "switch.side" for c in h.ha.calls)


async def test_night_lighting_shifts_light_windows(h: Harness) -> None:
    await h.system.start_grow("Leafy Greens", night_lighting=True)
    # 12:00 is outside the shifted 18:00-09:00 window.
    assert h.system.actual(h.system.devices[1]) is False


# -- stages -----------------------------------------------------------------------------


async def test_stages_never_advance_on_their_own(h: Harness) -> None:
    await h.system.start_grow("Leafy Greens")
    first = h.system.grow().stage
    for _ in range(40):
        h.clock.advance(days=1)
        await h.system.tick()
    assert h.system.grow().stage == first
    assert len(h.ha.fired(EVENT_STAGE_COMPLETE_DUE)) == 1  # prompted once, not repeatedly


async def test_stage_complete_prompt_names_next_stage(h: Harness) -> None:
    await h.system.start_grow("Leafy Greens")
    h.clock.advance(days=6)  # stage day 7 = planned length
    await h.system.tick()
    (event,) = h.ha.fired(EVENT_STAGE_COMPLETE_DUE)
    assert event["stage"] == "Sprouting"
    assert event["next_stage"] == "Seedling"
    assert "Check if ready for Seedling" in titles(h)


async def test_advance_and_previous_undo_restores_progress(h: Harness) -> None:
    await h.system.start_grow("Leafy Greens")
    check = item(h, "Check water volume")
    await h.system.complete_task(check["id"])
    await h.system.advance_stage()
    assert h.system.grow().stage.name == "Seedling"
    assert "Check water volume" not in titles(h, include_done=True)

    await h.system.previous_stage()
    assert h.system.grow().stage.name == "Sprouting"
    assert item(h, "Check water volume")["done"] is True  # checked-off state restored
    assert h.system.grow().stage_started == TODAY


async def test_last_and_first_stage_limits(h: Harness) -> None:
    await h.system.start_grow("Leafy Greens", stage_ref=3)
    with pytest.raises(GrowError):
        await h.system.advance_stage()
    await h.system.set_stage(1)
    with pytest.raises(GrowError):
        await h.system.previous_stage()


async def test_restart_stage_resets_the_day(h: Harness) -> None:
    await h.system.start_grow("Leafy Greens")
    h.clock.advance(days=3)
    assert h.system.grow().stage_day == 4
    await h.system.restart_stage()
    assert h.system.grow().stage_day == 1


# -- starting mid-cycle -------------------------------------------------------------------


async def test_start_mid_cycle_derives_grow_start_and_day(h: Harness) -> None:
    # Vegetative began 10 days ago; Sprouting + Seedling took 14 days before that.
    await h.system.start_grow(
        "Leafy Greens", stage_ref="Vegetative", stage_started=TODAY - timedelta(days=10)
    )
    assert h.system.grow().stage_day == 11
    assert h.system.grow().grow_day == 25
    assert h.system.grow().grow_started == TODAY - timedelta(days=24)


async def test_start_mid_cycle_recurring_tasks_are_due_today(h: Harness) -> None:
    await h.system.start_grow("Leafy Greens", stage_ref=3, stage_started=TODAY - timedelta(days=10))
    due = {t["title"]: t["due"] for t in h.system.task_items()}
    assert due["Move the grow lights"] == TODAY.isoformat()
    assert due["Add nutrients"] == TODAY.isoformat()
    assert "Vegetative" not in due  # one-off day 1 already passed: skipped by default


async def test_start_mid_cycle_can_include_past_one_offs_as_overdue(h: Harness) -> None:
    await h.system.start_grow(
        "Leafy Greens",
        stage_ref=3,
        stage_started=TODAY - timedelta(days=10),
        include_past_tasks=True,
    )
    assert item(h, "Vegetative")["overdue"] is True


async def test_unknown_plan_or_stage(h: Harness) -> None:
    with pytest.raises(GrowError):
        await h.system.start_grow("Nope")
    with pytest.raises(GrowError):
        await h.system.start_grow("Leafy Greens", stage_ref="Flowering")


# -- recurring tasks ------------------------------------------------------------------------


async def test_recurring_task_reappears_three_days_after_completion(h: Harness) -> None:
    await h.system.start_grow("Leafy Greens", stage_ref=3)
    first = item(h, "Move the grow lights")
    h.clock.advance(days=2)  # complete two days late
    await h.system.complete_task(first["id"])
    nxt = [
        t for t in h.system.task_items(include_done=False) if t["title"] == "Move the grow lights"
    ]
    assert [t["due"] for t in nxt] == [(TODAY + timedelta(days=5)).isoformat()]
    (created,) = h.ha.fired(EVENT_TASK_CREATED)[-1:]
    assert created["due"] == nxt[0]["due"]
    assert h.ha.fired(EVENT_TASK_COMPLETED)[-1]["next_due"] == nxt[0]["due"]


async def test_recurring_task_keeps_going_past_the_planned_stage_length(h: Harness) -> None:
    await h.system.start_grow("Leafy Greens", stage_ref=3)
    for _ in range(40):  # 120 days of completions: well past the 90 day stage
        current = item_open(h, "Add nutrients")
        h.clock.advance(days=3)
        await h.system.complete_task(current["id"])
    assert item_open(h, "Add nutrients")["due"] == (h.system.today + timedelta(days=3)).isoformat()


def item_open(h: Harness, title: str) -> dict:
    return next(t for t in h.system.task_items(include_done=False) if t["title"] == title)


async def test_custom_repeating_task(h: Harness) -> None:
    instance = await h.system.add_custom_task("Clean the reservoir", every=7)
    await h.system.complete_task(instance)
    nxt = item_open(h, "Clean the reservoir")
    assert nxt["due"] == (TODAY + timedelta(days=7)).isoformat()
    assert nxt["every"] == 7 and nxt["custom"]


async def test_custom_tasks_survive_stage_changes_but_plan_tasks_do_not(h: Harness) -> None:
    await h.system.start_grow("Leafy Greens")
    await h.system.add_custom_task("Buy nutrients")
    await h.system.advance_stage()
    assert "Buy nutrients" in titles(h)
    assert "Check water volume" not in titles(h)


async def test_deleting_a_repeating_task_stops_the_repeat(h: Harness) -> None:
    instance = await h.system.add_custom_task("Stir", every=2)
    h.system.delete_task(instance)
    assert "Stir" not in titles(h, include_done=True)
    assert "custom_tasks" in h.system.rt and not h.system.rt["custom_tasks"]


async def test_cannot_reopen_a_repeating_task(h: Harness) -> None:
    instance = await h.system.add_custom_task("Stir", every=2)
    await h.system.complete_task(instance)
    with pytest.raises(GrowError):
        await h.system.reopen_task(instance)


async def test_completing_twice_is_harmless(h: Harness) -> None:
    instance = await h.system.add_custom_task("Once")
    await h.system.complete_task(instance)
    await h.system.complete_task(instance)
    assert len(h.ha.fired(EVENT_TASK_COMPLETED)) == 1


async def test_done_tasks_are_pruned_after_a_week(h: Harness) -> None:
    instance = await h.system.add_custom_task("Once")
    await h.system.complete_task(instance)
    h.clock.advance(days=8)
    await h.system.tick()
    assert "Once" not in titles(h, include_done=True)


# -- reminders and prompts --------------------------------------------------------------------


async def test_daily_reminder_fires_once_after_reminder_time(h: Harness) -> None:
    h.clock.current = h.clock.current.replace(hour=7)
    await h.system.start_grow("Leafy Greens")
    await h.system.tick()
    assert h.ha.fired(EVENT_TASKS_DUE) == []  # 07:00 is before 08:00
    h.clock.advance(hours=2)
    await h.system.tick()
    await h.system.tick()
    (event,) = h.ha.fired(EVENT_TASKS_DUE)
    assert event["count"] == len(event["tasks"]) > 0
    assert {"title", "due", "overdue", "recurring"} <= set(event["tasks"][0])
    h.clock.advance(days=1)
    await h.system.tick()
    assert len(h.ha.fired(EVENT_TASKS_DUE)) == 2


async def test_no_reminder_when_nothing_is_due(h: Harness) -> None:
    await h.system.tick()
    assert h.ha.fired(EVENT_TASKS_DUE) == []


async def test_reading_overdue_fires_once_until_a_reading_is_recorded(h: Harness) -> None:
    await h.system.start_grow("Leafy Greens")
    h.clock.advance(days=3)
    await h.system.tick()
    await h.system.tick()
    assert len(h.ha.fired(EVENT_READING_OVERDUE)) == 1
    await h.system.water_checked()
    assert h.system.reading_overdue is False
    h.clock.advance(days=3)
    await h.system.tick()
    assert len(h.ha.fired(EVENT_READING_OVERDUE)) == 2


# -- readings, units and alerts -------------------------------------------------------------------


async def test_record_reading_logs_exactly_one_row(h: Harness) -> None:
    await h.system.start_grow("Leafy Greens")
    await h.system.record_reading(ph=6.1)
    assert len(h.readings.rows) == 1
    assert h.readings.rows[0][2] == 6.1
    assert h.system.ph == 6.1


async def test_ec_is_entered_in_the_display_unit_and_checked_in_ms_cm(h: Harness) -> None:
    h.system.data["ec_unit"] = "ppm 500"
    await h.system.start_grow("Leafy Greens", stage_ref=3)  # EC range 1.2-2.0 mS/cm
    await h.system.record_reading(ec=700)
    assert h.system.ec == pytest.approx(1.4)
    assert h.system.ec_display == 700
    assert h.system.is_out_of_range("ec") is False
    await h.system.record_reading(ec=500)  # 1.0 mS/cm
    assert h.system.is_out_of_range("ec") is True
    assert h.readings.rows[-1][3] == pytest.approx(1.0)


async def test_reading_validation(h: Harness) -> None:
    for kwargs in ({}, {"ph": 15}, {"ph": -1}, {"ec": -5}):
        with pytest.raises(GrowError):
            await h.system.record_reading(**kwargs)


async def test_ph_alert_is_debounced_and_clears(h: Harness) -> None:
    await h.system.start_grow("Leafy Greens")  # pH 5.8-6.5
    await h.system.record_reading(ph=7.4)
    assert h.ha.fired(EVENT_OUT_OF_RANGE) == []
    h.clock.advance(minutes=11)
    await h.system.tick()
    (event,) = h.ha.fired(EVENT_OUT_OF_RANGE)
    assert event["metric"] == "ph" and event["value"] == 7.4 and event["max"] == 6.5
    await h.system.record_reading(ph=6.0)
    h.clock.advance(minutes=11)
    await h.system.tick()
    assert len(h.ha.fired(EVENT_BACK_IN_RANGE)) == 1


async def test_ec_sensor_unit_is_detected_and_converted(h: Harness) -> None:
    h.system.data["sensors"]["ec"] = "sensor.ec"
    h.system.data["ec_unit"] = "µS/cm"
    h.system.set_state("sensor.ec", EntityState("1500", "µS/cm"))
    assert h.system.ec == pytest.approx(1.5)
    h.system.set_state("sensor.ec", EntityState("750", "ppm"))  # ambiguous: no override
    assert h.system.ec == pytest.approx(750)  # falls back to mS/cm until the user picks
    h.system.data["ec_sensor_unit"] = "ppm 500"
    assert h.system.ec == pytest.approx(1.5)


async def test_climate_ranges_use_the_plan_unit(h: Harness) -> None:
    h.system.data["sensors"]["temperature"] = "sensor.temp"
    await h.system.start_grow("Leafy Greens")  # 65-75 °F
    h.system.set_state("sensor.temp", EntityState("21", "°C"))  # 69.8 °F
    assert h.system.temperature == pytest.approx(69.8)
    assert h.system.is_out_of_range("temperature") is False
    h.system.set_state("sensor.temp", EntityState("30", "°C"))
    assert h.system.is_out_of_range("temperature") is True


# -- plans ---------------------------------------------------------------------------------------


async def test_deleting_the_running_plan_ends_the_grow(h: Harness) -> None:
    await h.system.start_grow("Leafy Greens")
    h.system.delete_plan("leafy")
    assert not h.system.is_active


async def test_removing_the_current_stage_moves_to_the_first(h: Harness) -> None:
    await h.system.start_grow("Leafy Greens", stage_ref=3)
    plan = dict(h.system.data["plans"]["leafy"])
    plan["stages"] = plan["stages"][:2]
    h.system.set_plan("leafy", plan)
    assert h.system.grow().stage.name == "Sprouting"


# -- snapshot -------------------------------------------------------------------------------------


async def test_snapshot_shape(h: Harness) -> None:
    from grow_planner.snapshot import snapshot

    idle = snapshot(h.system)
    assert idle["active"] is False and idle["grows"] == []

    h.system.data["ec_unit"] = "ppm 500"
    await h.system.start_grow("Leafy Greens", stage_ref=3, stage_started=TODAY - timedelta(days=4))
    await h.system.record_reading(ph=6.1, ec=800)
    snap = snapshot(h.system, with_profiles=True)
    [grow] = snap["grows"]
    assert grow["stage"]["name"] == "Vegetative" and grow["stage"]["day"] == 5
    assert grow["stage"]["count"] == 3 and len(grow["stages"]) == 3
    assert snap["metrics"]["ec"]["value"] == 800
    assert snap["metrics"]["ec"]["unit"] == "ppm 500"
    assert snap["metrics"]["ec"]["range"] == "600–1000"  # 1.2-2.0 mS/cm in ppm 500
    assert snap["metrics"]["ec"]["out_of_range"] is False
    assert snap["metrics"]["ph"]["range"] == "5.8–6.5"
    assert snap["metrics"]["humidity"]["range"] == "40–70"
    pump = next(d for d in snap["devices"] if d["id"] == "d_pump")
    assert pump["mode"] == "interval" and pump["schedule"] == "15 min every 3 h"
    assert len(pump["profile"]) == 8 and pump["profile"][:2] == [(0, 15), (180, 195)]
    assert snap["tasks_due"] >= 3


async def test_all_digit_stage_id_is_not_mistaken_for_a_stage_number(h: Harness) -> None:
    plan = h.system.data["plans"]["leafy"]
    plan["stages"][0]["id"] = "73984280"
    h.system.set_plan("leafy", plan)
    await h.system.start_grow("Leafy Greens", stage_ref=3)
    await h.system.set_stage("73984280")
    assert h.system.grow().stage.name == "Sprouting"


async def test_an_idle_tick_signals_no_change(h: Harness) -> None:
    await h.system.start_grow("Leafy Greens", stage_ref=3)
    await h.system.tick()
    changes, saves = h.changes, h.saves
    for _ in range(5):
        await h.system.tick()
    assert (h.changes, h.saves) == (changes, saves)


async def test_preview_start_changes_nothing_and_describes_the_result(h: Harness) -> None:
    started = TODAY - timedelta(days=10)
    preview = h.system.preview_start("Leafy Greens", "Vegetative", started)
    assert not h.system.is_active and h.ha.calls == []
    assert preview["stage"] == "Vegetative" and preview["stage_day"] == 11
    assert preview["grow_started"] == (TODAY - timedelta(days=24)).isoformat()
    assert {t["title"] for t in preview["tasks"]} >= {"Move the grow lights", "Add nutrients"}
    assert all(t["due"] == TODAY.isoformat() for t in preview["tasks"] if t["recurring"])
    assert "Vegetative" in preview["skipped_tasks"]  # the day-1 info task already passed
    pump = next(d for d in preview["devices"] if d["name"] == "Water pump")
    assert pump["desired"] is True  # 12:00 falls inside a run (the pump cycles from midnight)

    with_past = h.system.preview_start("Leafy Greens", 3, started, include_past_tasks=True)
    assert "Vegetative" in {t["title"] for t in with_past["tasks"]}
    assert with_past["skipped_tasks"] == []
