// One-page editor for a plan or a custom template. Nothing is saved until Save.

import type { ComponentChildren } from "preact";
import { useEffect, useMemo, useState } from "preact/hooks";

import { ApiError } from "./api";
import { clock } from "./format";
import { setDirty } from "./guard";
import { profile } from "./schedule";
import type { FieldError, Plan, Schedule, Stage, Task } from "./types";
import { fromCanonical, toCanonical } from "./units";
import { ConfirmButton, Field, NumberInput, Segmented, errorAt, useAction } from "./ui";

export interface Slot {
  key: string;
  label: string;
}

interface Props {
  initial: Plan;
  /** The devices (for a plan) or roles (for a template) that can have schedules. */
  slots: Slot[];
  ecUnit: string;
  stageTypes: string[];
  taskTypes: string[];
  onSave: (plan: Plan) => Promise<Plan>;
  onClose?: () => void;
  extra?: ComponentChildren;
  hint?: string;
}

const MODES = [
  { value: "manual", label: "Not managed" },
  { value: "off", label: "Off" },
  { value: "always_on", label: "Always on" },
  { value: "time_window", label: "Time window" },
  { value: "interval", label: "Cycle" },
];

const human = (key: string) => key.replace(/_/g, " ").replace(/^./, (c) => c.toUpperCase());

function blankStage(n: number): Stage {
  return { name: `Stage ${n}`, stage_type: "other", days: 7, outcome: "", ec_min: null, ec_max: null, schedules: {}, tasks: [] };
}

function blankTask(): Task {
  return { task_type: "reminder", title: "", days: [1], every: 0, until: null, method: "", note: "" };
}

const clone = <T,>(value: T): T => JSON.parse(JSON.stringify(value));

export function PlanEditor(props: Props) {
  const [saved, setSaved] = useState<Plan>(() => clone(props.initial));
  const [draft, setDraft] = useState<Plan>(() => clone(props.initial));
  const [errors, setErrors] = useState<FieldError[]>([]);
  const [selected, setSelected] = useState(0);
  const [dragging, setDragging] = useState<number | null>(null);
  const [over, setOver] = useState<number | null>(null);
  const { run, busy } = useAction();

  const dirty = useMemo(() => JSON.stringify(draft) !== JSON.stringify(saved), [draft, saved]);
  useEffect(() => {
    setDirty(dirty);
    return () => setDirty(false);
  }, [dirty]);

  const edit = (mutate: (plan: Plan) => void) => {
    const next = clone(draft);
    mutate(next);
    setDraft(next);
  };
  const stageIndex = Math.min(selected, draft.stages.length - 1);
  const stage = draft.stages[stageIndex];
  const err = (path: string) => errorAt(errors, path);
  const stageHasError = (i: number) => errors.some((e) => e.path.startsWith(`stages[${i}]`));

  // useAction turns a failure into a toast; keep the per-field errors too.
  const doSave = async () => {
    setErrors([]);
    try {
      const plan = await props.onSave(draft);
      setSaved(clone(plan));
      setDraft(clone(plan));
      return true;
    } catch (e) {
      if (e instanceof ApiError && e.fieldErrors.length) setErrors(e.fieldErrors);
      throw e;
    }
  };

  const moveStage = (from: number, to: number) => {
    if (to < 0 || to >= draft.stages.length || from === to) return;
    edit((p) => {
      const [moved] = p.stages.splice(from, 1);
      p.stages.splice(to, 0, moved);
    });
    setSelected(to);
  };

  return (
    <div class="stack">
      <section class="card">
        <div class="cols2">
          <Field label="Name" error={err("name")}>
            <input type="text" value={draft.name} onInput={(e) => edit((p) => (p.name = (e.currentTarget as HTMLInputElement).value))} />
          </Field>
          <Field label="Notes">
            <input type="text" value={draft.notes} onInput={(e) => edit((p) => (p.notes = (e.currentTarget as HTMLInputElement).value))} />
          </Field>
        </div>
        <h3>Targets <span class="muted small">— used for the in/out-of-range alerts</span></h3>
        <div class="grid" style="grid-template-columns:repeat(auto-fit,minmax(220px,1fr))">
          <RangePair label="pH" lo={draft.ph_min} hi={draft.ph_max} step={0.1} errLo={err("ph_min")} errHi={err("ph_max")}
            onChange={(lo, hi) => edit((p) => { p.ph_min = lo; p.ph_max = hi; })} />
          <div class="stack" style="gap:6px">
            <RangePair label={`Temperature (${draft.temp_unit ?? "°C"})`} lo={draft.temp_min} hi={draft.temp_max} errLo={err("temp_min")} errHi={err("temp_max")}
              onChange={(lo, hi) => edit((p) => { p.temp_min = lo; p.temp_max = hi; })} />
            <Segmented label="Temperature unit" value={(draft.temp_unit ?? "°C") as string} options={[{ value: "°C", label: "°C" }, { value: "°F", label: "°F" }]}
              onChange={(v) => edit((p) => (p.temp_unit = v))} />
          </div>
          <RangePair label="Humidity (%)" lo={draft.humidity_min} hi={draft.humidity_max} errLo={err("humidity_min")} errHi={err("humidity_max")}
            onChange={(lo, hi) => edit((p) => { p.humidity_min = lo; p.humidity_max = hi; })} />
        </div>
        {err("stages") ? <span class="error-text">{err("stages")}</span> : null}
      </section>

      <section class="card" aria-label="Stages">
        <div class="stage-tabs" role="tablist">
          {draft.stages.map((s, i) => (
            <button
              key={i}
              role="tab"
              class={`stage-tab ${over === i && dragging !== i ? "dragover" : ""}`}
              aria-selected={i === stageIndex}
              draggable
              onDragStart={() => setDragging(i)}
              onDragOver={(e) => { e.preventDefault(); setOver(i); }}
              onDragEnd={() => { setDragging(null); setOver(null); }}
              onDrop={() => { if (dragging !== null) moveStage(dragging, i); setDragging(null); setOver(null); }}
              onClick={() => setSelected(i)}
            >
              {i + 1}. {s.name || "Untitled"}
              <span class="muted small">{s.days}d</span>
              {stageHasError(i) ? <span class="badge bad">!</span> : null}
            </button>
          ))}
          <button class="btn small" onClick={() => { edit((p) => p.stages.push(blankStage(p.stages.length + 1))); setSelected(draft.stages.length); }}>+ Add stage</button>
        </div>

        {stage ? (
          <StageForm
            key={stageIndex}
            index={stageIndex}
            stage={stage}
            stages={draft.stages}
            slots={props.slots}
            ecUnit={props.ecUnit}
            stageTypes={props.stageTypes}
            taskTypes={props.taskTypes}
            err={err}
            edit={(mutate) => edit((p) => mutate(p.stages[stageIndex]))}
            toolbar={
              <div class="row wrap">
                <button class="btn small" disabled={stageIndex === 0} onClick={() => moveStage(stageIndex, stageIndex - 1)} aria-label="Move stage earlier">◀ Earlier</button>
                <button class="btn small" disabled={stageIndex === draft.stages.length - 1} onClick={() => moveStage(stageIndex, stageIndex + 1)} aria-label="Move stage later">Later ▶</button>
                <button class="btn small" onClick={() => { edit((p) => p.stages.splice(stageIndex + 1, 0, { ...clone(p.stages[stageIndex]), id: undefined, name: `${p.stages[stageIndex].name} (copy)` })); setSelected(stageIndex + 1); }}>Duplicate</button>
                <ConfirmButton label="Delete stage" class="small danger" question={`Delete “${stage.name}” and its tasks?`} confirmLabel="Delete" disabled={draft.stages.length === 1}
                  onConfirm={() => { edit((p) => p.stages.splice(stageIndex, 1)); setSelected(Math.max(0, stageIndex - 1)); }} />
              </div>
            }
          />
        ) : null}
      </section>

      <div class="save-bar">
        <span class="grow muted small">{dirty ? "Unsaved changes" : "All changes saved"}{props.hint ? ` · ${props.hint}` : ""}</span>
        {props.extra}
        <button class="btn" disabled={!dirty || busy} onClick={() => { setDraft(clone(saved)); setErrors([]); }}>Discard</button>
        <button class="btn primary" disabled={!dirty || busy} onClick={() => run(doSave, "Saved")}>Save</button>
        {props.onClose ? <button class="btn" onClick={props.onClose}>Close</button> : null}
      </div>
    </div>
  );
}

function RangePair(props: {
  label: string;
  lo: number | null;
  hi: number | null;
  step?: number;
  errLo?: string;
  errHi?: string;
  onChange: (lo: number | null, hi: number | null) => void;
}) {
  return (
    <div class="stack" style="gap:4px">
      <span class="small muted" style="font-weight:550">{props.label}</span>
      <div class="cols2">
        <Field label="Min" error={props.errLo}><NumberInput value={props.lo} step={props.step} onChange={(v) => props.onChange(v, props.hi)} ariaLabel={`${props.label} min`} /></Field>
        <Field label="Max" error={props.errHi}><NumberInput value={props.hi} step={props.step} onChange={(v) => props.onChange(props.lo, v)} ariaLabel={`${props.label} max`} /></Field>
      </div>
    </div>
  );
}

function StageForm(props: {
  index: number;
  stage: Stage;
  stages: Stage[];
  slots: Slot[];
  ecUnit: string;
  stageTypes: string[];
  taskTypes: string[];
  err: (path: string) => string | undefined;
  edit: (mutate: (stage: Stage) => void) => void;
  toolbar: ComponentChildren;
}) {
  const { stage, err, edit, index } = props;
  const base = `stages[${index}]`;
  const others = props.stages.map((s, i) => ({ s, i })).filter(({ i }) => i !== index);
  const ec = (v: number | null) => fromCanonical(v, props.ecUnit);
  return (
    <div class="stack">
      {props.toolbar}
      <div class="grid" style="grid-template-columns:repeat(auto-fit,minmax(180px,1fr))">
        <Field label="Stage name" error={err(`${base}.name`)}>
          <input type="text" value={stage.name} onInput={(e) => edit((s) => (s.name = (e.currentTarget as HTMLInputElement).value))} />
        </Field>
        <Field label="Type" error={err(`${base}.stage_type`)}>
          <select value={stage.stage_type} onChange={(e) => edit((s) => (s.stage_type = (e.currentTarget as HTMLSelectElement).value))}>
            {props.stageTypes.map((t) => <option value={t} key={t}>{human(t)}</option>)}
          </select>
        </Field>
        <Field label="Planned days" error={err(`${base}.days`)}>
          <NumberInput value={stage.days} step={1} min={1} onChange={(v) => edit((s) => (s.days = v ?? 0))} ariaLabel="Planned days" />
        </Field>
        <Field label={`EC min (${props.ecUnit})`} error={err(`${base}.ec_min`)} hint={props.ecUnit !== "mS/cm" && stage.ec_min !== null ? `${stage.ec_min.toFixed(2)} mS/cm` : undefined}>
          <NumberInput value={ec(stage.ec_min)} onChange={(v) => edit((s) => (s.ec_min = toCanonical(v, props.ecUnit)))} ariaLabel="EC min" />
        </Field>
        <Field label={`EC max (${props.ecUnit})`} error={err(`${base}.ec_max`)} hint={props.ecUnit !== "mS/cm" && stage.ec_max !== null ? `${stage.ec_max.toFixed(2)} mS/cm` : undefined}>
          <NumberInput value={ec(stage.ec_max)} onChange={(v) => edit((s) => (s.ec_max = toCanonical(v, props.ecUnit)))} ariaLabel="EC max" />
        </Field>
      </div>
      <Field label="Expected outcome (shown when it's time to check if the stage is done)">
        <input type="text" value={stage.outcome} onInput={(e) => edit((s) => (s.outcome = (e.currentTarget as HTMLInputElement).value))} />
      </Field>

      <div class="row between wrap">
        <h3>Schedules</h3>
        {others.length ? (
          <select aria-label="Copy schedules from another stage" style="width:auto" value=""
            onChange={(e) => {
              const from = props.stages[Number((e.currentTarget as HTMLSelectElement).value)];
              if (from) edit((s) => (s.schedules = clone(from.schedules)));
              (e.currentTarget as HTMLSelectElement).value = "";
            }}>
            <option value="">Copy from stage…</option>
            {others.map(({ s, i }) => <option value={i} key={i}>{i + 1}. {s.name}</option>)}
          </select>
        ) : null}
      </div>
      {props.slots.length === 0 ? <p class="muted small">Add devices under Settings to schedule them.</p> : null}
      {props.slots.map((slot) => (
        <ScheduleRow key={slot.key} label={slot.label} value={stage.schedules[slot.key] ?? { mode: "manual" }}
          err={(f) => err(`${base}.schedules.${slot.key}.${f}`)}
          onChange={(next) => edit((s) => (s.schedules[slot.key] = next))} />
      ))}

      <div class="row between wrap">
        <h3>Tasks</h3>
        <button class="btn small" onClick={() => edit((s) => s.tasks.push(blankTask()))}>+ Add task</button>
      </div>
      {stage.tasks.length === 0 ? <p class="muted small">No tasks in this stage.</p> : null}
      {stage.tasks.map((t, j) => (
        <TaskEditor key={j} task={t} taskTypes={props.taskTypes} err={(f) => err(`${base}.tasks[${j}].${f}`)}
          onChange={(next) => edit((s) => (s.tasks[j] = next))}
          onDuplicate={() => edit((s) => s.tasks.splice(j + 1, 0, { ...clone(t), id: undefined }))}
          onDelete={() => edit((s) => s.tasks.splice(j, 1))} />
      ))}
    </div>
  );
}

function DayBar({ schedule }: { schedule: Schedule }) {
  const windows = profile(schedule);
  return (
    <div>
      <div class="daybar" role="img" aria-label="24-hour preview">
        {windows.map(([a, b], i) => <i key={i} style={`left:${(a / 1440) * 100}%;width:${((b - a) / 1440) * 100}%`} />)}
      </div>
      <div class="dayscale"><span>0</span><span>6</span><span>12</span><span>18</span><span>24</span></div>
    </div>
  );
}

function ScheduleRow(props: { label: string; value: Schedule; err: (field: string) => string | undefined; onChange: (s: Schedule) => void }) {
  const s = props.value;
  const set = (patch: Partial<Schedule>) => props.onChange({ ...s, ...patch });
  const setMode = (mode: string) => {
    const next: Schedule = { mode };
    if (mode === "time_window") Object.assign(next, { on_time: s.on_time ?? "06:00:00", off_time: s.off_time ?? "22:00:00" });
    if (mode === "interval") Object.assign(next, { interval_on: s.interval_on ?? 900, interval_every: s.interval_every ?? 10800 });
    props.onChange(next);
  };
  const first = windowsSummary(s);
  return (
    <div class="task-edit">
      <div class="row between wrap">
        <strong>{props.label}</strong>
        <Segmented label={`${props.label} mode`} value={s.mode} options={MODES} onChange={setMode} />
      </div>
      {s.mode === "time_window" ? (
        <div class="cols2">
          <Field label="On at" error={props.err("on_time")}>
            <input type="time" value={(s.on_time ?? "").slice(0, 5)} onInput={(e) => set({ on_time: (e.currentTarget as HTMLInputElement).value })} />
          </Field>
          <Field label="Off at" error={props.err("off_time")}>
            <input type="time" value={(s.off_time ?? "").slice(0, 5)} onInput={(e) => set({ off_time: (e.currentTarget as HTMLInputElement).value })} />
          </Field>
        </div>
      ) : null}
      {s.mode === "interval" ? (
        <div class="cols2">
          <Field label="On for (minutes)" error={props.err("interval_on")}>
            <NumberInput value={(s.interval_on ?? 0) / 60} min={0} onChange={(v) => set({ interval_on: Math.round((v ?? 0) * 60) })} ariaLabel="On for minutes" />
          </Field>
          <Field label="Every (minutes)" error={props.err("interval_every")} hint={s.interval_every ? `= ${(s.interval_every / 3600).toFixed(2).replace(/\.?0+$/, "")} h` : undefined}>
            <NumberInput value={(s.interval_every ?? 0) / 60} min={0} onChange={(v) => set({ interval_every: Math.round((v ?? 0) * 60) })} ariaLabel="Every minutes" />
          </Field>
        </div>
      ) : null}
      {s.mode !== "manual" ? <DayBar schedule={s} /> : <p class="muted small">Left alone — the app won't switch this device in this stage.</p>}
      {first ? <p class="muted small">{first}</p> : null}
    </div>
  );
}

function windowsSummary(s: Schedule): string {
  const w = profile(s);
  if (s.mode === "interval" && w.length) return `${w.length} runs a day`;
  if (s.mode === "time_window" && w.length === 2) return `Runs overnight: ${clock(w[1][0])} to ${clock(w[0][1])}`;
  return "";
}

function TaskEditor(props: {
  task: Task;
  taskTypes: string[];
  err: (field: string) => string | undefined;
  onChange: (t: Task) => void;
  onDuplicate: () => void;
  onDelete: () => void;
}) {
  const t = props.task;
  const set = (patch: Partial<Task>) => props.onChange({ ...t, ...patch });
  const repeats = t.every > 0;
  const extras = t.days.slice(1).join(", ");
  const [extraText, setExtraText] = useState(extras);
  return (
    <div class="task-edit">
      <div class="row wrap">
        <div class="grow" style="min-width:200px">
          <Field label="Title" error={props.err("title")}>
            <input type="text" value={t.title} onInput={(e) => set({ title: (e.currentTarget as HTMLInputElement).value })} />
          </Field>
        </div>
        <div style="width:150px">
          <Field label="Type" error={props.err("task_type")}>
            <select value={t.task_type} onChange={(e) => set({ task_type: (e.currentTarget as HTMLSelectElement).value })}>
              {props.taskTypes.map((x) => <option value={x} key={x}>{human(x)}</option>)}
            </select>
          </Field>
        </div>
        <div style="width:110px">
          <Field label={repeats ? "First day" : "Day"} error={props.err("days")}>
            <NumberInput value={t.days[0] ?? 1} step={1} min={1} onChange={(v) => set({ days: [v ?? 1, ...t.days.slice(1)] })} ariaLabel="Day" />
          </Field>
        </div>
      </div>
      <div class="row wrap">
        <label class="check">
          <input type="checkbox" checked={repeats} onChange={(e) => set({ every: (e.currentTarget as HTMLInputElement).checked ? 3 : 0, until: null, days: [t.days[0] ?? 1] })} />
          Repeat
        </label>
        {repeats ? (
          <>
            <span class="row small">every <span style="width:70px"><NumberInput value={t.every} step={1} min={1} onChange={(v) => set({ every: v ?? 0 })} ariaLabel="Repeat every N days" /></span> days after it's checked off</span>
            <span class="row small muted">stop after day <span style="width:70px"><NumberInput value={t.until} step={1} min={1} placeholder="never" onChange={(v) => set({ until: v })} ariaLabel="Stop after day" /></span></span>
            {props.err("every") || props.err("until") ? <span class="error-text">{props.err("every") ?? props.err("until")}</span> : null}
          </>
        ) : (
          <label class="row small muted">also on days
            <input type="text" style="width:120px" placeholder="e.g. 9, 14" value={extraText}
              onInput={(e) => {
                const text = (e.currentTarget as HTMLInputElement).value;
                setExtraText(text);
                const more = text.split(/[,;\s]+/).filter(Boolean).map(Number).filter((n) => Number.isInteger(n) && n > 0);
                set({ days: [t.days[0] ?? 1, ...more] });
              }} />
          </label>
        )}
        <span class="grow" />
        <button class="btn small" onClick={props.onDuplicate}>Duplicate</button>
        <button class="btn small danger" onClick={props.onDelete}>Remove</button>
      </div>
      <details open={Boolean(t.note || t.method)}>
        <summary class="muted small">Note and method</summary>
        <div class="stack" style="margin-top:8px">
          <Field label="Method"><input type="text" value={t.method} onInput={(e) => set({ method: (e.currentTarget as HTMLInputElement).value })} /></Field>
          <Field label="Note"><textarea value={t.note} onInput={(e) => set({ note: (e.currentTarget as HTMLTextAreaElement).value })} /></Field>
        </div>
      </details>
    </div>
  );
}
