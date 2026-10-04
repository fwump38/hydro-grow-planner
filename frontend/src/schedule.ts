// Client-side preview of a device schedule, for the editor's 24-hour bar.
// Mirrors backend/grow_planner/core/schedule.py (desired_state / day_profile).

import type { Schedule } from "./types";

const DAY_SECONDS = 86400;

function minutes(value: string | undefined, fallback: number): number {
  if (!value) return fallback;
  const [h, m] = value.split(":").map(Number);
  return Number.isFinite(h) && Number.isFinite(m) ? h * 60 + m : fallback;
}

/** On-windows of a day as [start, end) minutes. */
export function profile(s: Schedule): [number, number][] {
  switch (s.mode) {
    case "always_on":
      return [[0, 1440]];
    case "time_window": {
      const on = minutes(s.on_time, 360);
      const off = minutes(s.off_time, 1320);
      if (on === off) return [];
      if (on < off) return [[on, off]];
      return [
        [0, off],
        [on, 1440],
      ];
    }
    case "interval": {
      const every = s.interval_every ?? 0;
      const on = Math.min(s.interval_on ?? 0, every);
      if (every <= 0 || on <= 0) return [];
      if (on >= every) return [[0, 1440]];
      const windows: [number, number][] = [];
      for (let t = 0; t < DAY_SECONDS; t += every) {
        windows.push([t / 60, Math.min(t + on, DAY_SECONDS) / 60]);
      }
      return windows;
    }
    default:
      return [];
  }
}

export function describe(s: Schedule): string {
  switch (s.mode) {
    case "manual":
      return "Not managed";
    case "off":
      return "Off";
    case "always_on":
      return "Always on";
    case "time_window":
      return `${(s.on_time ?? "").slice(0, 5)}–${(s.off_time ?? "").slice(0, 5)}`;
    case "interval":
      return `${span(s.interval_on ?? 0)} every ${span(s.interval_every ?? 0)}`;
    default:
      return s.mode;
  }
}

function span(seconds: number): string {
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = seconds % 60;
  return [h && `${h} h`, m && `${m} min`, s && `${s} s`].filter(Boolean).join(" ") || "0 s";
}
