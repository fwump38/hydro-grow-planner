"""Tests for settings loading."""

from __future__ import annotations

from pathlib import Path

import pytest

from grow_planner.settings import load


def test_in_supervisor(tmp_path: Path) -> None:
    options = tmp_path / "options.json"
    options.write_text('{"log_level": "debug"}')
    s = load({"SUPERVISOR_TOKEN": "tok"}, options)
    assert s.in_supervisor and s.ha_token == "tok"
    assert s.ha_ws_url == "ws://supervisor/core/websocket"
    assert s.log_level == "debug" and s.port == 8099 and s.data_dir == Path("/data")
    assert s.mqtt_host is None  # fetched from the Supervisor at startup


def test_standalone(tmp_path: Path) -> None:
    env = {
        "HA_URL": "https://ha.example.com/",
        "HA_TOKEN": "t",
        "MQTT_HOST": "broker",
        "MQTT_USER": "u",
        "DATA_DIR": str(tmp_path),
        "PORT": "9000",
    }
    s = load(env, tmp_path / "missing.json")
    assert not s.in_supervisor
    assert s.ha_ws_url == "wss://ha.example.com/api/websocket"
    assert (s.mqtt_host, s.mqtt_port, s.mqtt_user, s.port) == ("broker", 1883, "u", 9000)
    assert load({**env, "HA_URL": "http://ha:8123"}, tmp_path / "x").ha_ws_url == (
        "ws://ha:8123/api/websocket"
    )


def test_standalone_needs_credentials(tmp_path: Path) -> None:
    with pytest.raises(SystemExit):
        load({}, tmp_path / "x")


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("broker", ("broker", 1883)),
        ("192.168.1.5:1884", ("192.168.1.5", 1884)),
        ("mqtt://broker.local", ("broker.local", 1883)),
        ("mqtt://broker.local:1885/", ("broker.local", 1885)),
        ("mqtts://broker", ("broker", 1883)),
        ("  broker  ", ("broker", 1883)),
    ],
)
def test_broker_forms(value: str, expected: tuple[str, int], tmp_path: Path) -> None:
    from grow_planner.settings import split_broker

    assert split_broker(value, 1883) == expected
    s = load({"HA_URL": "http://ha", "HA_TOKEN": "t", "MQTT_HOST": value}, tmp_path / "x")
    assert (s.mqtt_host, s.mqtt_port) == expected
    assert s.mqtt_tls is value.startswith("mqtts://")
