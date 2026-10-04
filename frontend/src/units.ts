// EC unit conversion. Plans store mS/cm; the UI shows the system's chosen unit.
// Keep in step with backend/grow_planner/core/units.py.

const FACTOR: Record<string, number> = {
  "mS/cm": 1,
  "µS/cm": 1000,
  CF: 10,
  "ppm 500": 500,
  "ppm 700": 700,
};
const DECIMALS: Record<string, number> = { "mS/cm": 2, "µS/cm": 0, CF: 1, "ppm 500": 0, "ppm 700": 0 };

export function fromCanonical(value: number | null, unit: string): number | null {
  if (value === null) return null;
  const f = 10 ** (DECIMALS[unit] ?? 2);
  return Math.round(value * (FACTOR[unit] ?? 1) * f) / f;
}

export function toCanonical(value: number | null, unit: string): number | null {
  return value === null ? null : value / (FACTOR[unit] ?? 1);
}
