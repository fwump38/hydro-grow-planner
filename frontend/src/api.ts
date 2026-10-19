// Typed client for the backend. URLs are relative so the panel works under any
// Home Assistant ingress path.

import type {
  EntityRow,
  FieldError,
  Meta,
  Plan,
  Preview,
  Reading,
  Snapshot,
  SystemConfig,
  SystemRow,
  Template,
  TemplateCard,
} from "./types";

export class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
    public fieldErrors: FieldError[] = [],
  ) {
    super(message);
  }
}

async function request<T>(method: string, path: string, body?: unknown): Promise<T> {
  const response = await fetch(`api/${path}`, {
    method,
    headers: body === undefined ? undefined : { "Content-Type": "application/json" },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    const errors: FieldError[] = data.errors ?? [];
    const message = data.error ?? (errors.length ? "Fix the highlighted fields" : response.statusText);
    throw new ApiError(message, response.status, errors);
  }
  return data as T;
}

const get = <T>(path: string) => request<T>("GET", path);
const post = <T>(path: string, body: unknown = {}) => request<T>("POST", path, body);
const put = <T>(path: string, body: unknown) => request<T>("PUT", path, body);
const patch = <T>(path: string, body: unknown) => request<T>("PATCH", path, body);
const del = <T>(path: string) => request<T>("DELETE", path);

export interface StartArgs {
  template?: string;
  /** Zones (ids) whose lights run this grow; the pump is added automatically. */
  zones?: string[];
  /** Label for the new grow, e.g. "Layers 1+2". */
  name?: string;
  /** Replace this grow (id) instead of adding another. */
  replace?: string;
  stage?: string | number;
  stage_started?: string;
  grow_started?: string;
  include_past_tasks?: boolean;
  night_lighting?: boolean;
  /** With `replace`: keep counting the grow from the replaced grow's start date. */
  keep_grow_start?: boolean;
}

export const api = {
  meta: () => get<Meta>("meta"),
  entities: (domains: string[]) => get<EntityRow[]>(`ha/entities?domains=${domains.join(",")}`),
  systems: () => get<SystemRow[]>("systems"),
  createSystem: (name: string) => post<Snapshot>("systems", { name }),
  deleteSystem: (id: string) => del<unknown>(`systems/${id}`),
  system: (id: string) => get<Snapshot>(`systems/${id}`),
  config: (id: string) => get<SystemConfig>(`systems/${id}/config`),
  saveConfig: (id: string, config: Partial<SystemConfig>) =>
    patch<Snapshot>(`systems/${id}/config`, config),

  switchDevice: (id: string, device: string, on: boolean) =>
    post<Snapshot>(`systems/${id}/devices/${device}/switch`, { on }),
  scheduleControl: (id: string, enabled: boolean) =>
    post<Snapshot>(`systems/${id}/schedule-control`, { enabled }),
  sync: (id: string) => post<Snapshot>(`systems/${id}/sync`),

  record: (id: string, reading: { ph?: number | null; ec?: number | null }) =>
    post<Snapshot>(`systems/${id}/readings`, reading),
  waterChecked: (id: string) => post<Snapshot>(`systems/${id}/water-checked`),
  readings: (id: string, days = 14) =>
    get<{ ec_unit: string; readings: Reading[] }>(`systems/${id}/readings?days=${days}`),

  previewStart: (id: string, args: StartArgs) => post<Preview>(`systems/${id}/grows/preview`, args),
  startGrow: (id: string, args: StartArgs) => post<Snapshot>(`systems/${id}/grows`, args),
  endGrow: (id: string, grow: string) => del<Snapshot>(`systems/${id}/grows/${grow}`),
  updateGrow: (id: string, grow: string, changes: { name?: string; night_lighting?: boolean }) =>
    patch<Snapshot>(`systems/${id}/grows/${grow}`, changes),
  stageAction: (id: string, grow: string, action: "advance" | "previous" | "restart") =>
    post<Snapshot>(`systems/${id}/grows/${grow}/stage/${action}`),

  addTask: (
    id: string,
    task: { title: string; due?: string; note?: string; every?: number; grow?: string },
  ) => post<Snapshot>(`systems/${id}/tasks`, task),
  completeTask: (id: string, task: string) => post<Snapshot>(`systems/${id}/tasks/${task}/complete`),
  reopenTask: (id: string, task: string) => post<Snapshot>(`systems/${id}/tasks/${task}/reopen`),
  deleteTask: (id: string, task: string) => del<Snapshot>(`systems/${id}/tasks/${task}`),

  growPlan: (id: string, grow: string) => get<Plan>(`systems/${id}/grows/${grow}/plan`),
  saveGrowPlan: (id: string, grow: string, data: Plan) =>
    put<{ plan: Plan }>(`systems/${id}/grows/${grow}/plan`, data),

  templates: () => get<TemplateCard[]>("templates"),
  template: (id: string) => get<Template>(`templates/${id}`),
  duplicateTemplate: (id: string) => post<Template>("templates", { duplicate: id }),
  importTemplate: (template: unknown) => post<Template>("templates", { template }),
  templateFromGrow: (spec: { system_id: string; grow_id: string; name?: string }) =>
    post<Template>("templates", { from_grow: spec, name: spec.name }),
  saveTemplate: (id: string, data: Plan) => put<Template>(`templates/${id}`, data),
  deleteTemplate: (id: string) => del<unknown>(`templates/${id}`),

  testEvent: (event: string) => post<unknown>("events/test", { event }),
};

/** Call `onChange` whenever the backend says something changed (reconnects itself). */
export function watch(onChange: (message: { type: string; system_id: string }) => void): () => void {
  const source = new EventSource("api/stream");
  source.onmessage = (event) => onChange(JSON.parse(event.data));
  return () => source.close();
}
