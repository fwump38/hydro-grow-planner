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


def leafy_body(api) -> dict:
    """Start/preview arguments for a leafy greens grow driving the system's pump."""
    device = api.system.data["devices"][0]["id"]
    return {"template": "builtin:leafy_greens", "role_map": {"water_pump": device}}


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
    leafy = leafy_body(api)
    body = {**leafy, "stage": "Vegetative", "stage_started": "2026-09-10"}
    preview = await post(api, f"{api.base}/grows/preview", body)
    assert preview["stage_day"] == 11 and preview["grow_started"] == "2026-08-27"
    assert (await (await api.get(api.base)).json())["active"] is False  # preview changes nothing

    started = await post(api, f"{api.base}/grows", {**body, "night_lighting": False})
    grow = started["grows"][0]
    assert started["active"] and grow["stage"]["name"] == "Vegetative"
    assert grow["stage"]["day"] == 11 and grow["grow_day"] == 25
    assert any(t["title"] == "Add nutrients" for t in started["tasks"])
    # The pump runs 15 min every 3 h: eight runs a day.
    pump = started["devices"][0]["profile"]
    assert len(pump) == 8 and pump[0] == [0, 15] and pump[1] == [180, 195]

    response = await api.delete(f"{api.base}/grows/{grow['id']}")
    assert (await response.json())["active"] is False


async def test_stage_actions(api) -> None:
    leafy = leafy_body(api)
    started = await post(api, f"{api.base}/grows", leafy)
    base = f"{api.base}/grows/{started['grows'][0]['id']}"

    async def stage(path: str, body: dict | None = None) -> dict:
        return (await post(api, f"{base}/{path}", body))["grows"][0]["stage"]

    assert (await stage("stage/advance"))["name"] == "Seedling"
    assert (await stage("stage/previous"))["name"] == "Sprouting"
    assert (await stage("stage", {"stage": 3}))["name"] == "Vegetative"
    assert (await stage("stage/restart"))["day"] == 1
    assert (await api.post(f"{base}/stage/bogus")).status == 404
    await stage("stage", {"stage": 1})
    assert (await api.post(f"{base}/stage/previous")).status == 400


async def test_record_reading_and_history(api) -> None:
    leafy = leafy_body(api)
    await post(api, f"{api.base}/grows", {**leafy, "stage": 3})
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
    assert not (await post(api, f"{api.base}/schedule-control", {"enabled": False}))[
        "schedule_enabled"
    ]


async def test_a_grows_plan_can_be_edited_with_field_errors(api) -> None:
    started = await post(api, f"{api.base}/grows", leafy_body(api))
    gid = started["grows"][0]["id"]
    plan = await (await api.get(f"{api.base}/grows/{gid}/plan")).json()
    plan["name"] = "Renamed"
    plan["stages"][0]["days"] = 9
    resp = await api.put(f"{api.base}/grows/{gid}/plan", json=plan)
    assert resp.status == 200 and (await resp.json())["plan"]["stages"][0]["days"] == 9

    plan["stages"][0]["days"] = 0
    plan["ph_min"], plan["ph_max"] = 7, 6
    resp = await api.put(f"{api.base}/grows/{gid}/plan", json=plan)
    assert resp.status == 422
    paths = {e["path"] for e in (await resp.json())["errors"]}
    assert {"stages[0].days", "ph_min"} <= paths
    stored = await (await api.get(f"{api.base}/grows/{gid}/plan")).json()
    assert stored["stages"][0]["days"] == 9  # rejected edits change nothing

    assert (await api.put(f"{api.base}/grows/missing/plan", json=plan)).status == 400


async def test_a_grow_gets_its_plan_from_a_template_with_role_mapping(api) -> None:
    device = api.system.data["devices"][0]["id"]
    started = await post(
        api,
        f"{api.base}/grows",
        {"template": "builtin:lettuce", "role_map": {"water_pump": device}, "name": "My lettuce"},
    )
    gid = started["grows"][0]["id"]
    assert started["grows"][0]["name"] == "My lettuce"
    plan = await (await api.get(f"{api.base}/grows/{gid}/plan")).json()
    assert plan["humidity_min"] == 50 and set(plan["stages"][0]["schedules"]) == {device}
    bad = await api.post(
        f"{api.base}/grows",
        json={"template": "builtin:lettuce", "role_map": {"water_pump": "nope"}},
    )
    assert bad.status == 400
    assert (await api.post(f"{api.base}/grows", json={})).status == 400  # needs a template


async def test_templates_browse_duplicate_edit_delete(api) -> None:
    cards = await (await api.get("/api/templates")).json()
    leafy = next(c for c in cards if c["id"] == "builtin:leafy_greens")
    assert leafy["builtin"] and leafy["ph"] == "5.8–6.5" and leafy["humidity"] == "40–70"
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


async def test_save_a_grow_as_template(api) -> None:
    device = api.system.data["devices"][0]["id"]
    started = await post(api, f"{api.base}/grows", leafy_body(api))
    spec = {"system_id": api.system.id, "grow_id": started["grows"][0]["id"]}
    made = await post(api, "/api/templates", {"from_grow": spec, "name": "Mine"})
    assert made["name"] == "Mine" and set(made["stages"][2]["schedules"]) == {"water_pump"}
    # And it can start a grow again.
    again = await post(
        api,
        f"{api.base}/grows",
        {"template": made["id"], "role_map": {"water_pump": device}, "name": "Again"},
    )
    gid = next(g["id"] for g in again["grows"] if g["name"] == "Again")
    plan = await (await api.get(f"{api.base}/grows/{gid}/plan")).json()
    assert set(plan["stages"][0]["schedules"]) == {device}


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
    preview = await post(
        api,
        f"{api.base}/grows/preview",
        {
            "template": "builtin:leafy_greens",
            "role_map": {"water_pump": device},
            "stage": 3,
            "stage_started": "2026-09-10",
        },
    )
    assert preview["stage"] == "Vegetative" and preview["stage_day"] == 11
    assert api.system.grows == []  # nothing was started
    assert (
        await api.post(f"{api.base}/grows/preview", json={"template": "builtin:nope"})
    ).status == 400


async def test_two_grows_through_the_api(api) -> None:
    leafy = leafy_body(api)
    first = await post(api, f"{api.base}/grows", {**leafy, "name": "Layers 1+2"})
    second = await post(api, f"{api.base}/grows", {**leafy, "name": "Layers 3+4", "stage": 3})
    assert [g["name"] for g in second["grows"]] == ["Layers 1+2", "Layers 3+4"]
    one, two = (g["id"] for g in second["grows"])
    assert one == first["grows"][0]["id"]

    # Stage moves and night lighting address a grow by id.
    advanced = await post(api, f"{api.base}/grows/{one}/stage/advance")
    assert [g["stage"]["name"] for g in advanced["grows"]] == ["Seedling", "Vegetative"]
    patched = await api.patch(f"{api.base}/grows/{two}", json={"night_lighting": True})
    grows = (await patched.json())["grows"]
    assert [g["night_lighting"] for g in grows] == [False, True]
    renamed = await api.patch(f"{api.base}/grows/{two}", json={"name": "Herbs"})
    assert (await renamed.json())["grows"][1]["name"] == "Herbs"
    clash = await api.patch(f"{api.base}/grows/{two}", json={"name": "layers 1+2"})
    assert clash.status == 400

    # A task can be tagged with a grow.
    tagged = await post(api, f"{api.base}/tasks", {"title": "Harvest", "grow": one})
    assert next(t for t in tagged["tasks"] if t["title"] == "Harvest")["grow"] == "Layers 1+2"

    # Replacing a grow keeps its place; ending one leaves the other.
    replaced = await post(api, f"{api.base}/grows", {**leafy, "name": "Salad", "replace": one})
    assert [g["name"] for g in replaced["grows"]] == ["Salad", "Herbs"]
    ended = await (await api.delete(f"{api.base}/grows/{one}")).json()
    assert [g["name"] for g in ended["grows"]] == ["Herbs"] and ended["active"]
    assert (await api.post(f"{api.base}/grows/{one}/stage/advance")).status == 400


async def test_a_template_role_can_map_to_several_devices(api) -> None:
    devices = [d["id"] for d in api.system.data["devices"]]
    started = await post(
        api,
        f"{api.base}/grows",
        {"template": "builtin:leafy_greens", "role_map": {"side_lights": devices[:2]}},
    )
    plan = await (await api.get(f"{api.base}/grows/{started['grows'][0]['id']}/plan")).json()
    schedules = plan["stages"][0]["schedules"]
    assert set(schedules) == set(devices[:2])


async def test_zones_choose_lights_and_share_the_pump(api) -> None:
    zones = [{"name": "Layers 1+2"}, {"name": "Layers 3+4"}]
    devices = [
        {"name": "Center 1+2", "entity_id": "switch.c12", "role": "center_lights", "zone": "z1"},
        {"name": "Side 1+2", "entity_id": "switch.s12", "role": "side_lights", "zone": "z1"},
        {"name": "Center 3+4", "entity_id": "switch.c34", "role": "center_lights", "zone": "z2"},
        {"name": "Pump", "entity_id": "switch.pump", "role": "water_pump"},
    ]
    # Zone ids are generated, so save the zones first, then point the lights at them.
    saved = await (await api.patch(f"{api.base}/config", json={"zones": zones})).json()
    z1, z2 = (z["id"] for z in saved["zones"])
    for d in devices:
        if d.get("zone"):
            d["zone"] = z1 if d["zone"] == "z1" else z2
    snap = await (await api.patch(f"{api.base}/config", json={"devices": devices})).json()
    by_name = {d["name"]: d for d in snap["devices"]}
    assert by_name["Center 3+4"]["zone"] == z2 and by_name["Pump"]["zone"] is None

    bad = await api.post(f"{api.base}/grows", json={"template": "builtin:lettuce", "zones": ["x"]})
    assert bad.status == 400

    # A zone is busy only while a running grow drives its lights.
    snap = await post(
        api, f"{api.base}/grows", {"template": "builtin:lettuce", "zones": [z1], "name": "A"}
    )
    plan = await (await api.get(f"{api.base}/grows/{snap['grows'][0]['id']}/plan")).json()
    used = set(plan["stages"][0]["schedules"])
    assert used == {by_name[n]["id"] for n in ("Center 1+2", "Side 1+2", "Pump")}
    snap = await (await api.get(api.base)).json()
    busy = {z["name"]: z["busy_by"] for z in snap["zones"]}
    assert busy == {"Layers 1+2": ["A"], "Layers 3+4": []}
    await api.delete(f"{api.base}/grows/{snap['grows'][0]['id']}")
    snap = await (await api.get(api.base)).json()
    assert all(z["busy_by"] == [] for z in snap["zones"])


async def test_zone_and_role_validation(api) -> None:
    dup = await api.patch(f"{api.base}/config", json={"zones": [{"name": "A"}, {"name": "a"}]})
    assert dup.status == 400
    role = await api.patch(
        f"{api.base}/config",
        json={"devices": [{"name": "x", "entity_id": "switch.x", "role": "nope"}]},
    )
    assert role.status == 400
    # Removing a zone unzones its lights.
    saved = await (await api.patch(f"{api.base}/config", json={"zones": [{"name": "A"}]})).json()
    zid = saved["zones"][0]["id"]
    light = {"name": "c", "entity_id": "switch.c", "role": "center_lights", "zone": zid}
    await api.patch(f"{api.base}/config", json={"devices": [light]})
    snap = await (await api.patch(f"{api.base}/config", json={"zones": []})).json()
    assert snap["devices"][0]["zone"] is None


def test_legacy_devices_get_a_guessed_role() -> None:
    from grow_planner.core.presets import guess_role

    assert guess_role("switch.x", "Center lights") == "center_lights"
    assert guess_role("switch.x", "Side light") == "side_lights"
    assert guess_role("switch.water_pump", "Pump") == "water_pump"
    assert guess_role("switch.x", "Fan") == ""
