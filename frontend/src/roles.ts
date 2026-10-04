// Templates schedule roles (center lights, side lights, water pump); plans schedule
// real devices. These helpers map one onto the other.

export interface DeviceRef {
  id: string;
  name: string;
  entity_id: string;
}

const HINTS: Record<string, RegExp> = {
  center_lights: /center|centre|main|top/i,
  side_lights: /side/i,
  water_pump: /pump|water/i,
};

/** Pick a likely device for each role, never using a device twice. */
export function guessRoles(roles: string[], devices: DeviceRef[]): Record<string, string> {
  const used = new Set<string>();
  const result: Record<string, string> = {};
  for (const role of roles) {
    const hint = HINTS[role];
    const match = devices.find(
      (d) => !used.has(d.id) && hint?.test(`${d.name} ${d.entity_id}`),
    );
    if (match) {
      result[role] = match.id;
      used.add(match.id);
    } else {
      result[role] = "";
    }
  }
  // A lone unmatched role with a lone unused device is almost certainly a pair.
  const freeRoles = roles.filter((r) => !result[r]);
  const freeDevices = devices.filter((d) => !used.has(d.id));
  if (freeRoles.length === 1 && freeDevices.length === 1) result[freeRoles[0]] = freeDevices[0].id;
  return result;
}

/** Invert a role → device map into device → role (for "save plan as template"). */
export function invert(map: Record<string, string>): Record<string, string> {
  return Object.fromEntries(
    Object.entries(map)
      .filter(([, device]) => device)
      .map(([role, device]) => [device, role]),
  );
}
