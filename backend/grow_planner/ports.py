"""Interfaces the engine needs from the outside world.

The real implementations live in ha_ws.py and store.py; tests use fakes.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Protocol


@dataclass(frozen=True, slots=True)
class EntityState:
    """A Home Assistant entity state, reduced to what the engine uses."""

    state: str
    unit: str | None = None
    name: str | None = None


class HAPort(Protocol):
    """Home Assistant access."""

    async def call_service(self, domain: str, service: str, data: dict[str, Any]) -> None:
        """Call a service."""

    async def fire_event(self, event_type: str, data: dict[str, Any]) -> None:
        """Fire an event on the HA bus."""


class ReadingsPort(Protocol):
    """Where manual and sensor readings are recorded for the panel's charts."""

    def add(self, system_id: str, when: datetime, ph: float | None, ec_ms_cm: float | None) -> None:
        """Record a reading (EC in mS/cm)."""

    def recent(self, system_id: str, now: datetime, days: int = 14) -> list[dict[str, Any]]:
        """Return the last `days` days of readings, oldest first."""


Clock = Callable[[], datetime]
"""Returns the current time as an aware, local datetime."""
