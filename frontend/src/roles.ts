// Templates schedule roles (center lights, side lights, water pump); plans schedule
// real devices. These helpers map one onto the other. A role can drive several
// devices, e.g. one plug per pair of layers.

export interface DeviceRef {
  id: string;
  name: string;
  entity_id: string;
}

/** Role → the ids of the devices that play it. */
export type RoleMap = Record<string, string[]>;

const HINTS: Record<string, RegExp> = {
  center_lights: /center|centre|main|top/i,
  side_lights: /side/i,
  water_pump: /pump|water/i,
};

/**
 * Pick a likely device for each role, never using a device twice.
 * Devices in `avoid` (e.g. lights another grow already runs) are not picked.
 */
export function guessRoles(roles: string[], devices: DeviceRef[], avoid: Set<string> = new Set()): RoleMap {
  const used = new Set<string>(avoid);
  const result: RoleMap = {};
  for (const role of roles) {
    const hint = HINTS[role];
    const match = devices.find((d) => !used.has(d.id) && hint?.test(`${d.name} ${d.entity_id}`));
    if (match) {
      result[role] = [match.id];
      used.add(match.id);
    } else {
      result[role] = [];
    }
  }
  // A lone unmatched role with a lone unused device is almost certainly a pair.
  const freeRoles = roles.filter((r) => result[r].length === 0);
  const freeDevices = devices.filter((d) => !used.has(d.id));
  if (freeRoles.length === 1 && freeDevices.length === 1) result[freeRoles[0]] = [freeDevices[0].id];
  return result;
}

/** Invert a role → devices map into device → role (for "save plan as template"). */
export function invert(map: RoleMap): Record<string, string> {
  const result: Record<string, string> = {};
  for (const [role, ids] of Object.entries(map)) {
    for (const id of ids) result[id] = role;
  }
  return result;
}
