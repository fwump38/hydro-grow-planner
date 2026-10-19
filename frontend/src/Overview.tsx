import { useEffect, useState } from "preact/hooks";

import { api } from "./api";
import { addDays, clock, dayLabel, num, shortDate, today, until } from "./format";
import type { DeviceView, GrowView, Metric, MetricView, Reading, Snapshot, StageView, TaskView } from "./types";
import { Badge, ConfirmButton, Field, NumberInput, Switch, useAction } from "./ui";

interface Props {
  snap: Snapshot;
  onSnap: (snap: Snapshot) => void;
  /** Open the wizard: to add a grow, or (with a grow id) to change that one. */
  onStart: (replace?: string) => void;
  /** Open a grow's own plan for editing. */
  onEditPlan: (grow: string) => void;
}

export function Overview({ snap, onSnap, onStart, onEditPlan }: Props) {
  const growing = snap.grows.filter((g) => g.stage);
  if (!snap.active || growing.length === 0) {
    return (
      <div class="card empty">
        <h2>No grow running</h2>
        <p class="muted">
          Pick a template, choose the stage you're at and when it started, and the schedules and
          tasks follow from there.
        </p>
        <button class="btn primary" onClick={() => onStart()}>Start a grow</button>
        {snap.devices.length === 0 ? (
          <p class="muted small">Tip: add your lights and pump under Settings first.</p>
        ) : null}
      </div>
    );
  }
  return (
    <>
      {growing.map((g) => (
        <StageCard key={g.id} snap={snap} grow={g} stage={g.stage as StageView} onSnap={onSnap} onStart={onStart} onEditPlan={onEditPlan} />
      ))}
      <div class="row">
        <button class="btn" onClick={() => onStart()}>Add a grow…</button>
        <span class="muted small">
          {snap.system_day ? `System day ${snap.system_day}. ` : ""}
          {growing.length > 1 ? "Grows share the reservoir, pump and room; each has its own lights, stage and tasks." : "Run another grow alongside, e.g. on a second set of layers."}
        </span>
      </div>
      <div class="grid wide">
        <DevicesCard snap={snap} onSnap={onSnap} />
        <WaterCard snap={snap} onSnap={onSnap} />
      </div>
      <TasksCard snap={snap} onSnap={onSnap} />
    </>
  );
}

// -- stage ---------------------------------------------------------------------------------

function StageCard({ snap, grow, stage, onSnap, onStart, onEditPlan }: Props & { grow: GrowView; stage: StageView }) {
  const { run, busy } = useAction();
  const act = (a: "advance" | "previous" | "restart") => run(() => api.stageAction(snap.id, grow.id, a)).then((s) => s && onSnap(s));
  const next = grow.stages[stage.number];
  const overdue = (stage.day ?? 0) >= stage.days;
  return (
    <section class="card" aria-label={`Current stage of ${grow.name}`}>
      <div class="row wrap between">
        <div>
          <h2>{grow.name}</h2>
          <p class="muted small">
            {grow.plan && grow.plan.name !== grow.name ? `${grow.plan.name} · ` : ""}
            Stage {stage.number} of {stage.count} · grow day {grow.grow_day} · started{" "}
            {shortDate(grow.grow_started)} · expected end {shortDate(grow.expected_end)}
          </p>
        </div>
        <div class="row">
          <button class="btn" onClick={() => onEditPlan(grow.id)}>Edit plan…</button>
          <button class="btn" onClick={() => onStart(grow.id)}>Change…</button>
          <ConfirmButton
            label="End grow"
            class="danger"
            confirmLabel="End grow"
            question={`End ${grow.name}? Its tasks are removed and its devices are left as they are.`}
            disabled={busy}
            onConfirm={() => run(() => api.endGrow(snap.id, grow.id), "Grow ended").then((s) => s && onSnap(s))}
          />
        </div>
      </div>
      <div class="timeline" role="list">
        {grow.stages.map((s, i) => {
          const state = i + 1 < stage.number ? "done" : i + 1 === stage.number ? "current" : "";
          const pct = state === "current" ? stage.progress ?? 0 : 0;
          return (
            <div role="listitem" class={`seg-stage ${state}`} style={`flex:${Math.max(s.days, 3)}`} key={s.id}>
              <div class="bar"><i style={state === "current" ? `width:${pct}%` : ""} /></div>
              <div class="nm" title={`${s.name} · ${s.days} days`}>{s.name}</div>
            </div>
          );
        })}
      </div>
      <div class="row wrap">
        <strong>{stage.name}</strong>
        <Badge kind="accent">day {stage.day} of {stage.days}</Badge>
        {stage.days_remaining ? <span class="muted small">{stage.days_remaining} days left</span> : null}
      </div>
      {stage.outcome ? <p class="muted small">Goal: {stage.outcome}</p> : null}
      {overdue ? (
        <div class="callout" role="status">
          <strong>This stage's planned time is up.</strong>
          <span>
            {next ? `Ready for ${next.name}? Check: ${stage.outcome || "the plants look ready"}.` : "Ready to finish the grow?"}
            {" "}Nothing changes until you say so.
          </span>
          {next ? (
            <div><button class="btn primary" disabled={busy} onClick={() => act("advance")}>Move to {next.name}</button></div>
          ) : null}
        </div>
      ) : null}
      <div class="row wrap">
        <ConfirmButton label="Previous stage" question="Go back to the previous stage?" disabled={busy || stage.number === 1} onConfirm={() => act("previous")} />
        <ConfirmButton label="Next stage" question={next ? `Move on to ${next.name}?` : ""} disabled={busy || !next} onConfirm={() => act("advance")} class={overdue ? "" : ""} />
        <ConfirmButton label="Restart stage" question="Restart this stage from day 1 (today)?" disabled={busy} onConfirm={() => act("restart")} />
        <span class="grow" />
        <label class="row small"><Switch label={`Night lighting for ${grow.name}`} checked={grow.night_lighting} onChange={(v) => run(() => api.updateGrow(snap.id, grow.id, { night_lighting: v })).then((s) => s && onSnap(s))} /> Night lighting</label>
      </div>
    </section>
  );
}

// -- devices -------------------------------------------------------------------------------

function nowMinutes(): number {
  const d = new Date();
  return d.getHours() * 60 + d.getMinutes();
}

function DayBar({ profile }: { profile: [number, number][] }) {
  const now = nowMinutes();
  return (
    <div>
      <div class="daybar" role="img" aria-label="Scheduled on-times today">
        {profile.map(([a, b]) => (
          <i key={a} style={`left:${(a / 1440) * 100}%;width:${((b - a) / 1440) * 100}%`} />
        ))}
        <b style={`left:${(now / 1440) * 100}%`} />
      </div>
      <div class="dayscale"><span>0</span><span>6</span><span>12</span><span>18</span><span>24</span></div>
    </div>
  );
}

function DevicesCard({ snap, onSnap }: { snap: Snapshot; onSnap: (s: Snapshot) => void }) {
  const { run, busy } = useAction();
  if (!snap.devices.length) {
    return (
      <section class="card">
        <h2>Devices</h2>
        <p class="muted">No devices yet. Add your lights and pump under Settings.</p>
      </section>
    );
  }
  return (
    <section class="card" aria-label="Devices">
      <div class="row between wrap">
        <h2>Devices</h2>
        <div class="row">
          <label class="row small"><Switch label="Schedule control" checked={snap.schedule_enabled} onChange={(v) => run(() => api.scheduleControl(snap.id, v)).then((s) => s && onSnap(s))} /> Schedule control</label>
          <button class="btn small" disabled={busy} onClick={() => run(() => api.sync(snap.id), "Devices synced").then((s) => s && onSnap(s))}>Sync now</button>
        </div>
      </div>
      {snap.devices.map((d) => (
        <Device key={d.id} d={d} busy={busy} manyGrows={snap.grows.length > 1} onToggle={(on) => run(() => api.switchDevice(snap.id, d.id, on)).then((s) => s && onSnap(s))} />
      ))}
    </section>
  );
}

function Device({ d, busy, manyGrows, onToggle }: { d: DeviceView; busy: boolean; manyGrows: boolean; onToggle: (on: boolean) => void }) {
  const next = until(d.next_change);
  return (
    <div class="stack" style="gap:6px">
      <div class="row">
        <div class="grow">
          <strong>{d.name}</strong>
          <div class="muted small">
            {d.drivers.length > 1 ? "Not managed" : d.schedule ?? "Not managed"}
            {d.drivers.length === 1 && manyGrows ? ` · ${d.drivers[0].grow}` : ""}
            {next && d.desired !== null ? ` · ${d.desired ? "off" : "on"} in ${next}` : ""}
          </div>
          {d.drivers.length > 1 ? (
            <div class="muted small">
              {d.drivers.map((x) => `${x.grow}: ${x.schedule}`).join(" · ")} — on whenever any of them wants it on
            </div>
          ) : null}
        </div>
        {d.override ? <Badge kind="warn">manual override</Badge> : null}
        {d.state === null ? <Badge>unavailable</Badge> : null}
        <Switch label={`${d.name} power`} checked={d.state === true} disabled={busy || d.state === null} onChange={onToggle} />
      </div>
      {d.profile && d.mode && d.mode !== "manual" ? <DayBar profile={d.profile} /> : null}
    </div>
  );
}

// -- water and climate ---------------------------------------------------------------------------

const LABELS: Record<Metric, string> = { ph: "pH", ec: "EC", temperature: "Temperature", humidity: "Humidity" };

function Band({ m }: { m: MetricView }) {
  if (m.value === null || m.min === null || m.max === null) return null;
  const span = Math.max(m.max - m.min, 0.0001);
  const lo = m.min - span * 0.8;
  const hi = m.max + span * 0.8;
  const pos = (v: number) => Math.min(100, Math.max(0, ((v - lo) / (hi - lo)) * 100));
  return (
    <div class="band" aria-hidden="true">
      <div class="target" style={`left:${pos(m.min)}%;width:${pos(m.max) - pos(m.min)}%`} />
      <div class={`dot ${m.out_of_range ? "bad" : ""}`} style={`left:${pos(m.value)}%`} />
    </div>
  );
}

function MetricTile({ metric, m, oldest }: { metric: Metric; m: MetricView; oldest?: string }) {
  return (
    <div class="metric">
      <div class="row between">
        <span class="muted small">{LABELS[metric]}</span>
        {m.conflict ? <Badge kind="warn">grows disagree</Badge> : null}
        {m.out_of_range === true ? <Badge kind="bad">out of range</Badge> : m.out_of_range === false ? <Badge kind="ok">in range</Badge> : null}
      </div>
      <div class="value">{m.value === null ? "—" : num(m.value, 2)}<span class="muted small"> {m.unit ?? ""}</span></div>
      <Band m={m} />
      <div class="muted small">{m.range ? `Target ${m.range}${m.unit ? " " + m.unit : ""}` : "No target range"}</div>
      {m.conflict ? <div class="muted small">The grows' ranges don't overlap; showing {oldest}'s.</div> : null}
    </div>
  );
}

function Spark({ points, label }: { points: number[]; label: string }) {
  if (points.length < 2) return null;
  const lo = Math.min(...points);
  const hi = Math.max(...points);
  const span = hi - lo || 1;
  const d = points.map((v, i) => `${i ? "L" : "M"}${(i / (points.length - 1)) * 100},${44 - ((v - lo) / span) * 40}`).join(" ");
  return (
    <svg class="spark" viewBox="0 0 100 48" preserveAspectRatio="none" role="img" aria-label={label}>
      <path d={d} fill="none" stroke="var(--accent)" stroke-width="1.5" vector-effect="non-scaling-stroke" />
    </svg>
  );
}

function WaterCard({ snap, onSnap }: { snap: Snapshot; onSnap: (s: Snapshot) => void }) {
  const { run, busy } = useAction();
  const [ph, setPh] = useState<number | null>(null);
  const [ec, setEc] = useState<number | null>(null);
  const [readings, setReadings] = useState<Reading[]>([]);
  const m = snap.metrics;
  useEffect(() => {
    api.readings(snap.id).then((r) => setReadings(r.readings)).catch(() => {});
  }, [snap.id, snap.last_reading, snap.ec_unit]);

  const manualPh = !m.ph.from_sensor;
  const manualEc = !m.ec.from_sensor;
  const record = async () => {
    const result = await run(() => api.record(snap.id, { ph, ec }), "Reading recorded");
    if (result) {
      onSnap(result);
      setPh(null);
      setEc(null);
    }
  };
  const phs = readings.flatMap((r) => (r.ph === null ? [] : [r.ph]));
  const ecs = readings.flatMap((r) => (r.ec === null ? [] : [r.ec]));
  return (
    <section class="card" aria-label="Water and climate">
      <h2>Water &amp; climate</h2>
      {snap.grows.length > 1 ? <p class="muted small">One reservoir and room for all grows. Targets are where their ranges overlap.</p> : null}
      <div class="cols2">
        {(["ph", "ec", "temperature", "humidity"] as Metric[]).map((k) => (
          <MetricTile key={k} metric={k} m={m[k]} oldest={snap.grows[0]?.name} />
        ))}
      </div>
      {phs.length > 1 || ecs.length > 1 ? (
        <div class="cols2">
          <div><div class="muted small">pH, last 14 days</div><Spark points={phs} label="pH history" /></div>
          <div><div class="muted small">EC, last 14 days</div><Spark points={ecs} label="EC history" /></div>
        </div>
      ) : null}
      {manualPh || manualEc ? (
        <form
          class="stack"
          onSubmit={(e) => {
            e.preventDefault();
            record();
          }}
        >
          <div class="cols2">
            {manualPh ? (
              <Field label="pH">
                <NumberInput value={ph} onChange={setPh} step="0.01" min={0} max={14} placeholder={m.ph.value === null ? "e.g. 6.00" : String(m.ph.value)} ariaLabel="pH value" />
              </Field>
            ) : null}
            {manualEc ? (
              <Field label={`EC (${snap.ec_unit})`} hint={m.ec.range ? `Target ${m.ec.range}` : undefined}>
                <NumberInput value={ec} onChange={setEc} min={0} placeholder={m.ec.value === null ? "" : String(m.ec.value)} ariaLabel="EC value" />
              </Field>
            ) : null}
          </div>
          <div class="row wrap">
            <button class="btn primary" type="submit" disabled={busy || (ph === null && ec === null)}>Record</button>
            <button class="btn" type="button" disabled={busy} onClick={() => run(() => api.waterChecked(snap.id), "Marked as checked").then((s) => s && onSnap(s))}>Water checked</button>
            <span class="grow" />
            <span class="muted small">
              {snap.last_reading ? `Last: ${dayLabel(snap.last_reading.slice(0, 10))}` : "No readings yet"}
            </span>
            {snap.reading_overdue ? <Badge kind="warn">reading overdue</Badge> : null}
          </div>
        </form>
      ) : null}
    </section>
  );
}

// -- tasks ---------------------------------------------------------------------------------------

function TaskRow({ t, tagged, onToggle, onDelete }: { t: TaskView; tagged: boolean; onToggle: () => void; onDelete: () => void }) {
  return (
    <div class={`task ${t.done ? "done" : ""}`}>
      <input type="checkbox" checked={t.done} onChange={onToggle} aria-label={`${t.done ? "Reopen" : "Complete"} ${t.title}`} />
      <div class="grow">
        <div class="row wrap" style="gap:6px">
          {t.maintenance ? <Badge>system</Badge> : tagged && t.grow ? <Badge kind="accent">{t.grow}</Badge> : null}
          <span class="title">{t.title}</span>
          {t.every ? <Badge>every {t.every} {t.every === 1 ? "day" : "days"}</Badge> : null}
          {t.overdue ? <Badge kind="bad">overdue</Badge> : null}
        </div>
        <div class="muted small">{dayLabel(t.due)}</div>
        {t.note && !t.done ? <details class="small"><summary class="muted">Details</summary><div class="note">{t.note}</div></details> : null}
      </div>
      <button class="icon-btn" aria-label={`${t.maintenance ? "Skip" : "Delete"} ${t.title}`} title={t.maintenance ? "Skip this time" : "Delete"} onClick={onDelete}>✕</button>
    </div>
  );
}

function TasksCard({ snap, onSnap }: { snap: Snapshot; onSnap: (s: Snapshot) => void }) {
  const { run, busy } = useAction();
  const [title, setTitle] = useState("");
  const [every, setEvery] = useState<number | null>(null);
  const [forGrow, setForGrow] = useState("");
  const tagged = snap.grows.length > 1;
  const [showDone, setShowDone] = useState(false);
  const t0 = today();
  const open = snap.tasks.filter((t) => !t.done);
  const groups: [string, TaskView[]][] = [
    ["Overdue", open.filter((t) => t.due < t0)],
    ["Today", open.filter((t) => t.due === t0)],
    ["Next 7 days", open.filter((t) => t.due > t0 && t.due <= addDays(t0, 7))],
    ["Later", open.filter((t) => t.due > addDays(t0, 7))],
  ];
  const done = snap.tasks.filter((t) => t.done);
  const row = (t: TaskView) => (
    <TaskRow key={t.id} t={t} tagged={tagged} onToggle={() => toggle(t)} onDelete={() => apply(() => api.deleteTask(snap.id, t.id))} />
  );
  const apply = (action: () => Promise<Snapshot>) => run(action).then((s) => s && onSnap(s));
  const toggle = (t: TaskView) => apply(() => (t.done ? api.reopenTask(snap.id, t.id) : api.completeTask(snap.id, t.id)));
  return (
    <section class="card" aria-label="Tasks">
      <h2>Tasks</h2>
      {open.length === 0 ? <p class="muted">Nothing to do. Nice.</p> : null}
      {groups.map(([name, items]) =>
        items.length ? (
          <div key={name}>
            <h3 class="muted small" style="margin:6px 0 2px">{name}</h3>
            {items.map(row)}
          </div>
        ) : null,
      )}
      {done.length ? (
        <div>
          <button class="btn ghost small" onClick={() => setShowDone(!showDone)}>{showDone ? "Hide" : "Show"} {done.length} done</button>
          {showDone ? done.map(row) : null}
        </div>
      ) : null}
      <form
        class="row wrap"
        onSubmit={(e) => {
          e.preventDefault();
          if (!title.trim()) return;
          apply(() => api.addTask(snap.id, { title, every: every ?? 0, grow: forGrow || undefined })).then(() => {
            setTitle("");
            setEvery(null);
          });
        }}
      >
        <input type="text" class="grow" style="min-width:160px" placeholder="Add a task" aria-label="New task" value={title} onInput={(e) => setTitle((e.currentTarget as HTMLInputElement).value)} />
        {tagged ? (
          <select aria-label="Task is for" style="width:auto" value={forGrow} onChange={(e) => setForGrow((e.currentTarget as HTMLSelectElement).value)}>
            <option value="">All grows</option>
            {snap.grows.map((g) => <option value={g.id} key={g.id}>{g.name}</option>)}
          </select>
        ) : null}
        <span class="row small muted">repeat every <span style="width:64px"><NumberInput value={every} onChange={setEvery} min={0} step={1} placeholder="–" ariaLabel="Repeat every N days" /></span> days</span>
        <button class="btn" type="submit" disabled={busy || !title.trim()}>Add</button>
      </form>
    </section>
  );
}

export { clock };
