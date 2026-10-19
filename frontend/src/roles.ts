// Helpers for choosing zones (groups of lights) when starting a grow.

export interface ZoneRef {
  id: string;
  name: string;
  /** Names of the running grows that drive this zone's lights. */
  busy_by: string[];
}

/** The other grows using a zone (the grow being replaced doesn't count: it is about to stop). */
export function busyWith(zone: ZoneRef, ignoreGrow?: string): string[] {
  return zone.busy_by.filter((name) => name !== ignoreGrow);
}

/** Zones to tick at first: the only free one, so a one-zone-left start needs no choosing. */
export function defaultZones(zones: ZoneRef[], ignoreGrow?: string): string[] {
  const free = zones.filter((z) => busyWith(z, ignoreGrow).length === 0);
  return free.length === 1 ? [free[0].id] : [];
}

/** A grow's default name: the zones it takes, e.g. "Layers 1+2". */
export function zoneLabel(zones: ZoneRef[], ids: string[]): string {
  return zones.filter((z) => ids.includes(z.id)).map((z) => z.name).join(" + ");
}
