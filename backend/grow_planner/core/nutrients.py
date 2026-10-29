"""Nutrient lines and the dosing calculator. Pure logic, no I/O.

A nutrient line is a set of products (with a density, so volumes can be shown as
weights) and a dose chart: for each stage column, how many ml of each product go in
one US gallon of water, and the EC that mix is expected to give.

    {
      "id": "builtin:plant_mana", "name": "Elfsys Plant Mana",
      "products": [{"id": "pm1", "name": "Plant Mana 1", "short": "PM-1", "density": 1.06}],
      "stages": [
        {"id": "sprouting", "name": "Sprouting", "ec": 1.1,
         "stage_types": ["germination", "sprouting"], "doses": {"pm1": 1.8}}
      ]
    }

EC is in mS/cm. The calculator assumes EC rises in proportion to the dose, so a stage's
recipe at full strength gives its `ec` and half the recipe gives half of it.
"""

from __future__ import annotations

from collections.abc import Callable
import copy
from typing import Any

from .const import STAGE_TYPES

Error = dict[str, str]

from .units import LITRES_PER_GALLON, VOLUME_UNITS  # noqa: F401  (re-exported)
BUILTIN_PREFIX = "builtin:"
DEFAULT_LINE = f"{BUILTIN_PREFIX}plant_mana"
DEFAULT_STALE_HOURS = 24

PLANT_MANA: dict[str, Any] = {
    "id": DEFAULT_LINE,
    "name": "Elfsys Plant Mana",
    "builtin": True,
    "products": [
        {"id": "pm1", "name": "Plant Mana 1", "short": "PM-1", "density": 1.06},
        {"id": "pm2", "name": "Plant Mana 2", "short": "PM-2", "density": 1.10},
        {"id": "pm3", "name": "Plant Mana 3", "short": "PM-3", "density": 1.26},
        {"id": "pmes", "name": "Plant Mana ES", "short": "PM-ES", "density": 1.06},
    ],
    # Doses are ml per US gallon of water, from the Elfsys feeding chart.
    "stages": [
        {
            "id": "sprouting",
            "name": "Sprouting",
            "ec": 1.1,
            "stage_types": ["germination", "sprouting"],
            "doses": {"pm1": 1.8, "pm2": 1.3, "pm3": 0, "pmes": 0},
        },
        {
            "id": "early_vegetation",
            "name": "Early vegetation",
            "ec": 2.3,
            "stage_types": ["seedling"],
            "doses": {"pm1": 3.7, "pm2": 2.5, "pm3": 0, "pmes": 0.5},
        },
        {
            "id": "peak_vegetation",
            "name": "Peak vegetation",
            "ec": 2.7,
            "stage_types": ["vegetative"],
            "doses": {"pm1": 4.5, "pm2": 3.2, "pm3": 0, "pmes": 0.8},
        },
        {
            "id": "flowering",
            "name": "Flowering / fruiting",
            "ec": 2.8,
            "stage_types": ["flowering", "fruiting", "ripening"],
            "doses": {"pm1": 2.2, "pm2": 2.7, "pm3": 2.9, "pmes": 0.8},
        },
    ],
}


def default_nutrients() -> dict[str, Any]:
    """Return the persisted nutrient settings of a new system: Plant Mana, no custom lines."""
    return {"active": DEFAULT_LINE, "custom": []}


def builtin_lines() -> list[dict[str, Any]]:
    """Return the nutrient lines that ship with the app."""
    return [copy.deepcopy(PLANT_MANA)]


def all_lines(nutrients: dict[str, Any]) -> list[dict[str, Any]]:
    """Return built-in lines followed by the system's own."""
    return builtin_lines() + [dict(c, builtin=False) for c in nutrients.get("custom", [])]


def active_line(nutrients: dict[str, Any]) -> dict[str, Any]:
    """Return the line in use, falling back to the first one if it was deleted."""
    lines = all_lines(nutrients)
    return next((ln for ln in lines if ln["id"] == nutrients.get("active")), lines[0])


def _positive(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if number > 0 else None


def normalize_line(
    raw: dict[str, Any], make_id: Callable[[], str], path: str = "nutrients"
) -> tuple[dict[str, Any], list[Error]]:
    """Return (clean custom nutrient line, errors) for what the settings screen sends."""
    errors: list[Error] = []

    def bad(sub: str, message: str) -> None:
        errors.append({"path": f"{path}.{sub}", "message": message})

    name = str(raw.get("name") or "").strip()
    if not name:
        bad("name", "Enter a name")

    products: list[dict[str, Any]] = []
    # Doses are keyed by the id the editor knew a product by, which may be a temporary one.
    sent_ids: dict[str, str] = {}
    seen: set[str] = set()
    for i, item in enumerate(raw.get("products") or []):
        pname = str(item.get("name") or "").strip()
        if not pname:
            bad(f"products[{i}].name", "Enter a name")
        density = _positive(item.get("density"))
        if density is None:
            bad(f"products[{i}].density", "Density (g/ml) must be above 0")
            density = 1.0
        pid = str(item.get("id") or "")
        sent = pid
        if not pid or pid.startswith("new-") or pid in seen:
            pid = make_id()
        seen.add(pid)
        sent_ids[pid] = sent
        products.append(
            {
                "id": pid,
                "name": pname,
                "short": str(item.get("short") or "").strip() or pname,
                "density": density,
            }
        )
    if not products:
        bad("products", "Add at least one product")

    stages: list[dict[str, Any]] = []
    seen_stages: set[str] = set()
    for i, item in enumerate(raw.get("stages") or []):
        sname = str(item.get("name") or "").strip()
        if not sname:
            bad(f"stages[{i}].name", "Enter a name")
        ec = _positive(item.get("ec"))
        if ec is None:
            bad(f"stages[{i}].ec", "Enter the EC this mix gives (mS/cm)")
            ec = 1.0
        doses: dict[str, float] = {}
        for product in products:
            try:
                dose = float((item.get("doses") or {}).get(sent_ids[product["id"]]) or 0)
            except (TypeError, ValueError):
                dose = -1
            if dose < 0:
                bad(f"stages[{i}].doses.{product['id']}", "Must be 0 or more")
                dose = 0
            doses[product["id"]] = dose
        if not any(doses.values()):
            bad(f"stages[{i}].doses", "Dose at least one product")
        sid = str(item.get("id") or "")
        if not sid or sid.startswith("new-") or sid in seen_stages:
            sid = make_id()
        seen_stages.add(sid)
        stages.append(
            {
                "id": sid,
                "name": sname,
                "ec": ec,
                "stage_types": [t for t in item.get("stage_types") or [] if t in STAGE_TYPES],
                "doses": doses,
            }
        )
    if not stages:
        bad("stages", "Add at least one column to the dose chart")

    line_id = str(raw.get("id") or "")
    if not line_id or line_id.startswith(("new-", BUILTIN_PREFIX)):
        line_id = make_id()
    return {"id": line_id, "name": name, "products": products, "stages": stages}, errors


def normalize_nutrients(
    raw: dict[str, Any], make_id: Callable[[], str]
) -> tuple[dict[str, Any], list[Error]]:
    """Return (clean nutrient settings, errors); ids of custom lines are kept."""
    errors: list[Error] = []
    custom: list[dict[str, Any]] = []
    renamed: dict[str, str] = {}
    for i, item in enumerate(raw.get("custom") or []):
        line, problems = normalize_line(item, make_id, f"nutrients.custom[{i}]")
        errors += problems
        renamed[str(item.get("id") or "")] = line["id"]
        custom.append(line)
    active = renamed.get(str(raw.get("active") or ""), raw.get("active"))
    nutrients = {"active": active, "custom": custom}
    if active not in {ln["id"] for ln in all_lines(nutrients)}:
        nutrients["active"] = DEFAULT_LINE
    return nutrients, errors


def column_for(stage_type: str, stage_ec: float | None, line: dict[str, Any]) -> dict[str, Any]:
    """Return the dose-chart column that fits a grow's current stage.

    The column that lists the stage's type wins; otherwise (harvest, other, or a line
    that doesn't map it) the column whose EC is nearest the stage's target EC.
    """
    for column in line["stages"]:
        if stage_type in column["stage_types"]:
            return column
    if stage_ec is not None:
        return min(line["stages"], key=lambda c: abs(c["ec"] - stage_ec))
    return line["stages"][-1]


def target_ec(low: float | None, high: float | None) -> float | None:
    """Return the middle of an EC range, or the one limit there is."""
    if low is not None and high is not None:
        return round((low + high) / 2, 3)
    return high if high is not None else low


def calculate(
    line: dict[str, Any],
    columns: list[dict[str, Any]],
    capacity_l: float,
    added_l: float,
    current_ec: float | None,
    target: float,
) -> dict[str, Any]:
    """Work out how much of each product to add with `added_l` litres of fresh water.

    The tank is topped up to `capacity_l`, so it held `capacity_l - added_l` before.
    Fresh water carries no EC, so mixing dilutes the tank's `current_ec`; the nutrients
    must make up the rest of the way to `target`. The recipes of `columns` (one per
    running grow's stage) are blended with equal weight, then scaled to the EC needed.
    Volumes come back in litres and ml of product; callers convert for display.
    """
    if added_l <= 0:
        raise ValueError("Add some water")
    if added_l > capacity_l + 1e-9:
        raise ValueError("That is more water than the tank holds")
    existing = capacity_l - added_l
    if existing > 1e-9 and current_ec is None:
        raise ValueError("Enter the current EC")
    diluted = (current_ec or 0.0) * existing / capacity_l
    rise = max(target - diluted, 0.0)

    # ml per US gallon of final tank water, per mS/cm of EC rise.
    ratio = {
        p["id"]: sum(c["doses"].get(p["id"], 0) / c["ec"] for c in columns) / len(columns)
        for p in line["products"]
    }
    capacity_gal = capacity_l / LITRES_PER_GALLON
    added_gal = added_l / LITRES_PER_GALLON
    products = []
    for p in line["products"]:
        ml = ratio[p["id"]] * rise * capacity_gal
        products.append(
            {
                "id": p["id"],
                "name": p["name"],
                "short": p["short"],
                "ml": ml,
                "g": ml * p["density"],
                "ml_per_gal": ml / added_gal,
                "ml_per_l": ml / added_l,
                "g_per_gal": ml * p["density"] / added_gal,
                "g_per_l": ml * p["density"] / added_l,
            }
        )
    # What the chart says for one gallon of plain water at the same blend, for comparison.
    full = {
        p["id"]: sum(c["doses"].get(p["id"], 0) for c in columns) / len(columns)
        for p in line["products"]
    }
    return {
        "existing_l": existing,
        "diluted_ec": diluted,
        "target_ec": target,
        "needs_nutrients": rise > 1e-9,
        "products": products,
        "chart_ml_per_gal": full,
        "concentrated": any(
            pr["ml_per_gal"] > full[pr["id"]] * 1.001 + 1e-9 for pr in products
        ),
    }
