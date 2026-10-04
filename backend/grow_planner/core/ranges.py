"""Debounced range alerts and small value helpers. Pure logic, no I/O."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from .models import out_of_range

DEFAULT_DEBOUNCE = timedelta(minutes=10)

EVENT_OUT = "out_of_range"
EVENT_BACK = "back_in_range"


def convert_temperature(value: float, source: str | None, target: str) -> float:
    """Convert between °C and °F; unknown source units are left alone."""
    if source == target or source not in ("°C", "°F") or target not in ("°C", "°F"):
        return value
    return value * 9 / 5 + 32 if source == "°C" else (value - 32) * 5 / 9


class RangeAlert:
    """Turns a stream of readings into debounced out/back-in-range transitions.

    A change of status only counts once it has lasted `debounce`, so a reading that
    flaps around a limit does not produce a burst of events. `state` is a plain dict
    so it can be persisted: `{"notified": bool, "candidate": "out"|"in"|None,
    "since": iso}`. `notified` is True after an out-of-range event was emitted and
    until the matching back-in-range event.
    """

    def __init__(self, state: dict[str, Any], debounce: timedelta = DEFAULT_DEBOUNCE) -> None:
        """Wrap a (mutable, persisted) state dict."""
        self.state = state
        self.debounce = debounce
        state.setdefault("notified", False)
        state.setdefault("candidate", None)
        state.setdefault("since", None)

    def reset(self) -> None:
        """Forget everything (e.g. when the grow ends)."""
        self.state.update(notified=False, candidate=None, since=None)

    def update(
        self, now: datetime, value: float | None, low: float | None, high: float | None
    ) -> str | None:
        """Feed a reading; return EVENT_OUT, EVENT_BACK or None."""
        outside = out_of_range(value, low, high)
        if outside is None:
            # No reading or no range: nothing to judge, and nothing pending.
            self.state.update(candidate=None, since=None)
            return None

        wanted = "out" if outside else "in"
        settled = "out" if self.state["notified"] else "in"
        if wanted == settled:
            self.state.update(candidate=None, since=None)
            return None

        if self.state["candidate"] != wanted:
            self.state.update(candidate=wanted, since=now.isoformat())
            return None

        since = datetime.fromisoformat(self.state["since"])
        if now - since < self.debounce:
            return None

        self.state.update(notified=wanted == "out", candidate=None, since=None)
        return EVENT_OUT if wanted == "out" else EVENT_BACK
