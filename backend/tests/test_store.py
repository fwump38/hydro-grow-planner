"""Tests for persistence."""

from __future__ import annotations

from datetime import datetime, timedelta
import json
from pathlib import Path
from zoneinfo import ZoneInfo

from grow_planner.store import ReadingsLog, Store

TZ = ZoneInfo("America/Denver")


def test_round_trip_and_atomic_write(tmp_path: Path) -> None:
    path = tmp_path / "state.json"
    store = Store(path, save_delay=0)
    store.load()
    store.systems["a"] = {"id": "a"}
    store.save()
    assert not path.with_suffix(".tmp").exists()

    again = Store(path)
    again.load()
    assert again.systems == {"a": {"id": "a"}}
    assert again.templates == {} and again.settings == {}


def test_missing_file_starts_empty(tmp_path: Path) -> None:
    store = Store(tmp_path / "nope.json")
    store.load()
    assert store.systems == {}


def test_corrupt_file_is_kept_not_overwritten(tmp_path: Path) -> None:
    path = tmp_path / "state.json"
    path.write_text("{not json")
    store = Store(path, save_delay=0)
    store.load()
    assert store.systems == {}
    assert path.with_suffix(".corrupt").read_text() == "{not json"
    store.save()
    assert json.loads(path.read_text())["systems"] == {}


async def test_saves_are_debounced(tmp_path: Path) -> None:
    import asyncio

    path = tmp_path / "state.json"
    store = Store(path, save_delay=0.05)
    store.save()
    store.save()
    assert not path.exists()
    await asyncio.sleep(0.1)
    assert path.exists()


def test_readings_history(tmp_path: Path) -> None:
    log = ReadingsLog(tmp_path / "readings.sqlite")
    now = datetime(2026, 9, 20, 12, tzinfo=TZ)
    log.add("s", now - timedelta(days=20), 6.0, 1.0)
    log.add("s", now - timedelta(days=2), 6.1, None)
    log.add("s", now, None, 1.4)
    log.add("other", now, 7.0, 2.0)
    rows = log.recent("s", now, days=14)
    assert [(r["ph"], r["ec"]) for r in rows] == [(6.1, None), (None, 1.4)]
    log.close()
