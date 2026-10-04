"""Tests for the REST API, through a real aiohttp test client."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

import pytest

from grow_planner.api import build_web_app
from grow_planner.ports import EntityState

from .test_app import app, configure  # noqa: F401  (fixtures and helper)


@pytest.fixture
async def api(app, aiohttp_client):  # noqa: F811
    system = configure(app)
    app.on_ha_state("switch.pump", EntityState("off", None, "Water pump"))
    app.on_ha_state("sensor.room_temp", EntityState("21", "°C", "Room temp"))
    app.on_ha_state("light.grow", EntityState("off", None, "Grow light"))
    client = await aiohttp_client(build_web_app(app))
    client.system = system
    client.ha = app.ha
    app.ha.system = system  # the fake mirrors switch changes, like HA state events
    client.base = f"/api/systems/{system.id}"
    return client


async def post(api, path: str, body: dict | None = None, status: int = 200) -> dict:
    response = await api.post(path, json=body)
    assert response.status == status, await response.text()
    return await response.json()


async def test_health_and_meta(api) -> None:
    assert (await (await api.get("/health")).json()) == {"status": "ok"}
    meta = await (await api.get("/api/meta")).json()
    assert "ppm 500" in meta["ec_units"] and "center_lights" in meta["roles"]
    assert any(e["event"] == "hydro_grow_planner_tasks_due" for e in meta["events"])


async def test_entities_are_listed_and_filtered(api) -> None:
    rows = await (await api.get("/api/ha/entities?domains=switch,light")).json()
    assert [r["entity_id"] for r in rows] == ["light.grow", "switch.pump"]  # sorted by name
    assert rows[1]["name"] == "Water pump"
    sensors = await (await api.get("/api/ha/entities?domains=sensor")).json()
    assert sensors[0]["unit"] == "°C"


async def test_system_crud(api) -> None:
    created = await post(api, "/api/systems", {"name": "Second"})
    assert created["name"] == "Second" and created["active"] is False
    assert len(await (await api.get("/api/systems")).json()) == 2
    assert (await api.post("/api/systems", json={"name": "second"})).status == 400
    assert (await api.delete(f"/api/systems/{created['id']}")).status == 200
    assert (await api.get(f"/api/systems/{created['id']}")).status == 400


async def test_config_patch_and_validation(api) -> None:
    resp = await api.patch(
        f"{api.base}/config", json={"ec_unit": "ppm 500", "reading_interval_days": 2}
    )
    assert (await resp.json())["ec_unit"] == "ppm 500"
    config = await (await api.get(f"{api.base}/config")).json()
    assert config["reading_interval_days"] == 2
    bad = await api.patch(f"{api.base}/config", json={"ec_unit": "furlongs"})
    assert bad.status == 400 and "EC unit" in (await bad.json())["error"]


async def test_start_wizard_flow_mid_cycle(api) -> None:
    plan_id = next(iter(api.system.data["plans"]))
    body = {"plan": plan_id, "stage": "Vegetative", "stage_started": "2026-09-10"}
    preview = await post(api, f"{api.base}/grow/preview", body)
    assert preview["stage_day"] == 11 and preview["grow_started"] == "2026-08-27"
    assert (await (await api.get(api.base)).json())["active"] is False  # preview changes nothing

    started = await post(api, f"{api.base}/grow/start", {**body, "night_lighting": False})
    assert started["active"] and started["stage"]["name"] == "Vegetative"
    assert started["stage"]["day"] == 11 and started["grow_day"] == 25
    assert any(t["title"] == "Add nutrients" for t in started["tasks"])
    assert started["devices"][0]["profile"] == [[0, 1440]]  # pump is always on in Vegetative

    ended = await post(api, f"{api.base}/grow/end")
    assert ended["active"] is False


async def test_stage_actions(api) -> None:
    plan_id = next(iter(api.system.data["plans"]))
    await post(api, f"{api.base}/grow/start", {"plan": plan_id})
    assert (await post(api, f"{api.base}/stage/advance"))["stage"]["name"] == "Seedling"
    assert (await post(api, f"{api.base}/stage/previous"))["stage"]["name"] == "Sprouting"
    assert (await post(api, f"{api.base}/stage", {"stage": 3}))["stage"]["name"] == "Vegetative"
    assert (await post(api, f"{api.base}/stage/restart"))["stage"]["day"] == 1
    assert (await api.post(f"{api.base}/stage/bogus")).status == 404
    await post(api, f"{api.base}/stage", {"stage": 1})
    assert (await api.post(f"{api.base}/stage/previous")).status == 400


async def test_record_reading_and_history(api) -> None:
    plan_id = next(iter(api.system.data["plans"]))
    await post(api, f"{api.base}/grow/start", {"plan": plan_id, "stage": 3})
    await api.patch(f"{api.base}/config", json={"ec_unit": "ppm 500"})
    snap = await post(api, f"{api.base}/readings", {"ph": "6.1", "ec": 800})
    assert snap["metrics"]["ph"]["value"] == 6.1
    assert snap["metrics"]["ec"]["value"] == 800 and snap["metrics"]["ec"]["out_of_range"] is False
    history = await (await api.get(f"{api.base}/readings?days=7")).json()
    assert history["ec_unit"] == "ppm 500" and len(history["readings"]) == 1
    assert history["readings"][0]["ec"] == 800
    assert (await api.post(f"{api.base}/readings", json={})).status == 400
    assert (await api.post(f"{api.base}/readings", json={"ph": 99})).status == 400
    snap = await post(api, f"{api.base}/water-checked")
    assert snap["reading_overdue"] is False


async def test_tasks_flow(api) -> None:
    snap = await post(api, f"{api.base}/tasks", {"title": "Clean tank", "every": 7})
    task = next(t for t in snap["tasks"] if t["title"] == "Clean tank")
    assert task["every"] == 7 and task["custom"]
    snap = await post(api, f"{api.base}/tasks/{task['id']}/complete")
    open_ = [t for t in snap["tasks"] if t["title"] == "Clean tank" and not t["done"]]
    assert len(open_) == 1
    assert (await api.post(f"{api.base}/tasks/{task['id']}/reopen")).status == 400  # repeating
    assert (await api.delete(f"{api.base}/tasks/{open_[0]['id']}")).status == 200
    assert (await api.post(f"{api.base}/tasks/nope/complete")).status == 400
    assert (await api.post(f"{api.base}/tasks", json={"title": " "})).status == 400


async def test_device_switch_and_toggles(api) -> None:
    device = api.system.data["devices"][0]["id"]
    snap = await post(api, f"{api.base}/devices/{device}/switch", {"on": True})
    assert snap["devices"][0]["state"] is True
    assert (await api.post(f"{api.base}/devices/zzz/switch", json={"on": True})).status == 400
    assert (await post(api, f"{api.base}/night-lighting", {"enabled": True}))["night_lighting"]
    assert not (await post(api, f"{api.base}/schedule-control", {"enabled": False}))[
        "schedule_enabled"
    ]


async def test_plan_editing_with_field_errors(api) -> None:
    plans = await (await api.get(f"{api.base}/plans")).json()
    plan_id, plan = next(iter(plans.items()))
    plan["name"] = "Renamed"
    plan["stages"][0]["days"] = 9
    resp = await api.put(f"{api.base}/plans/{plan_id}", json=plan)
    assert resp.status == 200 and (await resp.json())["plan"]["stages"][0]["days"] == 9

    plan["stages"][0]["days"] = 0
    plan["ph_min"], plan["ph_max"] = 7, 6
    resp = await api.put(f"{api.base}/plans/{plan_id}", json=plan)
    assert resp.status == 422
    paths = {e["path"] for e in (await resp.json())["errors"]}
    assert {"stages[0].days", "ph_min"} <= paths
    stored = (await (await api.get(f"{api.base}/plans")).json())[plan_id]
    assert stored["stages"][0]["days"] == 9  # rejected edits change nothing

    assert (await api.put(f"{api.base}/plans/missing", json=plan)).status == 404


async def test_plan_from_template_with_role_mapping(api) -> None:
    device = api.system.data["devices"][0]["id"]
    made = await post(
        api,
        f"{api.base}/plans",
        {"template": "builtin:lettuce", "role_map": {"water_pump": device}, "name": "My lettuce"},
    )
    plan = made["plan"]
    assert plan["name"] == "My lettuce" and plan["humidity_min"] == 50
    assert set(plan["stages"][0]["schedules"]) == {device}
    bad = await api.post(
        f"{api.base}/plans",
        json={"template": "builtin:lettuce", "role_map": {"water_pump": "nope"}},
    )
    assert bad.status == 400
    blank = await post(api, f"{api.base}/plans", {"name": "Blank"})
    assert len(blank["plan"]["stages"]) == 1
    snap = await (await api.delete(f"{api.base}/plans/{made['plan_id']}")).json()
    assert made["plan_id"] not in api.system.data["plans"] and snap["id"] == api.system.id


async def test_templates_browse_duplicate_edit_delete(api) -> None:
    cards = await (await api.get("/api/templates")).json()
    leafy = next(c for c in cards if c["id"] == "builtin:leafy_greens")
    assert leafy["builtin"] and leafy["ph"] == "5.8–6.5" and leafy["humidity"] == "50–70"
    assert leafy["ec"] == "0–2" and leafy["stage_count"] == 3 and leafy["total_days"] == 104
    detail = await (await api.get("/api/templates/builtin:leafy_greens")).json()
    assert detail["builtin"] and detail["stages"][2]["tasks"][1]["every"] == 3

    copy = await post(api, "/api/templates", {"duplicate": "builtin:leafy_greens"})
    assert copy["name"] == "Leafy Greens (copy)" and copy["id"].startswith("custom:")
    assert all(s["id"] for s in copy["stages"])

    copy["name"] = "My greens"
    copy["stages"][0]["days"] = 5
    resp = await api.put(f"/api/templates/{copy['id']}", json=copy)
    assert resp.status == 200 and (await resp.json())["stages"][0]["days"] == 5
    assert (await api.put("/api/templates/builtin:lettuce", json=copy)).status == 400
    assert (await api.delete("/api/templates/builtin:lettuce")).status == 400

    copy["stages"][0]["schedules"]["ghost_device"] = {"mode": "off"}
    assert (await api.put(f"/api/templates/{copy['id']}", json=copy)).status == 422

    assert (await api.delete(f"/api/templates/{copy['id']}")).status == 200
    assert (await api.get(f"/api/templates/{copy['id']}")).status == 400


async def test_template_import_and_export_round_trip(api) -> None:
    exported = await (await api.get("/api/templates/builtin:spinach")).json()
    exported.pop("id"), exported.pop("builtin")
    imported = await post(api, "/api/templates", {"template": json.loads(json.dumps(exported))})
    assert imported["name"] == "Spinach" and imported["stages"][0]["tasks"]
    broken = await api.post("/api/templates", json={"template": {"name": "", "stages": []}})
    assert broken.status == 422


async def test_save_plan_as_template(api) -> None:
    plan_id = next(iter(api.system.data["plans"]))
    device = api.system.data["devices"][0]["id"]
    spec = {"system_id": api.system.id, "plan_id": plan_id, "device_roles": {device: "water_pump"}}
    made = await post(api, "/api/templates", {"from_plan": spec, "name": "Mine"})
    assert made["name"] == "Mine" and set(made["stages"][2]["schedules"]) == {"water_pump"}
    # And it can be used for a new plan again.
    again = await post(
        api,
        f"{api.base}/plans",
        {"template": made["id"], "role_map": {"water_pump": device}},
    )
    assert set(again["plan"]["stages"][0]["schedules"]) == {device}


async def test_event_test_button_fires_a_marked_sample(api) -> None:
    await post(api, "/api/events/test", {"event": "hydro_grow_planner_tasks_due"})
    (event,) = api.ha.events
    assert event[0] == "hydro_grow_planner_tasks_due"
    assert event[1]["test"] is True and event[1]["tasks"]
    assert (await api.post("/api/events/test", json={"event": "nope"})).status == 400


async def test_stream_delivers_changes(api) -> None:
    response = await api.get("/api/stream")
    assert (await response.content.readline()).startswith(b": connected")
    await post(api, f"{api.base}/tasks", {"title": "Ping"})
    line = b""
    while not line.startswith(b"data:"):
        line = await asyncio.wait_for(response.content.readline(), 5)
    assert json.loads(line[5:])["type"] == "changed"
    response.close()


async def test_peer_restriction_exempts_only_health(app, aiohttp_client) -> None:  # noqa: F811
    client = await aiohttp_client(build_web_app(app, allowed_peers=frozenset({"172.30.32.2"})))
    assert (await client.get("/health")).status == 200
    assert (await client.get("/api/systems")).status == 403


async def test_serves_the_built_panel(app, aiohttp_client, tmp_path: Path) -> None:  # noqa: F811
    (tmp_path / "index.html").write_text("<html>panel</html>")
    (tmp_path / "app.js").write_text("console.log(1)")
    client = await aiohttp_client(build_web_app(app, tmp_path))
    assert "panel" in await (await client.get("/")).text()
    assert (await client.get("/app.js")).status == 200
    assert (await client.get("/api/systems")).status == 200  # API still wins


async def test_preview_a_template_before_any_plan_exists(api) -> None:
    device = api.system.data["devices"][0]["id"]
    before = dict(api.system.data["plans"])
    preview = await post(
        api,
        f"{api.base}/grow/preview",
        {
            "template": "builtin:leafy_greens",
            "role_map": {"water_pump": device},
            "stage": 3,
            "stage_started": "2026-09-10",
        },
    )
    assert preview["stage"] == "Vegetative" and preview["stage_day"] == 11
    assert api.system.data["plans"] == before  # nothing was created
    assert (
        await api.post(f"{api.base}/grow/preview", json={"template": "builtin:nope"})
    ).status == 400
