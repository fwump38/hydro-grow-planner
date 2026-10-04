import { describe, expect, it } from "vitest";

import { profile } from "./schedule";
import { fromCanonical, toCanonical } from "./units";

describe("EC units", () => {
  it("shows mS/cm targets in the chosen unit", () => {
    expect(fromCanonical(1.4, "ppm 500")).toBe(700);
    expect(fromCanonical(1.4, "ppm 700")).toBe(980);
    expect(fromCanonical(1.4, "µS/cm")).toBe(1400);
    expect(fromCanonical(1.4, "CF")).toBe(14);
    expect(fromCanonical(1.25, "mS/cm")).toBe(1.25);
    expect(fromCanonical(null, "CF")).toBeNull();
  });
  it("converts typed values back to mS/cm", () => {
    expect(toCanonical(700, "ppm 500")).toBeCloseTo(1.4);
    expect(toCanonical(600, "ppm 500")).toBeCloseTo(1.2);
    expect(toCanonical(null, "ppm 500")).toBeNull();
  });
});

describe("schedule profile (matches the backend)", () => {
  it("handles each mode", () => {
    expect(profile({ mode: "manual" })).toEqual([]);
    expect(profile({ mode: "off" })).toEqual([]);
    expect(profile({ mode: "always_on" })).toEqual([[0, 1440]]);
    expect(profile({ mode: "time_window", on_time: "06:00:00", off_time: "21:00:00" })).toEqual([[360, 1260]]);
    expect(profile({ mode: "time_window", on_time: "22:00", off_time: "04:00" })).toEqual([
      [0, 240],
      [1320, 1440],
    ]);
    expect(profile({ mode: "time_window", on_time: "06:00", off_time: "06:00" })).toEqual([]);
  });
  it("lays out a pump cycle like the backend", () => {
    const pump = profile({ mode: "interval", interval_on: 900, interval_every: 10800 });
    expect(pump).toHaveLength(8);
    expect(pump[0]).toEqual([0, 15]);
    expect(pump[1]).toEqual([180, 195]);
    expect(profile({ mode: "interval", interval_on: 0, interval_every: 600 })).toEqual([]);
  });
});

import { guessRoles, invert } from "./roles";

describe("role guessing", () => {
  const devices = [
    { id: "1", name: "Elfsys center lights", entity_id: "switch.elfsys_center_lights" },
    { id: "2", name: "Elfsys side lights", entity_id: "switch.elfsys_side_lights" },
    { id: "3", name: "Elfsys water pump", entity_id: "switch.elfsys_water_pump" },
  ];
  const roles = ["center_lights", "side_lights", "water_pump"];
  it("matches by name", () => {
    expect(guessRoles(roles, devices)).toEqual({ center_lights: "1", side_lights: "2", water_pump: "3" });
  });
  it("leaves unknown roles empty, and never reuses a device", () => {
    const got = guessRoles(roles, [devices[2], { id: "9", name: "Garage fan", entity_id: "switch.fan" }]);
    expect(got.water_pump).toBe("3");
    expect(Object.values(got).filter((v) => v === "3")).toHaveLength(1);
  });
  it("pairs a single leftover role and device", () => {
    const got = guessRoles(["water_pump", "side_lights"], [
      { id: "a", name: "Pump", entity_id: "switch.p" },
      { id: "b", name: "Strip 2", entity_id: "switch.s2" },
    ]);
    expect(got).toEqual({ water_pump: "a", side_lights: "b" });
  });
  it("inverts, dropping unmapped roles", () => {
    expect(invert({ water_pump: "3", side_lights: "" })).toEqual({ "3": "water_pump" });
  });
});
