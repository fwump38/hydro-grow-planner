"""Persistence: one JSON state file plus a SQLite log of readings.

The state file is written atomically (temp file, then rename) and, by default, a
couple of seconds after the last change so bursts of changes cost one write.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta
import json
import logging
import os
from pathlib import Path
import sqlite3
from typing import Any

_LOGGER = logging.getLogger(__name__)

STATE_VERSION = 1


def _empty() -> dict[str, Any]:
    return {"version": STATE_VERSION, "systems": {}, "templates": {}, "settings": {}}


class Store:
    """The app's persisted state."""

    def __init__(self, path: Path, save_delay: float = 2.0) -> None:
        """Create a store backed by `path`; `save_delay=0` writes immediately."""
        self.path = path
        self.save_delay = save_delay
        self.data: dict[str, Any] = _empty()
        self._handle: asyncio.TimerHandle | None = None

    def load(self) -> None:
        """Load the file, starting empty when it doesn't exist or is unreadable."""
        try:
            loaded = json.loads(self.path.read_text())
        except FileNotFoundError:
            return
        except (OSError, ValueError):
            # Keep the unreadable file around rather than overwriting it.
            backup = self.path.with_suffix(".corrupt")
            _LOGGER.exception("Could not read %s; moving it to %s", self.path, backup)
            os.replace(self.path, backup)
            return
        self.data = {**_empty(), **loaded}

    @property
    def systems(self) -> dict[str, dict[str, Any]]:
        """Return the grow systems' persisted dicts by id."""
        return self.data["systems"]

    @property
    def templates(self) -> dict[str, dict[str, Any]]:
        """Return the user's custom templates by id."""
        return self.data["templates"]

    @property
    def settings(self) -> dict[str, Any]:
        """Return app-wide settings."""
        return self.data["settings"]

    def save(self) -> None:
        """Request a save (debounced)."""
        if self.save_delay <= 0:
            self.flush()
            return
        if self._handle is not None:
            return
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            self.flush()
            return
        self._handle = loop.call_later(self.save_delay, self.flush)

    def flush(self) -> None:
        """Write the file now."""
        if self._handle is not None:
            self._handle.cancel()
            self._handle = None
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(self.data, indent=1, sort_keys=True))
        os.replace(tmp, self.path)


class ReadingsLog:
    """pH/EC readings, for the panel's charts. EC is stored in mS/cm."""

    def __init__(self, path: Path | str) -> None:
        """Open (and create) the database."""
        if str(path) != ":memory:":
            Path(path).parent.mkdir(parents=True, exist_ok=True)
        self._db = sqlite3.connect(str(path))
        self._db.execute(
            "CREATE TABLE IF NOT EXISTS readings ("
            "system_id TEXT NOT NULL, at TEXT NOT NULL, ph REAL, ec REAL)"
        )
        self._db.execute(
            "CREATE INDEX IF NOT EXISTS readings_by_system ON readings (system_id, at)"
        )
        self._db.commit()

    def add(self, system_id: str, when: datetime, ph: float | None, ec_ms_cm: float | None) -> None:
        """Record a reading."""
        self._db.execute(
            "INSERT INTO readings (system_id, at, ph, ec) VALUES (?, ?, ?, ?)",
            (system_id, when.isoformat(), ph, ec_ms_cm),
        )
        self._db.commit()

    def history(self, system_id: str, since: datetime) -> list[dict[str, Any]]:
        """Return readings newer than `since`, oldest first."""
        rows = self._db.execute(
            "SELECT at, ph, ec FROM readings WHERE system_id = ? AND at >= ? ORDER BY at",
            (system_id, since.isoformat()),
        ).fetchall()
        return [{"at": at, "ph": ph, "ec": ec} for at, ph, ec in rows]

    def recent(self, system_id: str, now: datetime, days: int = 14) -> list[dict[str, Any]]:
        """Return the last `days` days of readings."""
        return self.history(system_id, now - timedelta(days=days))

    def close(self) -> None:
        """Close the database."""
        self._db.close()
