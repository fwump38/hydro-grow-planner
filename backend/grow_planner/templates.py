"""Built-in and custom grow templates."""

from __future__ import annotations

from typing import Any

from .core.models import format_range
from .core.presets import PRESETS
from .engine import GrowError
from .store import Store

BUILTIN = "builtin:"
CUSTOM = "custom:"


def summarize(template_id: str, template: dict[str, Any]) -> dict[str, Any]:
    """Return the card data for a template (EC in mS/cm)."""
    stages = template["stages"]
    ec_mins = [s["ec_min"] for s in stages if s.get("ec_min") is not None]
    ec_maxs = [s["ec_max"] for s in stages if s.get("ec_max") is not None]
    unit = template.get("temp_unit")
    return {
        "id": template_id,
        "name": template["name"],
        "builtin": template_id.startswith(BUILTIN),
        "stage_count": len(stages),
        "total_days": sum(s["days"] for s in stages),
        "stages": [{"name": s["name"], "days": s["days"], "type": s["stage_type"]} for s in stages],
        "ph": format_range(template.get("ph_min"), template.get("ph_max")),
        "temperature": format_range(template.get("temp_min"), template.get("temp_max")),
        "temp_unit": unit,
        "humidity": format_range(template.get("humidity_min"), template.get("humidity_max")),
        "harvest_style": template.get("harvest_style", "once"),
        "ec": format_range(min(ec_mins, default=None), max(ec_maxs, default=None)),
    }


def list_templates(store: Store) -> list[dict[str, Any]]:
    """Return every template's card data: built-ins first, then the user's."""
    cards = [summarize(f"{BUILTIN}{key}", tpl) for key, tpl in sorted(PRESETS.items())]
    cards += [summarize(f"{CUSTOM}{key}", tpl) for key, tpl in store.templates.items()]
    return cards


def get_template(store: Store, template_id: str) -> dict[str, Any]:
    """Return a template's full data (built-in ones must not be modified)."""
    if template_id.startswith(BUILTIN) and template_id[len(BUILTIN) :] in PRESETS:
        return PRESETS[template_id[len(BUILTIN) :]]
    if template_id.startswith(CUSTOM) and template_id[len(CUSTOM) :] in store.templates:
        return store.templates[template_id[len(CUSTOM) :]]
    raise GrowError("Unknown template")


def custom_key(template_id: str) -> str:
    """Return the store key of a custom template id, or raise for built-ins."""
    if not template_id.startswith(CUSTOM):
        raise GrowError("Built-in templates can't be changed; duplicate it first")
    return template_id[len(CUSTOM) :]
