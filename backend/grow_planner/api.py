"""REST + live-update API for the panel, and static file serving.

Everything is relative to wherever the panel is mounted (Home Assistant ingress
serves it under a long token path), so the frontend uses relative URLs.
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from datetime import date
import json
import logging
from pathlib import Path
from typing import Any

from aiohttp import web

from .app import App
from .core import units
from .core.const import EC_UNITS, HARVEST_STYLES, SCHEDULE_MODES, STAGE_TYPES, TASK_TYPES
from .core.events_doc import EVENTS, example_payload
from .core.models import new_id
from .core.presets import PRESET_ROLES, build_from_template, plan_to_template
from .core.validate import normalize_plan
from .engine import GrowError, GrowSystem
from .snapshot import snapshot
from .templates import custom_key, get_template, list_templates

_LOGGER = logging.getLogger(__name__)

Handler = Callable[[web.Request], Awaitable[web.StreamResponse]]
APP_KEY = web.AppKey("grow_app", App)
KEEPALIVE_SECONDS = 25
# The Supervisor's ingress gateway; only it may reach the panel inside an app.
INGRESS_PEER = "172.30.32.2"


def _json(data: Any, status: int = 200) -> web.Response:
    return web.json_response(data, status=status, dumps=lambda o: json.dumps(o, default=str))


async def _body(request: web.Request) -> dict[str, Any]:
    if not request.can_read_body:
        return {}
    try:
        data = await request.json()
    except ValueError:
        raise GrowError("The request body isn't valid JSON") from None
    if not isinstance(data, dict):
        raise GrowError("The request body must be an object")
    return data


def _date(value: Any) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(str(value)[:10])
    except ValueError:
        raise GrowError(f"Not a date: {value}") from None


@web.middleware
async def errors(request: web.Request, handler: Handler) -> web.StreamResponse:
    """Turn GrowError into a 400 with a message the UI can show."""
    try:
        return await handler(request)
    except GrowError as err:
        return _json({"error": str(err)}, 400)
    except (ValueError, TypeError, KeyError) as err:
        _LOGGER.debug("Bad request", exc_info=True)
        return _json({"error": f"Invalid request: {err}"}, 400)


def peer_check(allowed: frozenset[str]) -> web.middleware:
    """Only accept connections from `allowed` (the health check is exempt)."""

    @web.middleware
    async def middleware(request: web.Request, handler: Handler) -> web.StreamResponse:
        if allowed and request.path != "/health" and request.remote not in allowed:
            return _json({"error": "Forbidden"}, 403)
        return await handler(request)

    return middleware


def _system(request: web.Request) -> GrowSystem:
    return request.app[APP_KEY].get(request.match_info["sid"])


def _view(system: GrowSystem) -> web.Response:
    return _json(snapshot(system, with_profiles=True))


def routes(app: App) -> web.RouteTableDef:  # noqa: C901 - one flat list of small handlers
    """Return the API routes."""
    r = web.RouteTableDef()

    # -- meta ---------------------------------------------------------------------------------

    @r.get("/api/meta")
    async def meta(_: web.Request) -> web.Response:
        return _json(
            {
                "ec_units": EC_UNITS,
                "harvest_styles": HARVEST_STYLES,
                "stage_types": STAGE_TYPES,
                "task_types": TASK_TYPES,
                "schedule_modes": SCHEDULE_MODES,
                "roles": PRESET_ROLES,
                "events": EVENTS,
                "mqtt": app.mqtt is not None,
            }
        )

    @r.get("/api/ha/entities")
    async def entities(request: web.Request) -> web.Response:
        domains = {d for d in request.query.get("domains", "").split(",") if d}
        rows = [
            {"entity_id": eid, "name": st.name or eid, "state": st.state, "unit": st.unit}
            for eid, st in app.all_states.items()
            if not domains or eid.split(".", 1)[0] in domains
        ]
        return _json(sorted(rows, key=lambda row: row["name"].casefold()))

    @r.get("/api/stream")
    async def stream(request: web.Request) -> web.StreamResponse:
        response = web.StreamResponse(
            headers={"Content-Type": "text/event-stream", "Cache-Control": "no-cache"}
        )
        await response.prepare(request)
        queue = app.subscribe()
        try:
            await response.write(b": connected\n\n")
            while True:
                try:
                    message = await asyncio.wait_for(queue.get(), KEEPALIVE_SECONDS)
                    await response.write(f"data: {json.dumps(message)}\n\n".encode())
                except TimeoutError:
                    await response.write(b": keepalive\n\n")
        except (ConnectionResetError, asyncio.CancelledError):
            pass
        finally:
            app.unsubscribe(queue)
        return response

    @r.post("/api/events/test")
    async def test_event(request: web.Request) -> web.Response:
        name = (await _body(request)).get("event", "")
        payload = example_payload(name)
        if payload is None:
            raise GrowError("Unknown event")
        await app.ha.fire_event(name, payload)
        return _json({"fired": name})

    # -- systems ---------------------------------------------------------------------------------

    @r.get("/api/systems")
    async def list_systems(_: web.Request) -> web.Response:
        return _json(
            [{"id": s.id, "name": s.name, "active": s.is_active} for s in app.systems.values()]
        )

    @r.post("/api/systems")
    async def create_system(request: web.Request) -> web.Response:
        system = app.create_system(str((await _body(request)).get("name", "")))
        return _view(system)

    @r.get("/api/systems/{sid}")
    async def get_system(request: web.Request) -> web.Response:
        return _view(_system(request))

    @r.delete("/api/systems/{sid}")
    async def delete_system(request: web.Request) -> web.Response:
        app.delete_system(request.match_info["sid"])
        return _json({"deleted": True})

    @r.get("/api/systems/{sid}/config")
    async def get_config(request: web.Request) -> web.Response:
        d = _system(request).data
        keys = (
            "name",
            "devices",
            "sensors",
            "ec_unit",
            "ec_sensor_unit",
            "reading_interval_days",
            "reminder_time",
            "todo_entity",
            "todo_adopt",
            "maintenance",
        )
        return _json({k: d[k] for k in keys})

    @r.patch("/api/systems/{sid}/config")
    async def patch_config(request: web.Request) -> web.Response:
        system = _system(request)
        system.update_config(**await _body(request))
        return _view(system)

    # -- commands ----------------------------------------------------------------------------------

    @r.post("/api/systems/{sid}/devices/{did}/switch")
    async def switch_device(request: web.Request) -> web.Response:
        system = _system(request)
        await system.manual_switch(request.match_info["did"], bool((await _body(request))["on"]))
        return _view(system)

    @r.post("/api/systems/{sid}/schedule-control")
    async def schedule_control(request: web.Request) -> web.Response:
        system = _system(request)
        await system.set_schedule_enabled(bool((await _body(request))["enabled"]))
        return _view(system)

    @r.post("/api/systems/{sid}/sync")
    async def sync(request: web.Request) -> web.Response:
        system = _system(request)
        await system.sync(force=True)
        return _view(system)

    @r.post("/api/systems/{sid}/readings")
    async def record(request: web.Request) -> web.Response:
        system = _system(request)
        body = await _body(request)
        ph = float(body["ph"]) if body.get("ph") not in (None, "") else None
        ec = float(body["ec"]) if body.get("ec") not in (None, "") else None
        await system.record_reading(ph=ph, ec=ec)
        return _view(system)

    @r.post("/api/systems/{sid}/water-checked")
    async def water_checked(request: web.Request) -> web.Response:
        system = _system(request)
        await system.water_checked()
        return _view(system)

    @r.get("/api/systems/{sid}/readings")
    async def readings(request: web.Request) -> web.Response:
        system = _system(request)
        days = min(max(int(request.query.get("days", "14")), 1), 365)
        unit = system.ec_unit
        rows = [
            {
                "at": row["at"],
                "ph": row["ph"],
                "ec": units.from_canonical(row["ec"], unit) if row["ec"] is not None else None,
            }
            for row in app.readings.recent(system.id, system.now, days)
        ]
        return _json({"ec_unit": unit, "readings": rows})

    def role_map_of(body: dict[str, Any]) -> dict[str, list[str]]:
        """Read {role: device id | [device ids]} from a request, dropping empty roles."""
        roles: dict[str, list[str]] = {}
        for role, value in (body.get("role_map") or {}).items():
            ids = [value] if isinstance(value, str) else list(value or [])
            if ids := [i for i in ids if i]:
                roles[role] = ids
        return roles

    def device_keys(system: GrowSystem) -> set[str]:
        return {d["id"] for d in system.data["devices"]}

    # -- grow lifecycle ----------------------------------------------------------------------------

    def start_args(body: dict[str, Any]) -> dict[str, Any]:
        return {
            "stage_ref": body.get("stage") or None,
            "stage_started": _date(body.get("stage_started")),
            "include_past_tasks": bool(body.get("include_past_tasks", False)),
        }

    @r.post("/api/systems/{sid}/grows/preview")
    async def preview(request: web.Request) -> web.Response:
        system = _system(request)
        body = await _body(request)
        args = {
            **start_args(body),
            "replace": body.get("replace") or None,
            "night_lighting": body.get("night_lighting"),
            "keep_start": bool(body.get("keep_grow_start")),
        }
        if body.get("template"):
            # Preview a template before a plan exists for it.
            template = get_template(app.store, body["template"])
            data = build_from_template(template, role_map_of(body), new_id)
            plan, problems = normalize_plan(data, new_id, device_keys(system))
            if problems:
                return _json({"errors": problems}, 422)
            return _json(system.preview_start(plan_data=plan, **args))
        return _json(system.preview_start(plan_ref=body["plan"], **args))

    @r.post("/api/systems/{sid}/grows")
    async def start(request: web.Request) -> web.Response:
        system = _system(request)
        body = await _body(request)
        await system.start_grow(
            plan_ref=body["plan"],
            **start_args(body),
            grow_started=_date(body.get("grow_started")),
            night_lighting=body.get("night_lighting"),
            name=body.get("name") or None,
            replace=body.get("replace") or None,
            keep_start=bool(body.get("keep_grow_start")),
        )
        return _view(system)

    @r.patch("/api/systems/{sid}/grows/{gid}")
    async def update_grow(request: web.Request) -> web.Response:
        system = _system(request)
        gid = request.match_info["gid"]
        body = await _body(request)
        if "name" in body:
            await system.rename_grow(str(body["name"]), gid)
        if "night_lighting" in body:
            await system.set_night_lighting(bool(body["night_lighting"]), gid)
        return _view(system)

    @r.delete("/api/systems/{sid}/grows/{gid}")
    async def end(request: web.Request) -> web.Response:
        system = _system(request)
        await system.end_grow(request.match_info["gid"])
        return _view(system)

    @r.post("/api/systems/{sid}/grows/{gid}/stage")
    async def set_stage(request: web.Request) -> web.Response:
        system = _system(request)
        body = await _body(request)
        await system.set_stage(
            body["stage"],
            started=_date(body.get("started")),
            include_past_tasks=bool(body.get("include_past_tasks", False)),
            grow=request.match_info["gid"],
        )
        return _view(system)

    @r.post("/api/systems/{sid}/grows/{gid}/stage/{action}")
    async def stage_action(request: web.Request) -> web.Response:
        system = _system(request)
        action = {
            "advance": system.advance_stage,
            "previous": system.previous_stage,
            "restart": system.restart_stage,
        }.get(request.match_info["action"])
        if action is None:
            raise web.HTTPNotFound
        await action(request.match_info["gid"])
        return _view(system)

    # -- tasks -------------------------------------------------------------------------------------

    @r.post("/api/systems/{sid}/tasks")
    async def add_task(request: web.Request) -> web.Response:
        system = _system(request)
        body = await _body(request)
        await system.add_custom_task(
            str(body.get("title", "")),
            _date(body.get("due")),
            str(body.get("note", "")),
            int(body.get("every") or 0),
            grow=body.get("grow") or None,
        )
        return _view(system)

    @r.post("/api/systems/{sid}/tasks/{tid}/complete")
    async def complete(request: web.Request) -> web.Response:
        system = _system(request)
        await system.complete_task(request.match_info["tid"])
        return _view(system)

    @r.post("/api/systems/{sid}/tasks/{tid}/reopen")
    async def reopen(request: web.Request) -> web.Response:
        system = _system(request)
        await system.reopen_task(request.match_info["tid"])
        return _view(system)

    @r.delete("/api/systems/{sid}/tasks/{tid}")
    async def delete_task(request: web.Request) -> web.Response:
        system = _system(request)
        system.delete_task(request.match_info["tid"])
        return _view(system)

    # -- plans -------------------------------------------------------------------------------------

    @r.get("/api/systems/{sid}/plans")
    async def get_plans(request: web.Request) -> web.Response:
        return _json(_system(request).data["plans"])

    @r.post("/api/systems/{sid}/plans")
    async def create_plan(request: web.Request) -> web.Response:
        system = _system(request)
        body = await _body(request)
        if body.get("template"):
            template = get_template(app.store, body["template"])
            role_map = role_map_of(body)
            unknown = {d for ids in role_map.values() for d in ids} - device_keys(system)
            if unknown:
                raise GrowError("Unknown device in the role mapping")
            data = build_from_template(template, role_map, new_id, body.get("name") or None)
        else:
            data = {
                "name": body.get("name") or "New plan",
                "stages": [
                    {
                        "name": "Stage 1",
                        "stage_type": "other",
                        "days": 7,
                        "schedules": {},
                        "tasks": [],
                    }
                ],
            }
        plan, problems = normalize_plan(data, new_id, device_keys(system))
        if problems:
            return _json({"errors": problems}, 422)
        plan_id = new_id()
        system.set_plan(plan_id, plan)
        return _json({"plan_id": plan_id, "plan": plan})

    @r.put("/api/systems/{sid}/plans/{pid}")
    async def put_plan(request: web.Request) -> web.Response:
        system = _system(request)
        plan_id = request.match_info["pid"]
        if plan_id not in system.data["plans"]:
            raise web.HTTPNotFound
        plan, problems = normalize_plan(await _body(request), new_id, device_keys(system))
        if problems:
            return _json({"errors": problems}, 422)
        system.set_plan(plan_id, plan)
        return _json({"plan": plan})

    @r.delete("/api/systems/{sid}/plans/{pid}")
    async def delete_plan(request: web.Request) -> web.Response:
        system = _system(request)
        system.delete_plan(request.match_info["pid"])
        return _view(system)

    # -- templates ---------------------------------------------------------------------------------

    @r.get("/api/templates")
    async def templates(_: web.Request) -> web.Response:
        return _json(list_templates(app.store))

    @r.get("/api/templates/{tid}")
    async def template(request: web.Request) -> web.Response:
        tid = request.match_info["tid"]
        return _json(
            {"id": tid, "builtin": tid.startswith("builtin:"), **get_template(app.store, tid)}
        )

    def clean_template(data: dict[str, Any]) -> dict[str, Any]:
        clean, problems = normalize_plan(data, new_id, set(PRESET_ROLES))
        if problems:
            raise TemplateInvalid(problems)
        return clean

    class TemplateInvalid(Exception):
        def __init__(self, problems: list[dict[str, str]]) -> None:
            self.problems = problems

    @r.post("/api/templates")
    async def create_template(request: web.Request) -> web.Response:
        body = await _body(request)
        try:
            if body.get("duplicate"):
                source = get_template(app.store, body["duplicate"])
                data = {**json.loads(json.dumps(source)), "name": f"{source['name']} (copy)"}
                if body.get("name"):
                    data["name"] = body["name"]
            elif body.get("from_plan"):
                spec = body["from_plan"]
                system = app.get(spec["system_id"])
                plan = system.data["plans"].get(spec["plan_id"])
                if plan is None:
                    raise GrowError("Unknown plan")
                roles = {
                    dev: role for dev, role in (spec.get("device_roles") or {}).items() if role
                }
                data = plan_to_template(plan, roles)
                if body.get("name"):
                    data["name"] = body["name"]
            else:
                data = body.get("template") or {}  # an import
            clean = clean_template(data)
        except TemplateInvalid as err:
            return _json({"errors": err.problems}, 422)
        key = new_id()
        app.store.templates[key] = clean
        app.store.save()
        return _json({"id": f"custom:{key}", **clean})

    @r.put("/api/templates/{tid}")
    async def put_template(request: web.Request) -> web.Response:
        key = custom_key(request.match_info["tid"])
        if key not in app.store.templates:
            raise web.HTTPNotFound
        try:
            clean = clean_template(await _body(request))
        except TemplateInvalid as err:
            return _json({"errors": err.problems}, 422)
        app.store.templates[key] = clean
        app.store.save()
        return _json({"id": request.match_info["tid"], **clean})

    @r.delete("/api/templates/{tid}")
    async def delete_template(request: web.Request) -> web.Response:
        key = custom_key(request.match_info["tid"])
        if app.store.templates.pop(key, None) is None:
            raise web.HTTPNotFound
        app.store.save()
        return _json({"deleted": True})

    return r


def build_web_app(
    app: App, static_dir: Path | None = None, allowed_peers: frozenset[str] = frozenset()
) -> web.Application:
    """Create the aiohttp application: /health, /api/* and the built panel."""
    web_app = web.Application(middlewares=[peer_check(allowed_peers), errors])
    web_app[APP_KEY] = app

    async def health(_: web.Request) -> web.Response:
        return _json({"status": "ok"})

    web_app.router.add_get("/health", health)
    web_app.add_routes(routes(app))

    if static_dir is not None and static_dir.is_dir():
        index = static_dir / "index.html"

        async def serve_index(_: web.Request) -> web.FileResponse:
            return web.FileResponse(index, headers={"Cache-Control": "no-cache"})

        web_app.router.add_get("/", serve_index)
        web_app.router.add_static("/", static_dir)
    return web_app
