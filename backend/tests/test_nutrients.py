"""Tests for the nutrient calculator."""

from __future__ import annotations

from datetime import timedelta

import pytest

from grow_planner.core import nutrients as nut
from grow_planner.core.nutrients import LITRES_PER_GALLON as GAL
from grow_planner.engine import GrowError
from grow_planner.ports import EntityState

LINE = nut.PLANT_MANA
PEAK = LINE["stages"][2]
FLOWER = LINE["stages"][3]


def by_id(result: dict) -> dict:
    return {p["id"]: p for p in result["products"]}


def test_a_full_change_gives_the_chart_dose() -> None:
    # An empty tank filled with plain water, target = the column's own EC.
    result = nut.calculate(LINE, [PEAK], 10 * GAL, 10 * GAL, None, PEAK["ec"])
    pm1 = by_id(result)["pm1"]
    assert pm1["ml_per_gal"] == pytest.approx(4.5)
    assert pm1["ml"] == pytest.approx(45)
    assert pm1["g"] == pytest.approx(45 * 1.06)


def test_topping_up_accounts_for_the_ec_already_in_the_tank() -> None:
    # 10 gal tank at EC 2.0, add 3.4 gal of water: diluted to 1.32. Target 2.7 -> rise 1.38.
    result = nut.calculate(LINE, [PEAK], 10 * GAL, 3.4 * GAL, 2.0, 2.7)
    assert result["diluted_ec"] == pytest.approx(1.32)
    pm1 = by_id(result)["pm1"]
    assert pm1["ml"] == pytest.approx(4.5 * 1.38 / 2.7 * 10)
    assert pm1["ml"] / 3.4 == pytest.approx(pm1["ml_per_gal"])
    assert result["concentrated"]


def test_a_tank_already_above_target_needs_nothing() -> None:
    result = nut.calculate(LINE, [PEAK], 10 * GAL, 1 * GAL, 3.5, 2.7)
    assert not result["needs_nutrients"]
    assert all(p["ml"] == 0 for p in result["products"])


def test_stages_are_blended_with_equal_weight() -> None:
    result = nut.calculate(LINE, [PEAK, FLOWER], 10 * GAL, 10 * GAL, None, 2.75)
    pm3 = by_id(result)["pm3"]
    expected = (0 / 2.7 + 2.9 / 2.8) / 2 * 2.75 * 10
    assert pm3["ml"] == pytest.approx(expected)


def test_bad_volumes_are_rejected() -> None:
    with pytest.raises(ValueError):
        nut.calculate(LINE, [PEAK], 10 * GAL, 11 * GAL, 2, 2.7)
    with pytest.raises(ValueError):
        nut.calculate(LINE, [PEAK], 10 * GAL, 0, 2, 2.7)
    with pytest.raises(ValueError):
        nut.calculate(LINE, [PEAK], 10 * GAL, 3 * GAL, None, 2.7)


def test_column_follows_stage_type_then_nearest_ec() -> None:
    assert nut.column_for("vegetative", None, LINE)["id"] == "peak_vegetation"
    assert nut.column_for("fruiting", 2.0, LINE)["id"] == "flowering"
    assert nut.column_for("harvest", 1.2, LINE)["id"] == "sprouting"


def test_custom_line_validation() -> None:
    ids = iter(f"n{i}" for i in range(50))
    raw = {
        "active": "new-1",
        "custom": [
            {
                "id": "new-1",
                "name": "Mine",
                "products": [{"id": "new-a", "name": "Grow", "density": 1.2}],
                "stages": [{"name": "All", "ec": 1.8, "doses": {"new-a": 3}}],
            }
        ],
    }
    clean, errors = nut.normalize_nutrients(raw, lambda: next(ids))
    assert not errors
    line = clean["custom"][0]
    assert clean["active"] == line["id"] and not line["id"].startswith("new-")
    assert line["stages"][0]["doses"] == {line["products"][0]["id"]: 3}

    raw["custom"][0].update(products=[{"name": "", "density": 0}], stages=[])
    _, errors = nut.normalize_nutrients(raw, lambda: next(ids))
    paths = {e["path"] for e in errors}
    assert "nutrients.custom[0].products[0].name" in paths
    assert "nutrients.custom[0].products[0].density" in paths
    assert "nutrients.custom[0].stages" in paths


async def grow(h) -> None:
    await h.start("Leafy Greens", stage_ref=2)
    h.system.update_config(capacity=10)


async def test_dose_needs_capacity_and_a_grow(h) -> None:
    with pytest.raises(GrowError, match="capacity"):
        h.system.nutrient_dose(3.4)
    h.system.update_config(capacity=10)
    with pytest.raises(GrowError, match="Nothing is growing"):
        h.system.nutrient_dose(3.4)


async def test_dose_uses_the_reading_and_target_range(h) -> None:
    await grow(h)
    await h.system.record_reading(ec=1.0)
    result = h.system.nutrient_dose(3.4)
    low, high = h.system.range_for("ec")
    assert result["target_ec"] == pytest.approx((low + high) / 2, abs=0.01)
    assert result["current_ec"] == 1.0 and result["current_volume"] == 6.6
    assert result["stages"][0]["grow"] and result["volume_unit"] == "gal"
    pm1 = next(p for p in result["products"] if p["id"] == "pm1")
    assert pm1["ml"] == pytest.approx(pm1["ml_per_unit"] * 3.4, rel=0.01)
    # An entered EC overrides the stored one; the target can be overridden too.
    other = h.system.nutrient_dose(3.4, ec=1.5, target_ec=2.0)
    assert other["current_ec"] == 1.5 and other["target_ec"] == 2.0
    assert any("outside" in w for w in other["warnings"]) == (not low <= 2.0 <= high)


async def test_dose_in_litres_and_in_a_different_ec_unit(h) -> None:
    await grow(h)
    h.system.update_config(volume_unit="L", capacity=40, ec_unit="ppm 500")
    await h.system.record_reading(ec=500)
    result = h.system.nutrient_dose(10)
    assert result["volume_unit"] == "L" and result["ec_unit"] == "ppm 500"
    assert result["current_ec"] == 500
    pm1 = next(p for p in result["products"] if p["id"] == "pm1")
    assert pm1["ml"] == pytest.approx(pm1["ml_per_unit"] * 10, rel=0.01)


async def test_manual_ec_goes_stale(h) -> None:
    await grow(h)
    assert h.system.ec_stale is None
    await h.system.record_reading(ec=1.2)
    assert h.system.ec_stale is False
    h.clock.advance(hours=25)
    assert h.system.ec_stale is True
    await h.system.record_reading(ph=6.0)  # pH alone doesn't refresh the EC
    assert h.system.ec_stale is True
    h.system.update_config(ec_stale_hours=48)
    assert h.system.ec_stale is False


async def test_sensor_ec_goes_stale_by_its_last_report(h) -> None:
    await grow(h)
    h.system.update_config(sensors={"ph": None, "ec": "sensor.ec", "temperature": None, "humidity": None})
    h.system.set_state("sensor.ec", EntityState("1.5", "mS/cm", None, h.clock()))
    assert h.system.ec_stale is False
    h.clock.advance(hours=30)
    assert h.system.ec_stale is True
    h.system.set_state("sensor.ec", EntityState("1.5", "mS/cm"))  # age unknown: trusted
    assert h.system.ec_stale is False


async def test_nutrient_settings_validate(h) -> None:
    for bad in ({"capacity": 0}, {"volume_unit": "pints"}, {"ec_stale_hours": 0}):
        with pytest.raises(GrowError):
            h.system.update_config(**bad)
    h.system.update_config(nutrients={"active": "builtin:nope", "custom": []})
    assert h.system.data["nutrients"]["active"] == nut.DEFAULT_LINE
    with pytest.raises(GrowError):
        h.system.update_config(nutrients={"custom": [{"name": "", "products": [], "stages": []}]})


def test_ha_unit_systems_map_to_the_apps_units() -> None:
    from grow_planner.core.units import from_ha_unit_system

    metric = {"temperature": "°C", "volume": "L", "mass": "g", "length": "km"}
    us = {"temperature": "°F", "volume": "gal", "mass": "oz", "length": "mi"}
    assert from_ha_unit_system(metric) == {"temperature": "°C", "volume": "L", "weight": "g"}
    assert from_ha_unit_system(us) == {"temperature": "°F", "volume": "gal", "weight": "oz"}
    assert from_ha_unit_system({"mass": "lb", "volume": "weird"}) == {"weight": "oz"}
    assert from_ha_unit_system(None) == {}


async def test_units_follow_home_assistant_unless_overridden(h) -> None:
    s = h.system
    assert (s.temperature_unit, s.volume_unit, s.weight_unit) == ("°C", "gal", "g")  # no HA, no plan
    s.ha_units.update(temperature="°F", volume="L", weight="oz")
    assert (s.temperature_unit, s.volume_unit, s.weight_unit) == ("°F", "L", "oz")
    s.update_config(temperature_unit="°C", weight_unit="g")
    assert (s.temperature_unit, s.volume_unit, s.weight_unit) == ("°C", "L", "g")
    s.update_config(temperature_unit=None)  # back to following Home Assistant
    assert s.temperature_unit == "°F"
    with pytest.raises(GrowError):
        s.update_config(weight_unit="lb")


async def test_capacity_survives_a_change_of_unit(h) -> None:
    s = h.system
    s.ha_units.update(volume="gal")
    s.update_config(capacity=10)
    assert s.capacity == 10
    s.ha_units.update(volume="L")  # Home Assistant switched to metric
    assert s.capacity == 37.85
    # Capacity is read in the unit that applies once the same change is saved.
    s.update_config(volume_unit="gal", capacity=5)
    assert s.capacity == 5 and s.data["capacity_l"] == pytest.approx(5 * GAL)


async def test_room_temperature_and_plan_ranges_use_the_chosen_unit(h) -> None:
    await h.start("Leafy Greens")
    s = h.system
    s.update_config(sensors={"ph": None, "ec": None, "temperature": "sensor.t", "humidity": None})
    s.set_state("sensor.t", EntityState("21", "°C"))
    s.ha_units.update(temperature="°F")
    assert s.temperature == 69.8 and s.temperature_unit == "°F"
    low, high = s.range_for("temperature")
    assert 60 < low < high < 90  # the plan's °C range, shown in °F


async def test_weights_in_ounces(h) -> None:
    await grow(h)
    await h.system.record_reading(ec=1.0)
    grams = h.system.nutrient_dose(3.4)["products"][0]
    h.system.update_config(weight_unit="oz")
    ounces = h.system.nutrient_dose(3.4)
    assert ounces["weight_unit"] == "oz"
    assert ounces["products"][0]["weight"] == pytest.approx(grams["weight"] / 28.3495, abs=0.01)
