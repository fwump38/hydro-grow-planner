"""Runtime settings: inside an app (Supervisor) or standalone for development."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
import json
from pathlib import Path


@dataclass(frozen=True, slots=True)
class Settings:
    """Where things are and how to reach Home Assistant."""

    data_dir: Path
    port: int
    log_level: str
    ha_ws_url: str
    ha_token: str
    # None means "ask the Supervisor" (in an app) or "no MQTT" (standalone).
    mqtt_host: str | None
    mqtt_port: int
    mqtt_user: str | None
    mqtt_password: str | None
    mqtt_tls: bool
    in_supervisor: bool


def _ws_url(http_url: str) -> str:
    base = http_url.rstrip("/")
    scheme = "wss" if base.startswith("https://") else "ws"
    return f"{scheme}://{base.split('://', 1)[-1]}/api/websocket"


def split_broker(value: str, default_port: int) -> tuple[str, int]:
    """Accept `host`, `host:1883`, `mqtt://host:1883` or `mqtts://host` and return (host, port)."""
    text = value.strip()
    if "://" in text:
        text = text.split("://", 1)[1]
    text = text.split("/", 1)[0]
    host, sep, port = text.rpartition(":")
    if sep and port.isdigit() and "]" not in port:
        return host, int(port)
    return text, default_port


def load(env: Mapping[str, str], options_file: Path | None = None) -> Settings:
    """Build settings from the environment (and /data/options.json in an app).

    In an app, SUPERVISOR_TOKEN is set. Standalone, set HA_URL and HA_TOKEN (a
    long-lived access token), and optionally MQTT_HOST/PORT/USER/PASSWORD.
    """
    options: dict[str, str] = {}
    options_file = options_file or Path("/data/options.json")
    if options_file.exists():
        options = json.loads(options_file.read_text())

    supervisor_token = env.get("SUPERVISOR_TOKEN")
    if supervisor_token:
        return Settings(
            data_dir=Path(env.get("DATA_DIR", "/data")),
            port=int(env.get("PORT", "8099")),
            log_level=options.get("log_level", "info"),
            ha_ws_url="ws://supervisor/core/websocket",
            ha_token=supervisor_token,
            mqtt_host=None,
            mqtt_port=1883,
            mqtt_user=None,
            mqtt_password=None,
            mqtt_tls=False,
            in_supervisor=True,
        )

    ha_url, token = env.get("HA_URL"), env.get("HA_TOKEN")
    broker = env.get("MQTT_HOST") or None
    mqtt_host, mqtt_port = (
        split_broker(broker, int(env.get("MQTT_PORT", "1883"))) if broker else (None, 1883)
    )
    if not ha_url or not token:
        raise SystemExit("Set HA_URL and HA_TOKEN (or run inside Home Assistant as an app)")
    return Settings(
        data_dir=Path(env.get("DATA_DIR", "./data")),
        port=int(env.get("PORT", "8099")),
        log_level=env.get("LOG_LEVEL", "info"),
        ha_ws_url=_ws_url(ha_url),
        ha_token=token,
        mqtt_host=mqtt_host,
        mqtt_port=mqtt_port,
        mqtt_user=env.get("MQTT_USER") or None,
        mqtt_password=env.get("MQTT_PASSWORD") or None,
        mqtt_tls=env.get("MQTT_TLS", "").lower() in ("1", "true", "yes")
        or bool(broker and broker.strip().startswith("mqtts://")),
        in_supervisor=False,
    )
