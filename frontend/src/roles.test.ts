import { describe, expect, it } from "vitest";

import { busyWith, defaultZones, zoneLabel } from "./roles";

const zones = [
  { id: "a", name: "Layers 1+2", busy_by: ["Lettuce"] },
  { id: "b", name: "Layers 3+4", busy_by: [] },
];

describe("zones", () => {
  it("picks the only free zone", () => {
    expect(defaultZones(zones)).toEqual(["b"]);
  });
  it("does not guess when several or none are free", () => {
    expect(defaultZones([zones[1], { id: "c", name: "C", busy_by: [] }])).toEqual([]);
    expect(defaultZones([zones[0]])).toEqual([]);
  });
  it("ignores the grow being replaced", () => {
    expect(busyWith(zones[0], "Lettuce")).toEqual([]);
    expect(defaultZones(zones, "Lettuce")).toEqual([]);
  });
  it("names a grow after its zones", () => {
    expect(zoneLabel(zones, ["a", "b"])).toBe("Layers 1+2 + Layers 3+4");
  });
});
