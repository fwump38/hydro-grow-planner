"""Fakes and fixtures for engine tests."""

from __future__ import annotations

import copy
from datetime import datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

import pytest

from grow_planner.core.models import new_id
from grow_planner.core.presets import PRESET_ROLES, build_from_preset
from grow_planner.engine import GrowError, GrowSystem, new_system_data
from grow_planner.ports import EntityState

TZ = ZoneInfo("America/Denver")


class FakeClock:
    """A settable clock."""

    def __init__(self, now: datetime) -> None:
        self.current = now

    def __call__(self) -> datetime:
        return self.current

    def advance(self, **kwargs: float) -> None:
        self.current += timedelta(**kwargs)


class FakeHA:
    """Records calls and mimics switch state changes."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, str, dict[str, Any]]] = []
        self.events: list[tuple[str, dict[str, Any]]] = []
        self.system: GrowSystem | None = None

    async def call_service(self, domain: str, service: str, data: dict[str, Any]) -> None:
        self.calls.append((domain, service, data))
        if self.system is not None and service in ("turn_on", "turn_off"):
            on = service == "turn_on"
            self.system.set_state(data["entity_id"], EntityState("on" if on else "off"))

    async def fire_event(self, event_type: str, data: dict[str, Any]) -> None:
        self.events.append((event_type, data))

    def fired(self, event_type: str) -> list[dict[str, Any]]:
        return [data for name, data in self.events if name == event_type]


class FakeReadings:
    def __init__(self) -> None:
        self.rows: list[tuple] = []

    def add(self, system_id, when, ph, ec_ms_cm) -> None:
        self.rows.append((system_id, when, ph, ec_ms_cm))

    def recent(self, system_id, now, days=14):
        cutoff = (now - timedelta(days=days)).isoformat()
        return [
            {"at": when.isoformat(), "ph": ph, "ec": ec}
            for sid, when, ph, ec in self.rows
            if sid == system_id and when.isoformat() >= cutoff
        ]


class Harness:
    """A GrowSystem wired to fakes."""

    def __init__(self) -> None:
        self.clock = FakeClock(datetime(2026, 9, 20, 12, 0, tzinfo=TZ))
        self.ha = FakeHA()
        self.readings = FakeReadings()
        self.saves = 0
        self.changes = 0
        counter = iter(range(1, 100000))
        data = new_system_data("sys1", "Tower")
        data["devices"] = [
            {
                "id": "d_center",
                "name": "Center lights",
                "entity_id": "switch.center",
                "light": True,
            },
            {"id": "d_side", "name": "Side lights", "entity_id": "switch.side", "light": True},
            {"id": "d_pump", "name": "Water pump", "entity_id": "switch.pump", "light": False},
        ]
        role_map = {
            "center_lights": "d_center",
            "side_lights": "d_side",
            "water_pump": "d_pump",
        }
        assert set(role_map) == set(PRESET_ROLES)
        # Plan data by name; each grow started from one keeps its own copy.
        self.plans: dict[str, dict[str, Any]] = {
            "Leafy Greens": build_from_preset("leafy_greens", role_map, new_id)
        }
        self.system = GrowSystem(
            data,
            self.ha,
            self.clock,
            self.readings,
            on_save=self._saved,
            on_change=self._changed,
            make_id=lambda: f"id{next(counter)}",
        )
        self.ha.system = self.system
        for entity in ("switch.center", "switch.side", "switch.pump"):
            self.system.set_state(entity, EntityState("off"))

    def plan(self, ref: str) -> dict[str, Any]:
        if ref not in self.plans:
            raise GrowError(f"Unknown plan: {ref}")
        return self.plans[ref]

    async def start(self, ref: str, *args: Any, **kwargs: Any) -> str:
        """Start a grow from one of the harness's plans."""
        return await self.system.start_grow(self.plan(ref), *args, **kwargs)

    def preview(self, ref: str, *args: Any, **kwargs: Any) -> dict[str, Any]:
        return self.system.preview_start(self.plan(ref), *args, **kwargs)

    def edit(self, grow: str | None = None, **changes: Any) -> dict[str, Any]:
        """Change a running grow's own plan, as the plan editor does."""
        plan = copy.deepcopy(self.system.grow(grow).data["plan"])
        plan.update(changes)
        self.system.set_grow_plan(grow, plan)
        return plan

    def _saved(self) -> None:
        self.saves += 1

    def _changed(self) -> None:
        self.changes += 1


@pytest.fixture
def h() -> Harness:
    return Harness()
