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

// -- temperature -----------------------------------------------------------------------------------

export function convertTemp(value: number | null, from: string | null, to: string): number | null {
  if (value === null || !from || from === to) return value;
  const out = from === "°C" ? (value * 9) / 5 + 32 : ((value - 32) * 5) / 9;
  return Math.round(out * 10) / 10;
}

/** A plan with its temperature range expressed in `unit` (the display unit chosen in Settings/HA). */
export function planInUnit<T extends { temp_min: number | null; temp_max: number | null; temp_unit: string | null }>(plan: T, unit: string): T {
  if ((plan.temp_unit ?? "°C") === unit) return { ...plan, temp_unit: unit };
  return {
    ...plan,
    temp_min: convertTemp(plan.temp_min, plan.temp_unit ?? "°C", unit),
    temp_max: convertTemp(plan.temp_max, plan.temp_unit ?? "°C", unit),
    temp_unit: unit,
  };
}

/** "60–65 °F" for a range stored in `from`, shown in `to`. */
export function tempRangeText(min: number | null, max: number | null, from: string | null, to: string): string | null {
  const lo = convertTemp(min, from ?? "°C", to);
  const hi = convertTemp(max, from ?? "°C", to);
  if (lo === null && hi === null) return null;
  const range = lo !== null && hi !== null ? `${lo}–${hi}` : lo !== null ? `≥ ${lo}` : `≤ ${hi}`;
  return `${range} ${to}`;
}
