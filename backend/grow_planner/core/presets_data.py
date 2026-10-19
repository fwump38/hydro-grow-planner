"""Grow templates from the Elfsys Grow Cloud app (v1.8.5).

The PRESETS literal was generated from the app's built-in templates; do not edit it
by hand. Hand-made changes live in the `_PATCHES` section at the end of this file
and are applied on import, so they are easy to audit:

- humidity ranges for every template (Elfsys has none): 50-70 %, except Leafy Greens at
  40-70 % because it is also used for herbs, which prefer drier air
- generic pH, temperature and EC ranges for Leafy Greens
- a temperature range for Spinach
- Leafy Greens "every 3 days" tasks are real recurring tasks (the source only had
  the wording in the title)
- Leafy Greens Vegetative runs the pump 15 min every 3 h like every other stage
  (the source had it always on)
- Leafy Greens light schedules follow the Lettuce/Spinach pattern (the source had 15 h
  of side light while sprouting, both lights in Seedling, and 17 h in Vegetative)
- Mixed Herbs is not an Elfsys template: it is derived from Leafy Greens for basil,
  cilantro, scallions/chives and bok choy sharing one reservoir (see `_mixed_herbs`)

- every template is "continuous" (see `_harvest_patches`): the plants keep growing and are
  harvested a little at a time, with a repeating harvest task saying how much and where.
  The leafy templates that ended at maturity (Lettuce, Spinach) gain a Harvest stage;
  the fruiting ones (Tomato, Pepper, Bell Pepper) get a longer Fruiting stage, since the
  source stopped at the first fruit. The lengths are estimates of how long the plants
  stay productive in a small indoor kit, not Elfsys figures.

Schedules are keyed by role (see presets.py). Days are 1-based.
"""

from copy import deepcopy
from typing import Any

PRESETS: dict[str, dict[str, Any]] = {
    "bell_pepper": {
        "name": "Bell Pepper",
        "ph_min": 6.0,
        "ph_max": 6.5,
        "temp_min": 70.0,
        "temp_max": 84.0,
        "temp_unit": "°F",
        "stages": [
            {
                "name": "Sprouting",
                "stage_type": "sprouting",
                "days": 7,
                "outcome": "The third leaf appear, which is the first true leaf after "
                "the initial 2 seed leaves.",
                "ec_min": 0.7,
                "ec_max": 0.9,
                "schedules": {
                    "center_lights": {"mode": "off"},
                    "water_pump": {"mode": "interval", "interval_on": 900, "interval_every": 10800},
                    "side_lights": {
                        "mode": "time_window",
                        "on_time": "11:00:00",
                        "off_time": "17:00:00",
                    },
                },
                "tasks": [
                    {
                        "task_type": "reminder",
                        "title": "Add water and nutrients",
                        "method": "",
                        "note": "Ensure there is sufficient water with nutrients "
                        "in the grow kit. The 2-layer kit can hold about "
                        "6.9 gallons (26 liters) of water, the 3-layer "
                        "about 8.7 gallons (33 liters), and the 4-layer "
                        "about 10.3 gallons (39 liters). Check if the "
                        "water level is near the maximum water line when "
                        "the water pump is off and water levels across "
                        "layers are stable. Continuous bubbling at the "
                        "drain of the primary grow container indicates "
                        "water is still returning to the primary grow "
                        "container, meaning water level is still "
                        "stabilizing. Add the recommended amount of "
                        "nutrient concentrates to the water according to "
                        "the instructions for the sprout stage of bell "
                        "pepper (or fruit vegetables in general) provided "
                        "by your nutrient brand. Bell pepper grows "
                        "optimally at a nutrient solution with electrical "
                        "conductivity (EC) between 0.7 and 0.9 mS/cm "
                        "during this stage. If you have an EC meter, you "
                        "can monitor the EC of your grow system and adjust "
                        "nutrients accordingly. If you only have a TDS "
                        "meter, the optimal range you would be looking is "
                        "between 490 and 610 ppm.",
                        "days": [1],
                        "every": 0,
                        "until": None,
                    },
                    {
                        "task_type": "reminder",
                        "title": "Add seeds",
                        "method": "",
                        "note": "Add clay pebbles to the net pots. Wash the clay "
                        "pebbles if it is being used for the first time. "
                        "Plant bell pepper seed about half an inch deep "
                        "into the clay pebbles. Not all net pots need to "
                        "be used. Depending on the cultivar, a single %s "
                        "can grow large enough to occupied the full layer. "
                        "Use the empty hole covers to cover the unused net "
                        "pots.",
                        "days": [1],
                        "every": 0,
                        "until": None,
                    },
                    {
                        "task_type": "reminder",
                        "title": "Choose dwarf variant",
                        "method": "",
                        "note": "Choose a dwarf variant of bell pepper, preferably "
                        "no taller than 12 inches (31 cm), to grow in the "
                        "Elfsys Grow Kit. Taller varieties can quickly "
                        "outgrow the grow lights, requiring more "
                        "maintenance efforts.",
                        "days": [1],
                        "every": 0,
                        "until": None,
                    },
                    {
                        "task_type": "reminder",
                        "title": "Move the grow lights",
                        "method": "",
                        "note": "Position the grow lights about 3 inches above the "
                        "grow container cover.",
                        "days": [1],
                        "every": 0,
                        "until": None,
                    },
                    {
                        "task_type": "reminder",
                        "title": "Spray water on the clay pebbles",
                        "method": "",
                        "note": "Excessive room temperature and light from the "
                        "grow light can cause the water on the surface of "
                        "the clay pebbles to evaporate. During "
                        "germination, it is recommended to mist the "
                        "surface of the clay pebbles daily with a "
                        "household sprayer.",
                        "days": [1],
                        "every": 1,
                        "until": 7,
                    },
                    {
                        "task_type": "reminder",
                        "title": "Check water pH",
                        "method": "",
                        "note": "Bell pepper grows optimally at water with pH "
                        "between 6-6.5. If you have a pH meter, monitor "
                        "the water pH constantly to ensure it stays within "
                        "the optimal range.",
                        "days": [1],
                        "every": 0,
                        "until": None,
                    },
                    {
                        "task_type": "reminder",
                        "title": "Monitor room temperature",
                        "method": "",
                        "note": "Bell pepper grows optimally at a room temperature "
                        "of 70°F (21°C) to 84°F (29°C). Monitor the room "
                        "temperature and take cooling measures like "
                        "increase ventilation if the temperature gets too "
                        "high.",
                        "days": [1],
                        "every": 0,
                        "until": None,
                    },
                    {
                        "task_type": "reminder",
                        "title": "Look for germination",
                        "method": "",
                        "note": "When you see a faint white root emerging from the "
                        "clay pebbles, it means your seeds have "
                        "successfully germinated. If not, adjust the seed "
                        "position or sow a few more seeds to ensure "
                        "germination in the net pot.",
                        "days": [4],
                        "every": 0,
                        "until": None,
                    },
                ],
            },
            {
                "name": "Seedling",
                "stage_type": "seedling",
                "days": 7,
                "outcome": "Roots can be observed at the bottom of the net pot.",
                "ec_min": 1.0,
                "ec_max": 1.3,
                "schedules": {
                    "center_lights": {
                        "mode": "time_window",
                        "on_time": "09:00:00",
                        "off_time": "19:00:00",
                    },
                    "water_pump": {"mode": "interval", "interval_on": 900, "interval_every": 10800},
                    "side_lights": {"mode": "off"},
                },
                "tasks": [
                    {
                        "task_type": "reminder",
                        "title": "Add water and nutrients",
                        "method": "",
                        "note": "Bell pepper at seedling requires more nutrients "
                        "to grow optimally compare to the last stage. Top "
                        "up nutrient concentrates to the water according "
                        "to the instructions for the seedling stage (or "
                        "fruit vegetables in general) provided by your "
                        "nutrient brand. Bell pepper grows optimally at a "
                        "nutrient solution with electrical conductivity "
                        "(EC) between 1 and 1.3 mS/cm during this stage. "
                        "If you have an EC meter, you can monitor the EC "
                        "of your grow system and adjust nutrients "
                        "accordingly. If you only have a TDS meter, the "
                        "optimal range you would be looking is between 700 "
                        "and 880 ppm.",
                        "days": [1],
                        "every": 0,
                        "until": None,
                    },
                    {
                        "task_type": "reminder",
                        "title": "Move the grow lights",
                        "method": "",
                        "note": "Position the grow lights about 3 inches above "
                        "above the top of your plants.",
                        "days": [1],
                        "every": 0,
                        "until": None,
                    },
                    {
                        "task_type": "reminder",
                        "title": "Check water pH",
                        "method": "",
                        "note": "Bell pepper grows optimally at water with pH "
                        "between 6-6.5. If you have a pH meter, monitor "
                        "the water pH constantly to ensure it stays within "
                        "the optimal range.",
                        "days": [1],
                        "every": 0,
                        "until": None,
                    },
                    {
                        "task_type": "reminder",
                        "title": "Monitor room temperature",
                        "method": "",
                        "note": "Bell pepper grows optimally at a room temperature "
                        "of 70°F (21°C) to 84°F (29°C). Monitor the room "
                        "temperature and take cooling measures like "
                        "increase ventilation if the temperature gets too "
                        "high.",
                        "days": [1],
                        "every": 0,
                        "until": None,
                    },
                    {
                        "task_type": "reminder",
                        "title": "Pruning extra seedlings",
                        "method": "",
                        "note": "If multiple seeds in a net pot have germinated, "
                        "now is the time to select the strongest seedling "
                        "and prune the rest. The pruned seedlings are "
                        "delicious microgreens. They are edible after "
                        "washing off the dust.",
                        "days": [7],
                        "every": 0,
                        "until": None,
                    },
                ],
            },
            {
                "name": "Vegetative",
                "stage_type": "vegetative",
                "days": 21,
                "outcome": "Flower buds appear.",
                "ec_min": 2.0,
                "ec_max": 2.5,
                "schedules": {
                    "center_lights": {
                        "mode": "time_window",
                        "on_time": "06:30:00",
                        "off_time": "21:30:00",
                    },
                    "water_pump": {"mode": "interval", "interval_on": 900, "interval_every": 10800},
                    "side_lights": {
                        "mode": "time_window",
                        "on_time": "06:30:00",
                        "off_time": "21:30:00",
                    },
                },
                "tasks": [
                    {
                        "task_type": "reminder",
                        "title": "Add water and nutrients",
                        "method": "",
                        "note": "Bell pepper at vegetative requires more nutrients "
                        "to grow optimally compare to the last stage. Top "
                        "up nutrient concentrates to the water according "
                        "to the instructions for the vegetative stage (or "
                        "fruit vegetables in general) provided by your "
                        "nutrient brand. Bell pepper grows optimally at a "
                        "nutrient solution with electrical conductivity "
                        "(EC) between 2 and 2.5 mS/cm during this stage. "
                        "If you have an EC meter, you can monitor the EC "
                        "of your grow system and adjust nutrients "
                        "accordingly. If you only have a TDS meter, the "
                        "optimal range you would be looking is between "
                        "1400 and 1750 ppm.",
                        "days": [1],
                        "every": 0,
                        "until": None,
                    },
                    {
                        "task_type": "reminder",
                        "title": "Check water pH",
                        "method": "",
                        "note": "Bell pepper grows optimally at water with pH "
                        "between 6-6.5. If you have a pH meter, monitor "
                        "the water pH constantly to ensure it stays within "
                        "the optimal range.",
                        "days": [1],
                        "every": 8,
                        "until": 17,
                    },
                    {
                        "task_type": "reminder",
                        "title": "Monitor room temperature",
                        "method": "",
                        "note": "Bell pepper grows optimally at a room temperature "
                        "of 70°F (21°C) to 84°F (29°C). Monitor the room "
                        "temperature and take cooling measures like "
                        "increase ventilation if the temperature gets too "
                        "high.",
                        "days": [1],
                        "every": 8,
                        "until": 17,
                    },
                    {
                        "task_type": "reminder",
                        "title": "Move the grow lights",
                        "method": "",
                        "note": "Position the grow lights about 3 inches above "
                        "above the top of your plants.",
                        "days": [1],
                        "every": 4,
                        "until": 21,
                    },
                    {
                        "task_type": "reminder",
                        "title": "Add water and nutrients if needed",
                        "method": "",
                        "note": "Check if the water level is near the maximum "
                        "water line when the water pump is not running. If "
                        "it is not, prepare a nutrient solution according "
                        "to the instructions for the vegetative stage of "
                        "bell pepper (or fruit vegetables in general) "
                        "provided by your nutrient brand. Then, top up the "
                        "nutrient solution to the grow kit until the water "
                        "reaches the maximum water line. Bell pepper grows "
                        "optimally at a nutrient solution with electrical "
                        "conductivity (EC) between 2 and 2.5 mS/cm during "
                        "this stage. If you have an EC meter, you can "
                        "monitor the EC of your grow system and adjust "
                        "nutrients accordingly. If you only have a TDS "
                        "meter, the optimal range you would be looking is "
                        "between 1400 and 1750 ppm.",
                        "days": [5],
                        "every": 4,
                        "until": 21,
                    },
                ],
            },
            {
                "name": "Flowering",
                "stage_type": "flowering",
                "days": 14,
                "outcome": "Flowers start to wilt.",
                "ec_min": 2.0,
                "ec_max": 2.5,
                "schedules": {
                    "center_lights": {
                        "mode": "time_window",
                        "on_time": "05:30:00",
                        "off_time": "22:30:00",
                    },
                    "water_pump": {"mode": "interval", "interval_on": 900, "interval_every": 10800},
                    "side_lights": {
                        "mode": "time_window",
                        "on_time": "05:30:00",
                        "off_time": "22:30:00",
                    },
                },
                "tasks": [
                    {
                        "task_type": "reminder",
                        "title": "Add water and nutrients",
                        "method": "",
                        "note": "Bell pepper at flowering requires more nutrients "
                        "to grow optimally compare to the last stage. Top "
                        "up nutrient concentrates to the water according "
                        "to the instructions for the flowering stage (or "
                        "fruit vegetables in general) provided by your "
                        "nutrient brand. Bell pepper grows optimally at a "
                        "nutrient solution with electrical conductivity "
                        "(EC) between 2 and 2.5 mS/cm during this stage. "
                        "If you have an EC meter, you can monitor the EC "
                        "of your grow system and adjust nutrients "
                        "accordingly. If you only have a TDS meter, the "
                        "optimal range you would be looking is between "
                        "1400 and 1750 ppm.",
                        "days": [1],
                        "every": 0,
                        "until": None,
                    },
                    {
                        "task_type": "reminder",
                        "title": "Move the grow lights",
                        "method": "",
                        "note": "Position the grow lights about 3 inches above "
                        "above the top of your plants.",
                        "days": [1],
                        "every": 0,
                        "until": None,
                    },
                    {
                        "task_type": "reminder",
                        "title": "Check water pH",
                        "method": "",
                        "note": "Bell pepper grows optimally at water with pH "
                        "between 6-6.5. If you have a pH meter, monitor "
                        "the water pH constantly to ensure it stays within "
                        "the optimal range.",
                        "days": [1, 9],
                        "every": 0,
                        "until": None,
                    },
                    {
                        "task_type": "reminder",
                        "title": "Monitor room temperature",
                        "method": "",
                        "note": "Bell pepper grows optimally at a room temperature "
                        "of 70°F (21°C) to 84°F (29°C). Monitor the room "
                        "temperature and take cooling measures like "
                        "increase ventilation if the temperature gets too "
                        "high.",
                        "days": [1, 9],
                        "every": 0,
                        "until": None,
                    },
                    {
                        "task_type": "reminder",
                        "title": "Add water and nutrients if needed",
                        "method": "",
                        "note": "Check if the water level is near the maximum "
                        "water line when the water pump is not running. If "
                        "it is not, prepare a nutrient solution according "
                        "to the instructions for the flowering stage of "
                        "bell pepper (or fruit vegetables in general) "
                        "provided by your nutrient brand. Then, top up the "
                        "nutrient solution to the grow kit until the water "
                        "reaches the maximum water line. Bell pepper grows "
                        "optimally at a nutrient solution with electrical "
                        "conductivity (EC) between 2 and 2.5 mS/cm during "
                        "this stage. If you have an EC meter, you can "
                        "monitor the EC of your grow system and adjust "
                        "nutrients accordingly. If you only have a TDS "
                        "meter, the optimal range you would be looking is "
                        "between 1400 and 1750 ppm.",
                        "days": [5],
                        "every": 4,
                        "until": 13,
                    },
                ],
            },
            {
                "name": "Fruiting",
                "stage_type": "fruiting",
                "days": 42,
                "outcome": "",
                "ec_min": 2.0,
                "ec_max": 2.5,
                "schedules": {
                    "center_lights": {
                        "mode": "time_window",
                        "on_time": "04:30:00",
                        "off_time": "23:30:00",
                    },
                    "water_pump": {"mode": "interval", "interval_on": 900, "interval_every": 10800},
                    "side_lights": {
                        "mode": "time_window",
                        "on_time": "04:30:00",
                        "off_time": "23:30:00",
                    },
                },
                "tasks": [
                    {
                        "task_type": "reminder",
                        "title": "Add water and nutrients",
                        "method": "",
                        "note": "Bell pepper at fruiting requires more nutrients "
                        "to grow optimally compare to the last stage. Top "
                        "up nutrient concentrates to the water according "
                        "to the instructions for the fruiting stage (or "
                        "fruit vegetables in general) provided by your "
                        "nutrient brand. Bell pepper grows optimally at a "
                        "nutrient solution with electrical conductivity "
                        "(EC) between 2 and 2.5 mS/cm during this stage. "
                        "If you have an EC meter, you can monitor the EC "
                        "of your grow system and adjust nutrients "
                        "accordingly. If you only have a TDS meter, the "
                        "optimal range you would be looking is between "
                        "1400 and 1750 ppm.",
                        "days": [1],
                        "every": 0,
                        "until": None,
                    },
                    {
                        "task_type": "reminder",
                        "title": "Check water pH",
                        "method": "",
                        "note": "Bell pepper grows optimally at water with pH "
                        "between 6-6.5. If you have a pH meter, monitor "
                        "the water pH constantly to ensure it stays within "
                        "the optimal range.",
                        "days": [1],
                        "every": 8,
                        "until": 41,
                    },
                    {
                        "task_type": "reminder",
                        "title": "Monitor room temperature",
                        "method": "",
                        "note": "Bell pepper grows optimally at a room temperature "
                        "of 70°F (21°C) to 84°F (29°C). Monitor the room "
                        "temperature and take cooling measures like "
                        "increase ventilation if the temperature gets too "
                        "high.",
                        "days": [1],
                        "every": 8,
                        "until": 41,
                    },
                    {
                        "task_type": "reminder",
                        "title": "Add water and nutrients if needed",
                        "method": "",
                        "note": "Check if the water level is near the maximum "
                        "water line when the water pump is not running. If "
                        "it is not, prepare a nutrient solution according "
                        "to the instructions for the fruiting stage of "
                        "bell pepper (or fruit vegetables in general) "
                        "provided by your nutrient brand. Then, top up the "
                        "nutrient solution to the grow kit until the water "
                        "reaches the maximum water line. Bell pepper grows "
                        "optimally at a nutrient solution with electrical "
                        "conductivity (EC) between 2 and 2.5 mS/cm during "
                        "this stage. If you have an EC meter, you can "
                        "monitor the EC of your grow system and adjust "
                        "nutrients accordingly. If you only have a TDS "
                        "meter, the optimal range you would be looking is "
                        "between 1400 and 1750 ppm.",
                        "days": [5],
                        "every": 4,
                        "until": 41,
                    },
                ],
            },
        ],
    },
    "leafy_greens": {
        "name": "Leafy Greens",
        "ph_min": None,
        "ph_max": None,
        "temp_min": None,
        "temp_max": None,
        "temp_unit": None,
        "stages": [
            {
                "name": "Sprouting",
                "stage_type": "sprouting",
                "days": 7,
                "outcome": "The first true leaf appears (normally it is the third "
                "leaf in total for most of the plants)",
                "ec_min": None,
                "ec_max": None,
                "schedules": {
                    "center_lights": {"mode": "off"},
                    "water_pump": {"mode": "interval", "interval_on": 900, "interval_every": 10800},
                    "side_lights": {
                        "mode": "time_window",
                        "on_time": "06:00:00",
                        "off_time": "21:00:00",
                    },
                },
                "tasks": [
                    {
                        "task_type": "reminder",
                        "title": "Check water volume",
                        "method": "",
                        "note": "Ensure there is sufficient water in the grow "
                        "kit. The 2-layer kit should have about 6.9 "
                        "gallons (26 liters) of water, 3 layers of about "
                        "8.7 gallons (33 liters), and 4- layer of about "
                        "10.3 gallons (39 liters). If you cannot measure "
                        "the water volume, keep the water pump running "
                        "and wait for water to return to the primary grow "
                        "container. Continuous bubbling at the drain of "
                        "the primary grow container indicates water is "
                        "returning. Then check if the water level is near "
                        "the maximum water line. If not, continue adding "
                        "water until it reaches the maximum water line.",
                        "days": [1],
                        "every": 0,
                        "until": None,
                    },
                    {
                        "task_type": "reminder",
                        "title": "Add seeds",
                        "method": "",
                        "note": "Add clay pebbles to the net pots. Wash the clay "
                        "pebbles if it is being used for the first time. "
                        "Plant the seeds about half an inch deep into the "
                        "clay pebbles. To increase the germination rate, "
                        "it is recommended to plant 2-3 seeds per net "
                        "pot.",
                        "days": [1],
                        "every": 0,
                        "until": None,
                    },
                    {
                        "task_type": "reminder",
                        "title": "Move the grow lights",
                        "method": "",
                        "note": "Position the grow lights about 3 inches above "
                        "the grow container cover.",
                        "days": [1],
                        "every": 0,
                        "until": None,
                    },
                    {
                        "task_type": "reminder",
                        "title": "Spray water on the clay pebbles",
                        "method": "",
                        "note": "Excessive room temperature and light from the "
                        "grow light can cause the water on the surface of "
                        "the clay pebbles to evaporate. During "
                        "germination, it is recommended to mist the "
                        "surface of the clay pebbles daily with a "
                        "household sprayer.",
                        "days": [1],
                        "every": 1,
                        "until": 7,
                    },
                    {
                        "task_type": "reminder",
                        "title": "Look for germination",
                        "method": "",
                        "note": "When you see a faint white root emerging from "
                        "the clay pebbles, it means your seeds have "
                        "successfully germinated. If not, adjust the seed "
                        "position or sow a few more seeds to ensure "
                        "germination in the net pot.",
                        "days": [4],
                        "every": 0,
                        "until": None,
                    },
                    {
                        "task_type": "reminder",
                        "title": "Add water if needed",
                        "method": "",
                        "note": "Check if the water level is near the maximum "
                        "water line when the water pump is not running. "
                        "Top up until the water level reaches the maximum "
                        "water line.\n"
                        "\n"
                        "Note: To avoid leaking water, do not top up "
                        "water to the maximum water line when the water "
                        "pump is running.",
                        "days": [4],
                        "every": 0,
                        "until": None,
                    },
                ],
            },
            {
                "name": "Seedling",
                "stage_type": "seedling",
                "days": 7,
                "outcome": "Observable roots at the bottom of the net pot",
                "ec_min": None,
                "ec_max": None,
                "schedules": {
                    "center_lights": {
                        "mode": "time_window",
                        "on_time": "06:00:00",
                        "off_time": "21:00:00",
                    },
                    "water_pump": {"mode": "interval", "interval_on": 900, "interval_every": 10800},
                    "side_lights": {
                        "mode": "time_window",
                        "on_time": "09:00:00",
                        "off_time": "18:00:00",
                    },
                },
                "tasks": [
                    {
                        "task_type": "reminder",
                        "title": "Move the grow lights",
                        "method": "",
                        "note": "Position the grow lights about 4 inches above "
                        "the grow container cover.",
                        "days": [1],
                        "every": 0,
                        "until": None,
                    },
                    {
                        "task_type": "reminder",
                        "title": "Add nutrients",
                        "method": "",
                        "note": "Add nutrients to the water according to the "
                        "instructions for the vegetative stage of this "
                        "type of plant provided by your nutrient brand.",
                        "days": [1],
                        "every": 0,
                        "until": None,
                    },
                    {
                        "task_type": "reminder",
                        "title": "Add water if needed",
                        "method": "",
                        "note": "Check if the water level is near the maximum "
                        "water line when the water pump is not running. "
                        "Top up until the water level reaches the maximum "
                        "water line.\n"
                        "\n"
                        "Note: To avoid leaking water, do not top up "
                        "water to the maximum water line when the water "
                        "pump is running.",
                        "days": [5],
                        "every": 0,
                        "until": None,
                    },
                    {
                        "task_type": "reminder",
                        "title": "Pruning extra seedlings",
                        "method": "",
                        "note": "If multiple seeds in a net pot have germinated, "
                        "now is the time to select the strongest seedling "
                        "and prune the rest. The pruned seedlings are "
                        "delicious microgreens. They are edible after "
                        "washing off the dust.",
                        "days": [5],
                        "every": 0,
                        "until": None,
                    },
                ],
            },
            {
                "name": "Vegetative",
                "stage_type": "vegetative",
                "days": 90,
                "outcome": "",
                "ec_min": None,
                "ec_max": None,
                "schedules": {
                    "center_lights": {
                        "mode": "time_window",
                        "on_time": "05:00:00",
                        "off_time": "22:00:00",
                    },
                    "water_pump": {"mode": "always_on"},
                    "side_lights": {
                        "mode": "time_window",
                        "on_time": "05:00:00",
                        "off_time": "22:00:00",
                    },
                },
                "tasks": [
                    {
                        "task_type": "reminder",
                        "title": "Vegetative",
                        "method": "",
                        "note": "The plants are now entering the rapid-growing "
                        "vegetative stage. This stage can last from 2 "
                        "weeks to a few months depending on the type of "
                        "plant you are growing. During this period, "
                        "please check the status of the grow kit "
                        "routinely. We recommend to inspect the system "
                        "every three days. This includes adding water and "
                        "nutrients, adjusting the height of the grow "
                        "light, and ensuring proper ventilation.",
                        "days": [1],
                        "every": 0,
                        "until": None,
                    },
                    {
                        "task_type": "reminder",
                        "title": "Move the grow lights (every 3 days)",
                        "method": "",
                        "note": "Position the grow lights about 2 inches above "
                        "the top of your plants.",
                        "days": [1],
                        "every": 0,
                        "until": None,
                    },
                    {
                        "task_type": "reminder",
                        "title": "Add nutrients (every 3 days)",
                        "method": "",
                        "note": "Add nutrients to the water according to the "
                        "instructions for the vegetative stage of this "
                        "type of plant provided by your nutrient brand.",
                        "days": [1],
                        "every": 0,
                        "until": None,
                    },
                    {
                        "task_type": "reminder",
                        "title": "Add water if needed (every 3 days)",
                        "method": "",
                        "note": "Check if the water level is near the maximum "
                        "water line when the water pump is not running. "
                        "Top up until the water level reaches the maximum "
                        "water line.\n"
                        "\n"
                        "Note: To avoid leaking water, do not top up "
                        "water to the maximum water line when the water "
                        "pump is running.",
                        "days": [1],
                        "every": 0,
                        "until": None,
                    },
                ],
            },
        ],
    },
    "lettuce": {
        "name": "Lettuce",
        "ph_min": 6.0,
        "ph_max": 7.0,
        "temp_min": 60.0,
        "temp_max": 65.0,
        "temp_unit": "°F",
        "stages": [
            {
                "name": "Sprouting",
                "stage_type": "sprouting",
                "days": 7,
                "outcome": "The third leaf appear, which is the first true leaf after the "
                "initial 2 seed leaves.",
                "ec_min": 0.3,
                "ec_max": 0.5,
                "schedules": {
                    "center_lights": {"mode": "off"},
                    "water_pump": {"mode": "interval", "interval_on": 900, "interval_every": 10800},
                    "side_lights": {
                        "mode": "time_window",
                        "on_time": "11:30:00",
                        "off_time": "16:30:00",
                    },
                },
                "tasks": [
                    {
                        "task_type": "reminder",
                        "title": "Add water and nutrients",
                        "method": "",
                        "note": "Ensure there is sufficient water with nutrients in "
                        "the grow kit. The 2-layer kit can hold about 6.9 "
                        "gallons (26 liters) of water, the 3-layer about 8.7 "
                        "gallons (33 liters), and the 4-layer about 10.3 "
                        "gallons (39 liters). Check if the water level is near "
                        "the maximum water line when the water pump is off and "
                        "water levels across layers are stable. Continuous "
                        "bubbling at the drain of the primary grow container "
                        "indicates water is still returning to the primary "
                        "grow container, meaning water level is still "
                        "stabilizing. Add the recommended amount of nutrient "
                        "concentrates to the water according to the "
                        "instructions for the sprout stage of lettuce (or leaf "
                        "vegetables in general) provided by your nutrient "
                        "brand. Lettuce grows optimally at a nutrient solution "
                        "with electrical conductivity (EC) between 0.3 and 0.5 "
                        "mS/cm during this stage. If you have an EC meter, you "
                        "can monitor the EC of your grow system and adjust "
                        "nutrients accordingly. If you only have a TDS meter, "
                        "the optimal range you would be looking is between 200 "
                        "and 290 ppm.",
                        "days": [1],
                        "every": 0,
                        "until": None,
                    },
                    {
                        "task_type": "reminder",
                        "title": "Add seeds",
                        "method": "",
                        "note": "Add clay pebbles to the net pots. Wash the clay "
                        "pebbles if it is being used for the first time. Plant "
                        "lettuce seeds about half an inch deep into the clay "
                        "pebbles. To increase the germination rate, it is "
                        "recommended to plant 2-3 seeds per net pot.",
                        "days": [1],
                        "every": 0,
                        "until": None,
                    },
                    {
                        "task_type": "reminder",
                        "title": "Move the grow lights",
                        "method": "",
                        "note": "Position the grow lights about 3 inches above the "
                        "grow container cover.",
                        "days": [1],
                        "every": 0,
                        "until": None,
                    },
                    {
                        "task_type": "reminder",
                        "title": "Spray water on the clay pebbles",
                        "method": "",
                        "note": "Excessive room temperature and light from the grow "
                        "light can cause the water on the surface of the clay "
                        "pebbles to evaporate. During germination, it is "
                        "recommended to mist the surface of the clay pebbles "
                        "daily with a household sprayer.",
                        "days": [1],
                        "every": 1,
                        "until": 7,
                    },
                    {
                        "task_type": "reminder",
                        "title": "Check water pH",
                        "method": "",
                        "note": "Lettuce grows optimally at water with pH between 6-7. "
                        "If you have a pH meter, monitor the water pH "
                        "constantly to ensure it stays within the optimal "
                        "range.",
                        "days": [1],
                        "every": 0,
                        "until": None,
                    },
                    {
                        "task_type": "reminder",
                        "title": "Monitor room temperature",
                        "method": "",
                        "note": "Lettuce grows optimally at a room temperature of 60°F "
                        "(16°C) to 65°F (18°C). It can tolerate a few days of "
                        "temperatures up to 85°F (29°C). Monitor the room "
                        "temperature and take cooling measures like increase "
                        "ventilation if the temperature gets too high.",
                        "days": [1],
                        "every": 0,
                        "until": None,
                    },
                    {
                        "task_type": "reminder",
                        "title": "Look for germination",
                        "method": "",
                        "note": "When you see a faint white root emerging from the "
                        "clay pebbles, it means your seeds have successfully "
                        "germinated. If not, adjust the seed position or sow a "
                        "few more seeds to ensure germination in the net pot.",
                        "days": [4],
                        "every": 0,
                        "until": None,
                    },
                ],
            },
            {
                "name": "Seedling",
                "stage_type": "seedling",
                "days": 7,
                "outcome": "Roots can be observed at the bottom of the net pot.",
                "ec_min": 0.4,
                "ec_max": 0.7,
                "schedules": {
                    "center_lights": {
                        "mode": "time_window",
                        "on_time": "10:00:00",
                        "off_time": "18:00:00",
                    },
                    "water_pump": {"mode": "interval", "interval_on": 900, "interval_every": 10800},
                    "side_lights": {"mode": "off"},
                },
                "tasks": [
                    {
                        "task_type": "reminder",
                        "title": "Add water and nutrients",
                        "method": "",
                        "note": "Lettuce at seedling requires more nutrients to grow "
                        "optimally compare to the last stage. Top up nutrient "
                        "concentrates to the water according to the "
                        "instructions for the seedling stage (or leaf "
                        "vegetables in general) provided by your nutrient "
                        "brand. Lettuce grows optimally at a nutrient solution "
                        "with electrical conductivity (EC) between 0.4 and 0.7 "
                        "mS/cm during this stage. If you have an EC meter, you "
                        "can monitor the EC of your grow system and adjust "
                        "nutrients accordingly. If you only have a TDS meter, "
                        "the optimal range you would be looking is between 280 "
                        "and 420 ppm.",
                        "days": [1],
                        "every": 0,
                        "until": None,
                    },
                    {
                        "task_type": "reminder",
                        "title": "Move the grow lights",
                        "method": "",
                        "note": "Position the grow lights about 3 inches above above "
                        "the top of your plants.",
                        "days": [1],
                        "every": 0,
                        "until": None,
                    },
                    {
                        "task_type": "reminder",
                        "title": "Check water pH",
                        "method": "",
                        "note": "Lettuce grows optimally at water with pH between 6-7. "
                        "If you have a pH meter, monitor the water pH "
                        "constantly to ensure it stays within the optimal "
                        "range.",
                        "days": [1],
                        "every": 0,
                        "until": None,
                    },
                    {
                        "task_type": "reminder",
                        "title": "Monitor room temperature",
                        "method": "",
                        "note": "Lettuce grows optimally at a room temperature of 60°F "
                        "(16°C) to 65°F (18°C). It can tolerate a few days of "
                        "temperatures up to 85°F (29°C). Monitor the room "
                        "temperature and take cooling measures like increase "
                        "ventilation if the temperature gets too high.",
                        "days": [1],
                        "every": 0,
                        "until": None,
                    },
                    {
                        "task_type": "reminder",
                        "title": "Pruning extra seedlings",
                        "method": "",
                        "note": "If multiple seeds in a net pot have germinated, now "
                        "is the time to select the strongest seedling and "
                        "prune the rest. The pruned seedlings are delicious "
                        "microgreens. They are edible after washing off the "
                        "dust.",
                        "days": [6],
                        "every": 0,
                        "until": None,
                    },
                ],
            },
            {
                "name": "Vegetative",
                "stage_type": "vegetative",
                "days": 21,
                "outcome": "",
                "ec_min": 0.8,
                "ec_max": 1.3,
                "schedules": {
                    "center_lights": {
                        "mode": "time_window",
                        "on_time": "07:00:00",
                        "off_time": "21:00:00",
                    },
                    "water_pump": {"mode": "interval", "interval_on": 900, "interval_every": 10800},
                    "side_lights": {
                        "mode": "time_window",
                        "on_time": "07:00:00",
                        "off_time": "21:00:00",
                    },
                },
                "tasks": [
                    {
                        "task_type": "reminder",
                        "title": "Add water and nutrients",
                        "method": "",
                        "note": "Lettuce at vegetative requires more nutrients to grow "
                        "optimally compare to the last stage. Top up nutrient "
                        "concentrates to the water according to the "
                        "instructions for the vegetative stage (or leaf "
                        "vegetables in general) provided by your nutrient "
                        "brand. Lettuce grows optimally at a nutrient solution "
                        "with electrical conductivity (EC) between 0.8 and 1.3 "
                        "mS/cm during this stage. If you have an EC meter, you "
                        "can monitor the EC of your grow system and adjust "
                        "nutrients accordingly. If you only have a TDS meter, "
                        "the optimal range you would be looking is between 560 "
                        "and 840 ppm.",
                        "days": [1],
                        "every": 0,
                        "until": None,
                    },
                    {
                        "task_type": "reminder",
                        "title": "Check water pH",
                        "method": "",
                        "note": "Lettuce grows optimally at water with pH between 6-7. "
                        "If you have a pH meter, monitor the water pH "
                        "constantly to ensure it stays within the optimal "
                        "range.",
                        "days": [1],
                        "every": 8,
                        "until": 17,
                    },
                    {
                        "task_type": "reminder",
                        "title": "Monitor room temperature",
                        "method": "",
                        "note": "Lettuce grows optimally at a room temperature of 60°F "
                        "(16°C) to 65°F (18°C). It can tolerate a few days of "
                        "temperatures up to 85°F (29°C). Monitor the room "
                        "temperature and take cooling measures like increase "
                        "ventilation if the temperature gets too high.",
                        "days": [1],
                        "every": 8,
                        "until": 17,
                    },
                    {
                        "task_type": "reminder",
                        "title": "Move the grow lights",
                        "method": "",
                        "note": "Position the grow lights about 3 inches above above "
                        "the top of your plants.",
                        "days": [1],
                        "every": 2,
                        "until": 21,
                    },
                    {
                        "task_type": "reminder",
                        "title": "Add water and nutrients if needed",
                        "method": "",
                        "note": "Check if the water level is near the maximum water "
                        "line when the water pump is not running. If it is "
                        "not, prepare a nutrient solution according to the "
                        "instructions for the vegetative stage of lettuce (or "
                        "leaf vegetables in general) provided by your nutrient "
                        "brand. Then, top up the nutrient solution to the grow "
                        "kit until the water reaches the maximum water line. "
                        "Lettuce grows optimally at a nutrient solution with "
                        "electrical conductivity (EC) between 0.8 and 1.3 "
                        "mS/cm during this stage. If you have an EC meter, you "
                        "can monitor the EC of your grow system and adjust "
                        "nutrients accordingly. If you only have a TDS meter, "
                        "the optimal range you would be looking is between 560 "
                        "and 840 ppm.",
                        "days": [5],
                        "every": 4,
                        "until": 21,
                    },
                ],
            },
        ],
    },
    "pepper": {
        "name": "Pepper",
        "ph_min": 5.8,
        "ph_max": 6.3,
        "temp_min": 70.0,
        "temp_max": 80.0,
        "temp_unit": "°F",
        "stages": [
            {
                "name": "Sprouting",
                "stage_type": "sprouting",
                "days": 7,
                "outcome": "The third leaf appear, which is the first true leaf after the "
                "initial 2 seed leaves.",
                "ec_min": 0.7,
                "ec_max": 1.0,
                "schedules": {
                    "center_lights": {"mode": "off"},
                    "water_pump": {"mode": "interval", "interval_on": 900, "interval_every": 10800},
                    "side_lights": {
                        "mode": "time_window",
                        "on_time": "11:00:00",
                        "off_time": "17:00:00",
                    },
                },
                "tasks": [
                    {
                        "task_type": "reminder",
                        "title": "Add water and nutrients",
                        "method": "",
                        "note": "Ensure there is sufficient water with nutrients in the "
                        "grow kit. The 2-layer kit can hold about 6.9 gallons "
                        "(26 liters) of water, the 3-layer about 8.7 gallons "
                        "(33 liters), and the 4-layer about 10.3 gallons (39 "
                        "liters). Check if the water level is near the maximum "
                        "water line when the water pump is off and water levels "
                        "across layers are stable. Continuous bubbling at the "
                        "drain of the primary grow container indicates water is "
                        "still returning to the primary grow container, meaning "
                        "water level is still stabilizing. Add the recommended "
                        "amount of nutrient concentrates to the water according "
                        "to the instructions for the sprout stage of pepper (or "
                        "fruit vegetables in general) provided by your nutrient "
                        "brand. Pepper grows optimally at a nutrient solution "
                        "with electrical conductivity (EC) between 0.7 and 1 "
                        "mS/cm during this stage. If you have an EC meter, you "
                        "can monitor the EC of your grow system and adjust "
                        "nutrients accordingly. If you only have a TDS meter, "
                        "the optimal range you would be looking is between 490 "
                        "and 740 ppm.",
                        "days": [1],
                        "every": 0,
                        "until": None,
                    },
                    {
                        "task_type": "reminder",
                        "title": "Add seeds",
                        "method": "",
                        "note": "Add clay pebbles to the net pots. Wash the clay "
                        "pebbles if it is being used for the first time. Plant "
                        "pepper seed about half an inch deep into the clay "
                        "pebbles. Not all net pots need to be used. Depending "
                        "on the cultivar, a single %s can grow large enough to "
                        "occupied the full layer. Use the empty hole covers to "
                        "cover the unused net pots.",
                        "days": [1],
                        "every": 0,
                        "until": None,
                    },
                    {
                        "task_type": "reminder",
                        "title": "Choose dwarf variant",
                        "method": "",
                        "note": "Choose a dwarf variant of pepper, preferably no taller "
                        "than 12 inches (31 cm), to grow in the Elfsys Grow "
                        "Kit. Taller varieties can quickly outgrow the grow "
                        "lights, requiring more maintenance efforts.",
                        "days": [1],
                        "every": 0,
                        "until": None,
                    },
                    {
                        "task_type": "reminder",
                        "title": "Move the grow lights",
                        "method": "",
                        "note": "Position the grow lights about 3 inches above the grow "
                        "container cover.",
                        "days": [1],
                        "every": 0,
                        "until": None,
                    },
                    {
                        "task_type": "reminder",
                        "title": "Spray water on the clay pebbles",
                        "method": "",
                        "note": "Excessive room temperature and light from the grow "
                        "light can cause the water on the surface of the clay "
                        "pebbles to evaporate. During germination, it is "
                        "recommended to mist the surface of the clay pebbles "
                        "daily with a household sprayer.",
                        "days": [1],
                        "every": 1,
                        "until": 7,
                    },
                    {
                        "task_type": "reminder",
                        "title": "Check water pH",
                        "method": "",
                        "note": "Pepper grows optimally at water with pH between "
                        "5.8-6.3. If you have a pH meter, monitor the water pH "
                        "constantly to ensure it stays within the optimal "
                        "range.",
                        "days": [1],
                        "every": 0,
                        "until": None,
                    },
                    {
                        "task_type": "reminder",
                        "title": "Monitor room temperature",
                        "method": "",
                        "note": "Pepper grows optimally at a room temperature of 70°F "
                        "(21°C) to 80°F (27°C). Monitor the room temperature "
                        "and take cooling measures like increase ventilation if "
                        "the temperature gets too high.",
                        "days": [1],
                        "every": 0,
                        "until": None,
                    },
                    {
                        "task_type": "reminder",
                        "title": "Look for germination",
                        "method": "",
                        "note": "When you see a faint white root emerging from the clay "
                        "pebbles, it means your seeds have successfully "
                        "germinated. If not, adjust the seed position or sow a "
                        "few more seeds to ensure germination in the net pot.",
                        "days": [4],
                        "every": 0,
                        "until": None,
                    },
                ],
            },
            {
                "name": "Seedling",
                "stage_type": "seedling",
                "days": 7,
                "outcome": "Roots can be observed at the bottom of the net pot.",
                "ec_min": 1.0,
                "ec_max": 1.5,
                "schedules": {
                    "center_lights": {
                        "mode": "time_window",
                        "on_time": "09:00:00",
                        "off_time": "19:00:00",
                    },
                    "water_pump": {"mode": "interval", "interval_on": 900, "interval_every": 10800},
                    "side_lights": {"mode": "off"},
                },
                "tasks": [
                    {
                        "task_type": "reminder",
                        "title": "Add water and nutrients",
                        "method": "",
                        "note": "Pepper at seedling requires more nutrients to grow "
                        "optimally compare to the last stage. Top up nutrient "
                        "concentrates to the water according to the "
                        "instructions for the seedling stage (or fruit "
                        "vegetables in general) provided by your nutrient "
                        "brand. Pepper grows optimally at a nutrient solution "
                        "with electrical conductivity (EC) between 1 and 1.5 "
                        "mS/cm during this stage. If you have an EC meter, you "
                        "can monitor the EC of your grow system and adjust "
                        "nutrients accordingly. If you only have a TDS meter, "
                        "the optimal range you would be looking is between 700 "
                        "and 1050 ppm.",
                        "days": [1],
                        "every": 0,
                        "until": None,
                    },
                    {
                        "task_type": "reminder",
                        "title": "Move the grow lights",
                        "method": "",
                        "note": "Position the grow lights about 3 inches above above "
                        "the top of your plants.",
                        "days": [1],
                        "every": 0,
                        "until": None,
                    },
                    {
                        "task_type": "reminder",
                        "title": "Check water pH",
                        "method": "",
                        "note": "Pepper grows optimally at water with pH between "
                        "5.8-6.3. If you have a pH meter, monitor the water pH "
                        "constantly to ensure it stays within the optimal "
                        "range.",
                        "days": [1],
                        "every": 0,
                        "until": None,
                    },
                    {
                        "task_type": "reminder",
                        "title": "Monitor room temperature",
                        "method": "",
                        "note": "Pepper grows optimally at a room temperature of 70°F "
                        "(21°C) to 80°F (27°C). Monitor the room temperature "
                        "and take cooling measures like increase ventilation if "
                        "the temperature gets too high.",
                        "days": [1],
                        "every": 0,
                        "until": None,
                    },
                    {
                        "task_type": "reminder",
                        "title": "Pruning extra seedlings",
                        "method": "",
                        "note": "If multiple seeds in a net pot have germinated, now is "
                        "the time to select the strongest seedling and prune "
                        "the rest. The pruned seedlings are delicious "
                        "microgreens. They are edible after washing off the "
                        "dust.",
                        "days": [7],
                        "every": 0,
                        "until": None,
                    },
                ],
            },
            {
                "name": "Vegetative",
                "stage_type": "vegetative",
                "days": 21,
                "outcome": "Flower buds appear.",
                "ec_min": 2.0,
                "ec_max": 3.0,
                "schedules": {
                    "center_lights": {
                        "mode": "time_window",
                        "on_time": "06:30:00",
                        "off_time": "21:30:00",
                    },
                    "water_pump": {"mode": "interval", "interval_on": 900, "interval_every": 10800},
                    "side_lights": {
                        "mode": "time_window",
                        "on_time": "06:30:00",
                        "off_time": "21:30:00",
                    },
                },
                "tasks": [
                    {
                        "task_type": "reminder",
                        "title": "Add water and nutrients",
                        "method": "",
                        "note": "Pepper at vegetative requires more nutrients to grow "
                        "optimally compare to the last stage. Top up nutrient "
                        "concentrates to the water according to the "
                        "instructions for the vegetative stage (or fruit "
                        "vegetables in general) provided by your nutrient "
                        "brand. Pepper grows optimally at a nutrient solution "
                        "with electrical conductivity (EC) between 2 and 3 "
                        "mS/cm during this stage. If you have an EC meter, you "
                        "can monitor the EC of your grow system and adjust "
                        "nutrients accordingly. If you only have a TDS meter, "
                        "the optimal range you would be looking is between 1400 "
                        "and 2100 ppm.",
                        "days": [1],
                        "every": 0,
                        "until": None,
                    },
                    {
                        "task_type": "reminder",
                        "title": "Check water pH",
                        "method": "",
                        "note": "Pepper grows optimally at water with pH between "
                        "5.8-6.3. If you have a pH meter, monitor the water pH "
                        "constantly to ensure it stays within the optimal "
                        "range.",
                        "days": [1],
                        "every": 8,
                        "until": 17,
                    },
                    {
                        "task_type": "reminder",
                        "title": "Monitor room temperature",
                        "method": "",
                        "note": "Pepper grows optimally at a room temperature of 70°F "
                        "(21°C) to 80°F (27°C). Monitor the room temperature "
                        "and take cooling measures like increase ventilation if "
                        "the temperature gets too high.",
                        "days": [1],
                        "every": 8,
                        "until": 17,
                    },
                    {
                        "task_type": "reminder",
                        "title": "Move the grow lights",
                        "method": "",
                        "note": "Position the grow lights about 3 inches above above "
                        "the top of your plants.",
                        "days": [1],
                        "every": 4,
                        "until": 21,
                    },
                    {
                        "task_type": "reminder",
                        "title": "Add water and nutrients if needed",
                        "method": "",
                        "note": "Check if the water level is near the maximum water "
                        "line when the water pump is not running. If it is not, "
                        "prepare a nutrient solution according to the "
                        "instructions for the vegetative stage of pepper (or "
                        "fruit vegetables in general) provided by your nutrient "
                        "brand. Then, top up the nutrient solution to the grow "
                        "kit until the water reaches the maximum water line. "
                        "Pepper grows optimally at a nutrient solution with "
                        "electrical conductivity (EC) between 2 and 3 mS/cm "
                        "during this stage. If you have an EC meter, you can "
                        "monitor the EC of your grow system and adjust "
                        "nutrients accordingly. If you only have a TDS meter, "
                        "the optimal range you would be looking is between 1400 "
                        "and 2100 ppm.",
                        "days": [5],
                        "every": 4,
                        "until": 21,
                    },
                ],
            },
            {
                "name": "Flowering",
                "stage_type": "flowering",
                "days": 14,
                "outcome": "Flowers start to wilt.",
                "ec_min": 2.0,
                "ec_max": 3.0,
                "schedules": {
                    "center_lights": {
                        "mode": "time_window",
                        "on_time": "05:30:00",
                        "off_time": "22:30:00",
                    },
                    "water_pump": {"mode": "interval", "interval_on": 900, "interval_every": 10800},
                    "side_lights": {
                        "mode": "time_window",
                        "on_time": "05:30:00",
                        "off_time": "22:30:00",
                    },
                },
                "tasks": [
                    {
                        "task_type": "reminder",
                        "title": "Add water and nutrients",
                        "method": "",
                        "note": "Pepper at flowering requires more nutrients to grow "
                        "optimally compare to the last stage. Top up nutrient "
                        "concentrates to the water according to the "
                        "instructions for the flowering stage (or fruit "
                        "vegetables in general) provided by your nutrient "
                        "brand. Pepper grows optimally at a nutrient solution "
                        "with electrical conductivity (EC) between 2 and 3 "
                        "mS/cm during this stage. If you have an EC meter, you "
                        "can monitor the EC of your grow system and adjust "
                        "nutrients accordingly. If you only have a TDS meter, "
                        "the optimal range you would be looking is between 1400 "
                        "and 2100 ppm.",
                        "days": [1],
                        "every": 0,
                        "until": None,
                    },
                    {
                        "task_type": "reminder",
                        "title": "Move the grow lights",
                        "method": "",
                        "note": "Position the grow lights about 3 inches above above "
                        "the top of your plants.",
                        "days": [1],
                        "every": 0,
                        "until": None,
                    },
                    {
                        "task_type": "reminder",
                        "title": "Check water pH",
                        "method": "",
                        "note": "Pepper grows optimally at water with pH between "
                        "5.8-6.3. If you have a pH meter, monitor the water pH "
                        "constantly to ensure it stays within the optimal "
                        "range.",
                        "days": [1, 9],
                        "every": 0,
                        "until": None,
                    },
                    {
                        "task_type": "reminder",
                        "title": "Monitor room temperature",
                        "method": "",
                        "note": "Pepper grows optimally at a room temperature of 70°F "
                        "(21°C) to 80°F (27°C). Monitor the room temperature "
                        "and take cooling measures like increase ventilation if "
                        "the temperature gets too high.",
                        "days": [1, 9],
                        "every": 0,
                        "until": None,
                    },
                    {
                        "task_type": "reminder",
                        "title": "Add water and nutrients if needed",
                        "method": "",
                        "note": "Check if the water level is near the maximum water "
                        "line when the water pump is not running. If it is not, "
                        "prepare a nutrient solution according to the "
                        "instructions for the flowering stage of pepper (or "
                        "fruit vegetables in general) provided by your nutrient "
                        "brand. Then, top up the nutrient solution to the grow "
                        "kit until the water reaches the maximum water line. "
                        "Pepper grows optimally at a nutrient solution with "
                        "electrical conductivity (EC) between 2 and 3 mS/cm "
                        "during this stage. If you have an EC meter, you can "
                        "monitor the EC of your grow system and adjust "
                        "nutrients accordingly. If you only have a TDS meter, "
                        "the optimal range you would be looking is between 1400 "
                        "and 2100 ppm.",
                        "days": [5],
                        "every": 4,
                        "until": 13,
                    },
                ],
            },
            {
                "name": "Fruiting",
                "stage_type": "fruiting",
                "days": 42,
                "outcome": "",
                "ec_min": 2.0,
                "ec_max": 3.0,
                "schedules": {
                    "center_lights": {
                        "mode": "time_window",
                        "on_time": "04:30:00",
                        "off_time": "23:30:00",
                    },
                    "water_pump": {"mode": "interval", "interval_on": 900, "interval_every": 10800},
                    "side_lights": {
                        "mode": "time_window",
                        "on_time": "04:30:00",
                        "off_time": "23:30:00",
                    },
                },
                "tasks": [
                    {
                        "task_type": "reminder",
                        "title": "Add water and nutrients",
                        "method": "",
                        "note": "Pepper at fruiting requires more nutrients to grow "
                        "optimally compare to the last stage. Top up nutrient "
                        "concentrates to the water according to the "
                        "instructions for the fruiting stage (or fruit "
                        "vegetables in general) provided by your nutrient "
                        "brand. Pepper grows optimally at a nutrient solution "
                        "with electrical conductivity (EC) between 2 and 3 "
                        "mS/cm during this stage. If you have an EC meter, you "
                        "can monitor the EC of your grow system and adjust "
                        "nutrients accordingly. If you only have a TDS meter, "
                        "the optimal range you would be looking is between 1400 "
                        "and 2100 ppm.",
                        "days": [1],
                        "every": 0,
                        "until": None,
                    },
                    {
                        "task_type": "reminder",
                        "title": "Check water pH",
                        "method": "",
                        "note": "Pepper grows optimally at water with pH between "
                        "5.8-6.3. If you have a pH meter, monitor the water pH "
                        "constantly to ensure it stays within the optimal "
                        "range.",
                        "days": [1],
                        "every": 8,
                        "until": 41,
                    },
                    {
                        "task_type": "reminder",
                        "title": "Monitor room temperature",
                        "method": "",
                        "note": "Pepper grows optimally at a room temperature of 70°F "
                        "(21°C) to 80°F (27°C). Monitor the room temperature "
                        "and take cooling measures like increase ventilation if "
                        "the temperature gets too high.",
                        "days": [1],
                        "every": 8,
                        "until": 41,
                    },
                    {
                        "task_type": "reminder",
                        "title": "Add water and nutrients if needed",
                        "method": "",
                        "note": "Check if the water level is near the maximum water "
                        "line when the water pump is not running. If it is not, "
                        "prepare a nutrient solution according to the "
                        "instructions for the fruiting stage of pepper (or "
                        "fruit vegetables in general) provided by your nutrient "
                        "brand. Then, top up the nutrient solution to the grow "
                        "kit until the water reaches the maximum water line. "
                        "Pepper grows optimally at a nutrient solution with "
                        "electrical conductivity (EC) between 2 and 3 mS/cm "
                        "during this stage. If you have an EC meter, you can "
                        "monitor the EC of your grow system and adjust "
                        "nutrients accordingly. If you only have a TDS meter, "
                        "the optimal range you would be looking is between 1400 "
                        "and 2100 ppm.",
                        "days": [5],
                        "every": 4,
                        "until": 41,
                    },
                ],
            },
        ],
    },
    "spinach": {
        "name": "Spinach",
        "ph_min": 5.5,
        "ph_max": 6.2,
        "temp_min": None,
        "temp_max": None,
        "temp_unit": None,
        "stages": [
            {
                "name": "Sprouting",
                "stage_type": "sprouting",
                "days": 7,
                "outcome": "The third leaf appear, which is the first true leaf after the "
                "initial 2 seed leaves.",
                "ec_min": 0.6,
                "ec_max": 0.8,
                "schedules": {
                    "center_lights": {"mode": "off"},
                    "water_pump": {"mode": "interval", "interval_on": 900, "interval_every": 10800},
                    "side_lights": {
                        "mode": "time_window",
                        "on_time": "11:30:00",
                        "off_time": "16:30:00",
                    },
                },
                "tasks": [
                    {
                        "task_type": "reminder",
                        "title": "Add water and nutrients",
                        "method": "",
                        "note": "Ensure there is sufficient water with nutrients in "
                        "the grow kit. The 2-layer kit can hold about 6.9 "
                        "gallons (26 liters) of water, the 3-layer about 8.7 "
                        "gallons (33 liters), and the 4-layer about 10.3 "
                        "gallons (39 liters). Check if the water level is near "
                        "the maximum water line when the water pump is off and "
                        "water levels across layers are stable. Continuous "
                        "bubbling at the drain of the primary grow container "
                        "indicates water is still returning to the primary "
                        "grow container, meaning water level is still "
                        "stabilizing. Add the recommended amount of nutrient "
                        "concentrates to the water according to the "
                        "instructions for the sprout stage of spinach (or leaf "
                        "vegetables in general) provided by your nutrient "
                        "brand. Spinach grows optimally at a nutrient solution "
                        "with electrical conductivity (EC) between 0.6 and 0.8 "
                        "mS/cm during this stage. If you have an EC meter, you "
                        "can monitor the EC of your grow system and adjust "
                        "nutrients accordingly. If you only have a TDS meter, "
                        "the optimal range you would be looking is between 440 "
                        "and 560 ppm.",
                        "days": [1],
                        "every": 0,
                        "until": None,
                    },
                    {
                        "task_type": "reminder",
                        "title": "Add seeds",
                        "method": "",
                        "note": "Add clay pebbles to the net pots. Wash the clay "
                        "pebbles if it is being used for the first time. Plant "
                        "spinach seeds about half an inch deep into the clay "
                        "pebbles.",
                        "days": [1],
                        "every": 0,
                        "until": None,
                    },
                    {
                        "task_type": "reminder",
                        "title": "Move the grow lights",
                        "method": "",
                        "note": "Position the grow lights about 3 inches above the "
                        "grow container cover.",
                        "days": [1],
                        "every": 0,
                        "until": None,
                    },
                    {
                        "task_type": "reminder",
                        "title": "Spray water on the clay pebbles",
                        "method": "",
                        "note": "Excessive room temperature and light from the grow "
                        "light can cause the water on the surface of the clay "
                        "pebbles to evaporate. During germination, it is "
                        "recommended to mist the surface of the clay pebbles "
                        "daily with a household sprayer.",
                        "days": [1],
                        "every": 1,
                        "until": 7,
                    },
                    {
                        "task_type": "reminder",
                        "title": "Check water pH",
                        "method": "",
                        "note": "Spinach grows optimally at water with pH between "
                        "5.5-6.2. If you have a pH meter, monitor the water pH "
                        "constantly to ensure it stays within the optimal "
                        "range.",
                        "days": [1],
                        "every": 0,
                        "until": None,
                    },
                    {
                        "task_type": "reminder",
                        "title": "Look for germination",
                        "method": "",
                        "note": "When you see a faint white root emerging from the "
                        "clay pebbles, it means your seeds have successfully "
                        "germinated. If not, adjust the seed position or sow a "
                        "few more seeds to ensure germination in the net pot.",
                        "days": [4],
                        "every": 0,
                        "until": None,
                    },
                ],
            },
            {
                "name": "Seedling",
                "stage_type": "seedling",
                "days": 7,
                "outcome": "Roots can be observed at the bottom of the net pot.",
                "ec_min": 0.9,
                "ec_max": 1.2,
                "schedules": {
                    "center_lights": {
                        "mode": "time_window",
                        "on_time": "10:00:00",
                        "off_time": "18:00:00",
                    },
                    "water_pump": {"mode": "interval", "interval_on": 900, "interval_every": 10800},
                    "side_lights": {"mode": "off"},
                },
                "tasks": [
                    {
                        "task_type": "reminder",
                        "title": "Add water and nutrients",
                        "method": "",
                        "note": "Spinach at seedling requires more nutrients to grow "
                        "optimally compare to the last stage. Top up nutrient "
                        "concentrates to the water according to the "
                        "instructions for the seedling stage (or leaf "
                        "vegetables in general) provided by your nutrient "
                        "brand. Spinach grows optimally at a nutrient solution "
                        "with electrical conductivity (EC) between 0.9 and 1.2 "
                        "mS/cm during this stage. If you have an EC meter, you "
                        "can monitor the EC of your grow system and adjust "
                        "nutrients accordingly. If you only have a TDS meter, "
                        "the optimal range you would be looking is between 630 "
                        "and 810 ppm.",
                        "days": [1],
                        "every": 0,
                        "until": None,
                    },
                    {
                        "task_type": "reminder",
                        "title": "Move the grow lights",
                        "method": "",
                        "note": "Position the grow lights about 3 inches above above "
                        "the top of your plants.",
                        "days": [1],
                        "every": 0,
                        "until": None,
                    },
                    {
                        "task_type": "reminder",
                        "title": "Check water pH",
                        "method": "",
                        "note": "Spinach grows optimally at water with pH between "
                        "5.5-6.2. If you have a pH meter, monitor the water pH "
                        "constantly to ensure it stays within the optimal "
                        "range.",
                        "days": [1],
                        "every": 0,
                        "until": None,
                    },
                ],
            },
            {
                "name": "Vegetative",
                "stage_type": "vegetative",
                "days": 28,
                "outcome": "",
                "ec_min": 1.8,
                "ec_max": 2.3,
                "schedules": {
                    "center_lights": {
                        "mode": "time_window",
                        "on_time": "07:00:00",
                        "off_time": "21:00:00",
                    },
                    "water_pump": {"mode": "interval", "interval_on": 900, "interval_every": 10800},
                    "side_lights": {
                        "mode": "time_window",
                        "on_time": "07:00:00",
                        "off_time": "21:00:00",
                    },
                },
                "tasks": [
                    {
                        "task_type": "reminder",
                        "title": "Add water and nutrients",
                        "method": "",
                        "note": "Spinach at vegetative requires more nutrients to grow "
                        "optimally compare to the last stage. Top up nutrient "
                        "concentrates to the water according to the "
                        "instructions for the vegetative stage (or leaf "
                        "vegetables in general) provided by your nutrient "
                        "brand. Spinach grows optimally at a nutrient solution "
                        "with electrical conductivity (EC) between 1.8 and 2.3 "
                        "mS/cm during this stage. If you have an EC meter, you "
                        "can monitor the EC of your grow system and adjust "
                        "nutrients accordingly. If you only have a TDS meter, "
                        "the optimal range you would be looking is between "
                        "1260 and 1610 ppm.",
                        "days": [1],
                        "every": 0,
                        "until": None,
                    },
                    {
                        "task_type": "reminder",
                        "title": "Check water pH",
                        "method": "",
                        "note": "Spinach grows optimally at water with pH between "
                        "5.5-6.2. If you have a pH meter, monitor the water pH "
                        "constantly to ensure it stays within the optimal "
                        "range.",
                        "days": [1],
                        "every": 8,
                        "until": 25,
                    },
                    {
                        "task_type": "reminder",
                        "title": "Move the grow lights",
                        "method": "",
                        "note": "Position the grow lights about 3 inches above above "
                        "the top of your plants.",
                        "days": [1],
                        "every": 2,
                        "until": 27,
                    },
                    {
                        "task_type": "reminder",
                        "title": "Add water and nutrients if needed",
                        "method": "",
                        "note": "Check if the water level is near the maximum water "
                        "line when the water pump is not running. If it is "
                        "not, prepare a nutrient solution according to the "
                        "instructions for the vegetative stage of spinach (or "
                        "leaf vegetables in general) provided by your nutrient "
                        "brand. Then, top up the nutrient solution to the grow "
                        "kit until the water reaches the maximum water line. "
                        "Spinach grows optimally at a nutrient solution with "
                        "electrical conductivity (EC) between 1.8 and 2.3 "
                        "mS/cm during this stage. If you have an EC meter, you "
                        "can monitor the EC of your grow system and adjust "
                        "nutrients accordingly. If you only have a TDS meter, "
                        "the optimal range you would be looking is between "
                        "1260 and 1610 ppm.",
                        "days": [5],
                        "every": 4,
                        "until": 25,
                    },
                ],
            },
        ],
    },
    "tomato": {
        "name": "Tomato",
        "ph_min": 5.5,
        "ph_max": 6.5,
        "temp_min": 70.0,
        "temp_max": 82.0,
        "temp_unit": "°F",
        "stages": [
            {
                "name": "Sprouting",
                "stage_type": "sprouting",
                "days": 7,
                "outcome": "The third leaf appear, which is the first true leaf after the "
                "initial 2 seed leaves.",
                "ec_min": 0.7,
                "ec_max": 1.8,
                "schedules": {
                    "center_lights": {"mode": "off"},
                    "water_pump": {"mode": "interval", "interval_on": 900, "interval_every": 10800},
                    "side_lights": {
                        "mode": "time_window",
                        "on_time": "11:00:00",
                        "off_time": "17:00:00",
                    },
                },
                "tasks": [
                    {
                        "task_type": "reminder",
                        "title": "Add water and nutrients",
                        "method": "",
                        "note": "Ensure there is sufficient water with nutrients in the "
                        "grow kit. The 2-layer kit can hold about 6.9 gallons "
                        "(26 liters) of water, the 3-layer about 8.7 gallons "
                        "(33 liters), and the 4-layer about 10.3 gallons (39 "
                        "liters). Check if the water level is near the maximum "
                        "water line when the water pump is off and water levels "
                        "across layers are stable. Continuous bubbling at the "
                        "drain of the primary grow container indicates water is "
                        "still returning to the primary grow container, meaning "
                        "water level is still stabilizing. Add the recommended "
                        "amount of nutrient concentrates to the water according "
                        "to the instructions for the sprout stage of tomato (or "
                        "fruit vegetables in general) provided by your nutrient "
                        "brand. Tomato grows optimally at a nutrient solution "
                        "with electrical conductivity (EC) between 0.7 and 1.8 "
                        "mS/cm during this stage. If you have an EC meter, you "
                        "can monitor the EC of your grow system and adjust "
                        "nutrients accordingly. If you only have a TDS meter, "
                        "the optimal range you would be looking is between 490 "
                        "and 1230 ppm.",
                        "days": [1],
                        "every": 0,
                        "until": None,
                    },
                    {
                        "task_type": "reminder",
                        "title": "Add seeds",
                        "method": "",
                        "note": "Add clay pebbles to the net pots. Wash the clay "
                        "pebbles if it is being used for the first time. Plant "
                        "tomato seed about half an inch deep into the clay "
                        "pebbles. Not all net pots need to be used. Depending "
                        "on the cultivar, a single %s can grow large enough to "
                        "occupied the full layer. Use the empty hole covers to "
                        "cover the unused net pots.",
                        "days": [1],
                        "every": 0,
                        "until": None,
                    },
                    {
                        "task_type": "reminder",
                        "title": "Choose dwarf variant",
                        "method": "",
                        "note": "Choose a dwarf variant of tomato, preferably no taller "
                        "than 12 inches (31 cm), to grow in the Elfsys Grow "
                        "Kit. Taller varieties can quickly outgrow the grow "
                        "lights, requiring more maintenance efforts.",
                        "days": [1],
                        "every": 0,
                        "until": None,
                    },
                    {
                        "task_type": "reminder",
                        "title": "Move the grow lights",
                        "method": "",
                        "note": "Position the grow lights about 3 inches above the grow "
                        "container cover.",
                        "days": [1],
                        "every": 0,
                        "until": None,
                    },
                    {
                        "task_type": "reminder",
                        "title": "Spray water on the clay pebbles",
                        "method": "",
                        "note": "Excessive room temperature and light from the grow "
                        "light can cause the water on the surface of the clay "
                        "pebbles to evaporate. During germination, it is "
                        "recommended to mist the surface of the clay pebbles "
                        "daily with a household sprayer.",
                        "days": [1],
                        "every": 1,
                        "until": 7,
                    },
                    {
                        "task_type": "reminder",
                        "title": "Check water pH",
                        "method": "",
                        "note": "Tomato grows optimally at water with pH between "
                        "5.5-6.5. If you have a pH meter, monitor the water pH "
                        "constantly to ensure it stays within the optimal "
                        "range.",
                        "days": [1],
                        "every": 0,
                        "until": None,
                    },
                    {
                        "task_type": "reminder",
                        "title": "Monitor room temperature",
                        "method": "",
                        "note": "Tomato grows optimally at a room temperature of 70°F "
                        "(21°C) to 82°F (28°C). It can tolerate a few days of "
                        "temperatures up to 90°F (32°C). Monitor the room "
                        "temperature and take cooling measures like increase "
                        "ventilation if the temperature gets too high.",
                        "days": [1],
                        "every": 0,
                        "until": None,
                    },
                    {
                        "task_type": "reminder",
                        "title": "Look for germination",
                        "method": "",
                        "note": "When you see a faint white root emerging from the clay "
                        "pebbles, it means your seeds have successfully "
                        "germinated. If not, adjust the seed position or sow a "
                        "few more seeds to ensure germination in the net pot.",
                        "days": [4],
                        "every": 0,
                        "until": None,
                    },
                ],
            },
            {
                "name": "Seedling",
                "stage_type": "seedling",
                "days": 7,
                "outcome": "Roots can be observed at the bottom of the net pot.",
                "ec_min": 1.0,
                "ec_max": 2.5,
                "schedules": {
                    "center_lights": {
                        "mode": "time_window",
                        "on_time": "09:30:00",
                        "off_time": "18:30:00",
                    },
                    "water_pump": {"mode": "interval", "interval_on": 900, "interval_every": 10800},
                    "side_lights": {"mode": "off"},
                },
                "tasks": [
                    {
                        "task_type": "reminder",
                        "title": "Add water and nutrients",
                        "method": "",
                        "note": "Tomato at seedling requires more nutrients to grow "
                        "optimally compare to the last stage. Top up nutrient "
                        "concentrates to the water according to the "
                        "instructions for the seedling stage (or fruit "
                        "vegetables in general) provided by your nutrient "
                        "brand. Tomato grows optimally at a nutrient solution "
                        "with electrical conductivity (EC) between 1 and 2.5 "
                        "mS/cm during this stage. If you have an EC meter, you "
                        "can monitor the EC of your grow system and adjust "
                        "nutrients accordingly. If you only have a TDS meter, "
                        "the optimal range you would be looking is between 700 "
                        "and 1750 ppm.",
                        "days": [1],
                        "every": 0,
                        "until": None,
                    },
                    {
                        "task_type": "reminder",
                        "title": "Move the grow lights",
                        "method": "",
                        "note": "Position the grow lights about 3 inches above above "
                        "the top of your plants.",
                        "days": [1],
                        "every": 0,
                        "until": None,
                    },
                    {
                        "task_type": "reminder",
                        "title": "Check water pH",
                        "method": "",
                        "note": "Tomato grows optimally at water with pH between "
                        "5.5-6.5. If you have a pH meter, monitor the water pH "
                        "constantly to ensure it stays within the optimal "
                        "range.",
                        "days": [1],
                        "every": 0,
                        "until": None,
                    },
                    {
                        "task_type": "reminder",
                        "title": "Monitor room temperature",
                        "method": "",
                        "note": "Tomato grows optimally at a room temperature of 70°F "
                        "(21°C) to 82°F (28°C). It can tolerate a few days of "
                        "temperatures up to 90°F (32°C). Monitor the room "
                        "temperature and take cooling measures like increase "
                        "ventilation if the temperature gets too high.",
                        "days": [1],
                        "every": 0,
                        "until": None,
                    },
                    {
                        "task_type": "reminder",
                        "title": "Pruning extra seedlings",
                        "method": "",
                        "note": "If multiple seeds in a net pot have germinated, now is "
                        "the time to select the strongest seedling and prune "
                        "the rest. The pruned seedlings are delicious "
                        "microgreens. They are edible after washing off the "
                        "dust.",
                        "days": [7],
                        "every": 0,
                        "until": None,
                    },
                ],
            },
            {
                "name": "Vegetative",
                "stage_type": "vegetative",
                "days": 21,
                "outcome": "Flower buds appear.",
                "ec_min": 2.0,
                "ec_max": 5.0,
                "schedules": {
                    "center_lights": {
                        "mode": "time_window",
                        "on_time": "07:00:00",
                        "off_time": "21:00:00",
                    },
                    "water_pump": {"mode": "interval", "interval_on": 900, "interval_every": 10800},
                    "side_lights": {
                        "mode": "time_window",
                        "on_time": "07:00:00",
                        "off_time": "21:00:00",
                    },
                },
                "tasks": [
                    {
                        "task_type": "reminder",
                        "title": "Add water and nutrients",
                        "method": "",
                        "note": "Tomato at vegetative requires more nutrients to grow "
                        "optimally compare to the last stage. Top up nutrient "
                        "concentrates to the water according to the "
                        "instructions for the vegetative stage (or fruit "
                        "vegetables in general) provided by your nutrient "
                        "brand. Tomato grows optimally at a nutrient solution "
                        "with electrical conductivity (EC) between 2 and 5 "
                        "mS/cm during this stage. If you have an EC meter, you "
                        "can monitor the EC of your grow system and adjust "
                        "nutrients accordingly. If you only have a TDS meter, "
                        "the optimal range you would be looking is between 1400 "
                        "and 3500 ppm.",
                        "days": [1],
                        "every": 0,
                        "until": None,
                    },
                    {
                        "task_type": "reminder",
                        "title": "Check water pH",
                        "method": "",
                        "note": "Tomato grows optimally at water with pH between "
                        "5.5-6.5. If you have a pH meter, monitor the water pH "
                        "constantly to ensure it stays within the optimal "
                        "range.",
                        "days": [1],
                        "every": 8,
                        "until": 17,
                    },
                    {
                        "task_type": "reminder",
                        "title": "Monitor room temperature",
                        "method": "",
                        "note": "Tomato grows optimally at a room temperature of 70°F "
                        "(21°C) to 82°F (28°C). It can tolerate a few days of "
                        "temperatures up to 90°F (32°C). Monitor the room "
                        "temperature and take cooling measures like increase "
                        "ventilation if the temperature gets too high.",
                        "days": [1],
                        "every": 8,
                        "until": 17,
                    },
                    {
                        "task_type": "reminder",
                        "title": "Move the grow lights",
                        "method": "",
                        "note": "Position the grow lights about 3 inches above above "
                        "the top of your plants.",
                        "days": [1],
                        "every": 4,
                        "until": 21,
                    },
                    {
                        "task_type": "reminder",
                        "title": "Add water and nutrients if needed",
                        "method": "",
                        "note": "Check if the water level is near the maximum water "
                        "line when the water pump is not running. If it is not, "
                        "prepare a nutrient solution according to the "
                        "instructions for the vegetative stage of tomato (or "
                        "fruit vegetables in general) provided by your nutrient "
                        "brand. Then, top up the nutrient solution to the grow "
                        "kit until the water reaches the maximum water line. "
                        "Tomato grows optimally at a nutrient solution with "
                        "electrical conductivity (EC) between 2 and 5 mS/cm "
                        "during this stage. If you have an EC meter, you can "
                        "monitor the EC of your grow system and adjust "
                        "nutrients accordingly. If you only have a TDS meter, "
                        "the optimal range you would be looking is between 1400 "
                        "and 3500 ppm.",
                        "days": [5],
                        "every": 4,
                        "until": 21,
                    },
                ],
            },
            {
                "name": "Flowering",
                "stage_type": "flowering",
                "days": 14,
                "outcome": "Flowers start to wilt.",
                "ec_min": 2.0,
                "ec_max": 5.0,
                "schedules": {
                    "center_lights": {
                        "mode": "time_window",
                        "on_time": "06:30:00",
                        "off_time": "21:30:00",
                    },
                    "water_pump": {"mode": "interval", "interval_on": 900, "interval_every": 10800},
                    "side_lights": {
                        "mode": "time_window",
                        "on_time": "06:30:00",
                        "off_time": "21:30:00",
                    },
                },
                "tasks": [
                    {
                        "task_type": "reminder",
                        "title": "Add water and nutrients",
                        "method": "",
                        "note": "Tomato at flowering requires more nutrients to grow "
                        "optimally compare to the last stage. Top up nutrient "
                        "concentrates to the water according to the "
                        "instructions for the flowering stage (or fruit "
                        "vegetables in general) provided by your nutrient "
                        "brand. Tomato grows optimally at a nutrient solution "
                        "with electrical conductivity (EC) between 2 and 5 "
                        "mS/cm during this stage. If you have an EC meter, you "
                        "can monitor the EC of your grow system and adjust "
                        "nutrients accordingly. If you only have a TDS meter, "
                        "the optimal range you would be looking is between 1400 "
                        "and 3500 ppm.",
                        "days": [1],
                        "every": 0,
                        "until": None,
                    },
                    {
                        "task_type": "reminder",
                        "title": "Move the grow lights",
                        "method": "",
                        "note": "Position the grow lights about 3 inches above above "
                        "the top of your plants.",
                        "days": [1],
                        "every": 0,
                        "until": None,
                    },
                    {
                        "task_type": "reminder",
                        "title": "Check water pH",
                        "method": "",
                        "note": "Tomato grows optimally at water with pH between "
                        "5.5-6.5. If you have a pH meter, monitor the water pH "
                        "constantly to ensure it stays within the optimal "
                        "range.",
                        "days": [1, 9],
                        "every": 0,
                        "until": None,
                    },
                    {
                        "task_type": "reminder",
                        "title": "Monitor room temperature",
                        "method": "",
                        "note": "Tomato grows optimally at a room temperature of 70°F "
                        "(21°C) to 82°F (28°C). It can tolerate a few days of "
                        "temperatures up to 90°F (32°C). Monitor the room "
                        "temperature and take cooling measures like increase "
                        "ventilation if the temperature gets too high.",
                        "days": [1, 9],
                        "every": 0,
                        "until": None,
                    },
                    {
                        "task_type": "reminder",
                        "title": "Add water and nutrients if needed",
                        "method": "",
                        "note": "Check if the water level is near the maximum water "
                        "line when the water pump is not running. If it is not, "
                        "prepare a nutrient solution according to the "
                        "instructions for the flowering stage of tomato (or "
                        "fruit vegetables in general) provided by your nutrient "
                        "brand. Then, top up the nutrient solution to the grow "
                        "kit until the water reaches the maximum water line. "
                        "Tomato grows optimally at a nutrient solution with "
                        "electrical conductivity (EC) between 2 and 5 mS/cm "
                        "during this stage. If you have an EC meter, you can "
                        "monitor the EC of your grow system and adjust "
                        "nutrients accordingly. If you only have a TDS meter, "
                        "the optimal range you would be looking is between 1400 "
                        "and 3500 ppm.",
                        "days": [5],
                        "every": 4,
                        "until": 13,
                    },
                ],
            },
            {
                "name": "Fruiting",
                "stage_type": "fruiting",
                "days": 42,
                "outcome": "",
                "ec_min": 2.0,
                "ec_max": 5.0,
                "schedules": {
                    "center_lights": {
                        "mode": "time_window",
                        "on_time": "05:30:00",
                        "off_time": "22:30:00",
                    },
                    "water_pump": {"mode": "interval", "interval_on": 900, "interval_every": 10800},
                    "side_lights": {
                        "mode": "time_window",
                        "on_time": "05:30:00",
                        "off_time": "22:30:00",
                    },
                },
                "tasks": [
                    {
                        "task_type": "reminder",
                        "title": "Add water and nutrients",
                        "method": "",
                        "note": "Tomato at fruiting requires more nutrients to grow "
                        "optimally compare to the last stage. Top up nutrient "
                        "concentrates to the water according to the "
                        "instructions for the fruiting stage (or fruit "
                        "vegetables in general) provided by your nutrient "
                        "brand. Tomato grows optimally at a nutrient solution "
                        "with electrical conductivity (EC) between 2 and 5 "
                        "mS/cm during this stage. If you have an EC meter, you "
                        "can monitor the EC of your grow system and adjust "
                        "nutrients accordingly. If you only have a TDS meter, "
                        "the optimal range you would be looking is between 1400 "
                        "and 3500 ppm.",
                        "days": [1],
                        "every": 0,
                        "until": None,
                    },
                    {
                        "task_type": "reminder",
                        "title": "Check water pH",
                        "method": "",
                        "note": "Tomato grows optimally at water with pH between "
                        "5.5-6.5. If you have a pH meter, monitor the water pH "
                        "constantly to ensure it stays within the optimal "
                        "range.",
                        "days": [1],
                        "every": 8,
                        "until": 41,
                    },
                    {
                        "task_type": "reminder",
                        "title": "Monitor room temperature",
                        "method": "",
                        "note": "Tomato grows optimally at a room temperature of 70°F "
                        "(21°C) to 82°F (28°C). It can tolerate a few days of "
                        "temperatures up to 90°F (32°C). Monitor the room "
                        "temperature and take cooling measures like increase "
                        "ventilation if the temperature gets too high.",
                        "days": [1],
                        "every": 8,
                        "until": 41,
                    },
                    {
                        "task_type": "reminder",
                        "title": "Add water and nutrients if needed",
                        "method": "",
                        "note": "Check if the water level is near the maximum water "
                        "line when the water pump is not running. If it is not, "
                        "prepare a nutrient solution according to the "
                        "instructions for the fruiting stage of tomato (or "
                        "fruit vegetables in general) provided by your nutrient "
                        "brand. Then, top up the nutrient solution to the grow "
                        "kit until the water reaches the maximum water line. "
                        "Tomato grows optimally at a nutrient solution with "
                        "electrical conductivity (EC) between 2 and 5 mS/cm "
                        "during this stage. If you have an EC meter, you can "
                        "monitor the EC of your grow system and adjust "
                        "nutrients accordingly. If you only have a TDS meter, "
                        "the optimal range you would be looking is between 1400 "
                        "and 3500 ppm.",
                        "days": [5],
                        "every": 4,
                        "until": 41,
                    },
                ],
            },
        ],
    },
}


# --- Hand-made patches -------------------------------------------------------------

_HUMIDITY = (50.0, 70.0)

# Generic leafy greens/herbs values, in °F and mS/cm.
_LEAFY_GREENS_RANGES = {"ph_min": 5.8, "ph_max": 6.5, "temp_min": 65.0, "temp_max": 75.0}
_LEAFY_GREENS_HUMIDITY = (40.0, 70.0)  # herbs prefer drier air than lettuce
_LEAFY_GREENS_EC = {"Sprouting": (0.0, 0.5), "Seedling": (0.6, 1.2), "Vegetative": (1.2, 2.0)}
_LEAFY_GREENS_REPEATING = {
    "Move the grow lights (every 3 days)",
    "Add nutrients (every 3 days)",
    "Add water if needed (every 3 days)",
}


def _window(on: str, off: str) -> dict[str, str]:
    return {"mode": "time_window", "on_time": on, "off_time": off}


def _apply_patches() -> None:
    for preset in PRESETS.values():
        preset["humidity_min"], preset["humidity_max"] = _HUMIDITY

    leafy = PRESETS["leafy_greens"]
    leafy.update(_LEAFY_GREENS_RANGES, temp_unit="°F")
    leafy["humidity_min"], leafy["humidity_max"] = _LEAFY_GREENS_HUMIDITY
    for stage in leafy["stages"]:
        stage["ec_min"], stage["ec_max"] = _LEAFY_GREENS_EC[stage["name"]]
        for task in stage["tasks"]:
            if task["title"] in _LEAFY_GREENS_REPEATING:
                task["title"] = task["title"].removesuffix(" (every 3 days)")
                task["every"] = 3

    # Same light pattern as Lettuce and Spinach: side lights only while sprouting, center
    # lights only as seedlings, then both for 14 h.
    leafy_lights = {
        "Sprouting": (_window("11:30:00", "16:30:00"), {"mode": "off"}),
        "Seedling": ({"mode": "off"}, _window("10:00:00", "18:00:00")),
        "Vegetative": (_window("07:00:00", "21:00:00"), _window("07:00:00", "21:00:00")),
    }
    for stage in leafy["stages"]:
        side, center = leafy_lights[stage["name"]]
        stage["schedules"]["side_lights"] = dict(side)
        stage["schedules"]["center_lights"] = dict(center)

    # Every other stage of every template runs the pump 15 min every 3 h.
    for stage in leafy["stages"]:
        if stage["schedules"]["water_pump"]["mode"] == "always_on":
            stage["schedules"]["water_pump"] = {
                "mode": "interval",
                "interval_on": 900,
                "interval_every": 10800,
            }

    spinach = PRESETS["spinach"]
    spinach.update(temp_min=60.0, temp_max=70.0, temp_unit="°F")

    PRESETS["mixed_herbs"] = _mixed_herbs(leafy)
    _harvest_patches()


def _task(
    title: str,
    note: str,
    days: list[int],
    every: int = 0,
    until: int | None = None,
    task_type: str = "reminder",
    method: str = "",
):
    return {
        "task_type": task_type,
        "title": title,
        "method": method,
        "note": note,
        "days": days,
        "every": every,
        "until": until,
    }


def _mixed_herbs(leafy: dict[str, Any]) -> dict[str, Any]:
    """Return a template for herbs and alliums that share one reservoir.

    Built for basil, cilantro, scallions or chives and bok choy together, so every
    range is where those plants overlap: pH 6.0-6.5 (basil tops out at 6.5, cilantro
    and the alliums want 6.0 or more), 65-75 °F, and a middling EC that suits basil
    without starving bok choy. Germination is slower and more uneven than lettuce,
    so the early stages are longer, and herbs are cut often, not harvested once.
    """
    herbs = deepcopy(leafy)
    herbs.update(name="Mixed Herbs", ph_min=6.0, ph_max=6.5, temp_min=65.0, temp_max=75.0)
    herbs["humidity_min"], herbs["humidity_max"] = 40.0, 65.0
    sprouting, seedling, vegetative = herbs["stages"]
    sprouting.update(days=10, ec_min=0.0, ec_max=0.6)
    seedling.update(days=14, ec_min=0.8, ec_max=1.4)
    vegetative.update(days=60, ec_min=1.2, ec_max=1.8)
    sprouting["outcome"] = (
        "Most pots have sprouted. Cilantro, scallions and chives are slower than basil "
        "and bok choy, so give them until the end of the stage."
    )
    seedling["outcome"] = "Observable roots at the bottom of the net pot"

    for task in sprouting["tasks"]:
        if task["title"] == "Spray water on the clay pebbles":
            task["until"] = 10
        elif task["title"] == "Look for germination":
            task["days"] = [4, 8]
            task["note"] += (
                " Basil and bok choy usually sprout within a week; cilantro, scallions "
                "and chives can take two."
            )
    sprouting["tasks"].insert(
        2,
        _task(
            "Plant each herb in its own pots",
            "Keep each herb together, grouped by how tall it grows, so the taller "
            "ones (basil, bok choy) don't shade the shorter ones (chives, scallions). "
            "Put the thirstiest plants nearest the drain. Sow 2-3 seeds per pot; "
            "cilantro and scallion seeds benefit from a day's soak first.",
            [1],
        ),
    )

    vegetative["tasks"] += [
        _task(
            "Pinch and harvest herbs",
            "Cut basil just above a leaf pair and pinch off any flower buds. Cut "
            "scallions, chives and cilantro an inch or two above the pot. Harvest bok "
            "choy as whole heads or outer leaves. Start with the plants that are "
            "tallest and bushiest, and rotate so no one pot is stripped.",
            [14],
            every=7,
            task_type="harvest",
            method="Never take more than a third of a plant at once",
        ),
        _task(
            "Check for bolting",
            "Cilantro and scallions bolt (send up a flower stalk) when it is warm or "
            "the roots are crowded. If it is, harvest the plant and reseed.",
            [21],
            every=14,
        ),
        _task(
            "Sow cilantro again",
            "Cilantro runs out fast. A new pot every three weeks keeps a steady "
            "supply of fresh leaves.",
            [21],
            every=21,
            until=45,
        ),
    ]
    return herbs


# What to harvest, how much and from where; the plants' productive lifespan in this kit.
_LEAFY_HARVEST_NOTE = (
    "Only cut leaves that are about as big as your hand or bigger. Take the outer, older "
    "leaves first and leave the center of each plant alone: the crown (the growing point "
    "in the middle) makes the new leaves. Use clean scissors and cut about an inch above "
    "the crown. Spread the picking over all the pots, so none is stripped; skip a plant "
    "that has not grown back since the last cut. Leaves keep best if cut right after the "
    "lights come on."
)
# Shown as the signs the grow is done: the last stage of a continuous plan ends when the
# plants are spent, which only a person can judge.
_LEAFY_HARVEST_END = (
    "Regrowth is slow or the leaves are small, bitter or tough, or a flower stalk is "
    "rising from the center (bolting). Harvest what is left, clean the system and replant."
)


def _harvest_stage(
    source: dict[str, Any], days: int, outcome: str, harvest: dict[str, Any]
) -> dict[str, Any]:
    """Return a stage that continues `source` for `days` days with a repeating harvest task."""
    stage = deepcopy(source)
    stage.update(name="Harvest", stage_type="harvest", days=days, outcome=outcome)
    # One-off setup tasks are done; keep the upkeep, to the end of the stage.
    stage["tasks"] = [t for t in stage["tasks"] if t["every"]]
    for task in stage["tasks"]:
        task["until"] = days
    stage["tasks"].append(harvest)
    return stage


def _harvest_patches() -> None:
    for preset in PRESETS.values():
        preset["harvest_style"] = "continuous"

    # Lettuce and spinach: Vegetative ends when the plants are mature; they then go on to
    # be cut a third at a time until they run out of steam.
    for key, days, every, note_extra, lifespan in (
        (
            "lettuce",
            42,
            5,
            "",
            "about 10-11 weeks from sowing",
        ),
        (
            "spinach",
            28,
            5,
            " Spinach bolts quickly when warm or under long days, so keep it cool and "
            "expect a shorter run than lettuce.",
            "about 10 weeks from sowing",
        ),
    ):
        preset = PRESETS[key]
        vegetative = preset["stages"][-1]
        harvest = _task(
            "Harvest outer leaves",
            _LEAFY_HARVEST_NOTE + note_extra,
            [1],
            every=every,
            until=days,
            task_type="harvest",
            method="Cut up to a third of a plant's leaves (the biggest outer ones)",
        )
        preset["stages"].append(_harvest_stage(vegetative, days, _LEAFY_HARVEST_END, harvest))
        vegetative["outcome"] = (
            "Plants are full size, with leaves about as big as your hand, ready for the first cut."
        )
        preset["notes"] = (
            f"Cut-and-come-again: the plants are cut a third at a time from the Harvest "
            f"stage on and stay productive for {lifespan}. {preset.get('notes', '')}"
        ).strip()

    PRESETS["leafy_greens"]["stages"][-1]["outcome"] = _LEAFY_HARVEST_END
    PRESETS["mixed_herbs"]["stages"][-1]["outcome"] = (
        "The plants are leggy, woody or going to seed and no longer grow back well after "
        "cutting. Harvest what is left, clean the system and replant."
    )

    # Leafy Greens (generic) already has one long Vegetative stage; harvest inside it.
    leafy = PRESETS["leafy_greens"]
    leafy["stages"][-1]["tasks"].append(
        _task(
            "Harvest outer leaves",
            _LEAFY_HARVEST_NOTE
            + " This stage can run for around three months; "
            + _LEAFY_HARVEST_END,
            [21],
            every=5,
            until=leafy["stages"][-1]["days"],
            task_type="harvest",
            method="Cut up to a third of a plant's leaves (the biggest outer ones)",
        )
    )

    # Fruiting crops: pick ripe fruit as it comes. The source's 42 days stops at the first
    # fruit; the plants carry on for months, so stretch Fruiting and add the picking.
    for key, days, first, every, method, note in (
        (
            "tomato",
            90,
            28,
            3,
            "Pick only fully colored fruit; leave unripe ones to ripen",
            "Pick fruit that has turned its full color and gives slightly when squeezed. "
            "Twist or cut it off with its little cap (the calyx) on, from the lowest "
            "truss first, since that ripens first. Pick the whole truss at once only "
            "when most of it is ripe. Remove yellowing leaves below the lowest truss at "
            "the same time to keep air moving. A dwarf plant is productive for about "
            "three months of fruiting; pick everything when the plant stops setting new "
            "fruit or the lower leaves are mostly spent.",
        ),
        (
            "pepper",
            90,
            30,
            4,
            "Pick fully colored peppers; leave unripe ones",
            "Hot peppers are hottest and sweetest when fully colored, though they can be "
            "picked green earlier. Cut each pepper off with scissors, leaving a short "
            "piece of stem, rather than pulling, which tears the branch. Start with the "
            "biggest, most colorful ones near the base of the plant; picking encourages "
            "new flowers. The plant stays productive for about three months of fruiting "
            "in this kit; harvest everything when flowering stops.",
        ),
        (
            "bell_pepper",
            90,
            35,
            5,
            "Pick full-size peppers; leave smaller ones to grow",
            "Pick a bell pepper when it is full size and firm. Green ones can be picked "
            "then; leave it longer to turn red, yellow or orange, which is sweeter but "
            "slows the plant down. Cut with scissors, leaving about half an inch of "
            "stem, never pull. Pick the biggest fruit lowest on the plant first, and take "
            "at most a few at a time so the plant keeps enough leaf to ripen the rest. "
            "Expect about three months of fruiting from a dwarf plant; harvest everything "
            "when it stops flowering.",
        ),
    ):
        fruiting = PRESETS[key]["stages"][-1]
        fruiting["outcome"] = (
            "The plant has stopped setting new fruit, or most of its leaves are yellow or "
            "spent. Pick what is left, clean the system and replant."
        )
        old_days = fruiting["days"]
        fruiting["days"] = days
        for task in fruiting["tasks"]:
            if task["until"] == old_days - 1:  # ran to the end of the stage
                task["until"] = days - 1
        fruiting["tasks"].append(
            _task(
                "Harvest ripe fruit",
                note,
                [first],
                every=every,
                until=days,
                task_type="harvest",
                method=method,
            )
        )


_apply_patches()
