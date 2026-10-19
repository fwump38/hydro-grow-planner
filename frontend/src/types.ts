// Shapes returned by the backend (see backend/grow_planner/snapshot.py and api.py).

export type Metric = "ph" | "ec" | "temperature" | "humidity";

export interface MetricView {
  value: number | null;
  min: number | null;
  max: number | null;
  range: string | null;
  out_of_range: boolean | null;
  /** The running grows' target ranges don't overlap; the oldest grow's range is shown. */
  conflict: boolean;
  from_sensor: boolean;
  unit: string | null;
}

export interface DeviceView {
  id: string;
  name: string;
  entity_id: string;
  light: boolean;
  state: boolean | null;
  desired: boolean | null;
  override: boolean;
  mode: string | null;
  schedule: string | null;
  next_change: string | null;
  /** The grows that schedule this device. With more than one it is on if any wants it on. */
  drivers: { grow_id: string; grow: string; schedule: string; mode: string }[];
  profile?: [number, number][];
}

export interface TaskView {
  id: string;
  title: string;
  note: string;
  task_type: string;
  due: string;
  overdue: boolean;
  done: boolean;
  every: number;
  custom: boolean;
  /** System upkeep (water changes, cleaning…): belongs to the system, not to a grow. */
  maintenance: boolean;
  grow_id: string | null;
  grow: string | null;
}

export interface StageView {
  id: string;
  name: string;
  type: string;
  number: number;
  count: number;
  days: number;
  outcome: string;
  started: string | null;
  day: number | null;
  days_remaining: number | null;
  progress: number | null;
}

/** One running plan. A system can run several at once. */
export interface GrowView {
  id: string;
  name: string;
  active: boolean;
  plan: { id: string; name: string; harvest_style: HarvestStyle } | null;
  stage: StageView | null;
  stages: { id: string; name: string; type: string; days: number; outcome: string }[];
  grow_day: number | null;
  grow_started: string | null;
  expected_end: string | null;
  night_lighting: boolean;
}

/** "once": harvest everything and start over. "continuous": keep it growing, harvest a little at a time. */
export type HarvestStyle = "once" | "continuous";

/** A repeating job for the system itself (not for a plan): changing the water, cleaning, calibrating. */
export interface MaintenanceTask {
  id: string;
  title: string;
  note: string;
  task_type: string;
  /** Repeats this many days after the system started running, or after it was last done. */
  every: number;
  enabled: boolean;
  /** Doing this also does these (by id), so their clocks restart. */
  covers: string[];
}

export interface MaintenanceView extends MaintenanceTask {
  last_done: string | null;
  days_since: number | null;
  next_due: string | null;
}

export interface Snapshot {
  id: string;
  name: string;
  active: boolean;
  grows: GrowView[];
  /** Days the system has been running: counted from the oldest running grow's start. */
  system_day: number | null;
  system_started: string | null;
  maintenance: MaintenanceView[];
  plans: { id: string; name: string }[];
  schedule_enabled: boolean;
  devices: DeviceView[];
  metrics: Record<Metric, MetricView>;
  ec_unit: string;
  last_reading: string | null;
  reading_overdue: boolean | null;
  tasks: TaskView[];
  tasks_due: number;
  activity: { at: string; kind: string; message: string }[];
}

export interface SystemRow {
  id: string;
  name: string;
  active: boolean;
}

export interface DeviceConfig {
  id?: string;
  name: string;
  entity_id: string;
  light: boolean;
}

export interface SystemConfig {
  name: string;
  devices: DeviceConfig[];
  sensors: Record<Metric, string | null>;
  ec_unit: string;
  ec_sensor_unit: string | null;
  reading_interval_days: number;
  reminder_time: string;
  todo_entity: string | null;
  todo_adopt: boolean;
  maintenance: MaintenanceTask[];
}

export interface Schedule {
  mode: string;
  on_time?: string;
  off_time?: string;
  interval_on?: number;
  interval_every?: number;
}

export interface Task {
  id?: string;
  task_type: string;
  title: string;
  days: number[];
  every: number;
  until: number | null;
  method: string;
  note: string;
}

export interface Stage {
  id?: string;
  name: string;
  stage_type: string;
  days: number;
  outcome: string;
  ec_min: number | null;
  ec_max: number | null;
  schedules: Record<string, Schedule>;
  tasks: Task[];
}

export interface Plan {
  name: string;
  ph_min: number | null;
  ph_max: number | null;
  temp_min: number | null;
  temp_max: number | null;
  temp_unit: string | null;
  humidity_min: number | null;
  humidity_max: number | null;
  notes: string;
  harvest_style: HarvestStyle;
  stages: Stage[];
}

export interface TemplateCard {
  id: string;
  name: string;
  builtin: boolean;
  stage_count: number;
  total_days: number;
  stages: { name: string; days: number; type: string }[];
  ph: string | null;
  temperature: string | null;
  temp_unit: string | null;
  humidity: string | null;
  ec: string | null;
  harvest_style: HarvestStyle;
}

export type Template = Plan & { id: string; builtin?: boolean };

export interface EntityRow {
  entity_id: string;
  name: string;
  state: string;
  unit: string | null;
}

export interface FieldError {
  path: string;
  message: string;
}

export interface Preview {
  plan: string;
  stage: string;
  stage_number: number;
  stage_count: number;
  stage_started: string;
  stage_day: number;
  stage_days: number;
  grow_started: string;
  expected_end: string;
  stage_check_due: string;
  devices: { name: string; desired: boolean | null; shared_with: string[] }[];
  tasks: { title: string; due: string; overdue: boolean; recurring: boolean }[];
  skipped_tasks: string[];
}

export interface Meta {
  ec_units: string[];
  harvest_styles: HarvestStyle[];
  stage_types: string[];
  task_types: string[];
  schedule_modes: string[];
  roles: Record<string, string>;
  events: { event: string; when: string; example: Record<string, unknown> }[];
  mqtt: boolean;
}

export interface Reading {
  at: string;
  ph: number | null;
  ec: number | null;
}
