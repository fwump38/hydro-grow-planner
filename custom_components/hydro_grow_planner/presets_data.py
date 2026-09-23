"""Grow templates from the Elfsys Grow Cloud app (v1.8.5).

Generated from the app's built-in templates; do not edit by hand.
Schedules are keyed by role (see presets.py). Days are 1-based.
"""

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
