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
