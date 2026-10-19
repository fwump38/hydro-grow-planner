import { useEffect, useState } from "preact/hooks";

import { api } from "./api";
import { PlanEditor } from "./PlanEditor";
import { describe, profile } from "./schedule";
import type { Meta, Plan, Schedule, Stage, Task, Template, TemplateCard } from "./types";
import { fromCanonical } from "./units";
import { Badge, ConfirmButton, useAction } from "./ui";

interface Props {
  meta: Meta;
  ecUnit: string;
  onUse: (templateId: string) => void;
}

type View = { kind: "list" } | { kind: "detail"; id: string } | { kind: "edit"; id: string };

export function Templates({ meta, ecUnit, onUse }: Props) {
  const [view, setView] = useState<View>({ kind: "list" });
  const [cards, setCards] = useState<TemplateCard[] | null>(null);
  const { run } = useAction();
  const load = () => api.templates().then(setCards);
  useEffect(() => {
    load();
  }, []);

  if (view.kind === "detail") {
    return (
      <Detail
        id={view.id}
        meta={meta}
        ecUnit={ecUnit}
        onBack={() => { load(); setView({ kind: "list" }); }}
        onUse={onUse}
        onEdit={(id) => setView({ kind: "edit", id })}
       
      />
    );
  }
  if (view.kind === "edit") {
    return <Edit id={view.id} meta={meta} ecUnit={ecUnit} onBack={() => setView({ kind: "detail", id: view.id })} />;
  }

  const importFile = async (file: File) => {
    try {
      const data = JSON.parse(await file.text());
      const made = await run(() => api.importTemplate(data.template ?? data), "Template imported");
      if (made) {
        await load();
        setView({ kind: "detail", id: made.id });
      }
    } catch {
      run(() => Promise.reject(new Error("That file isn't valid JSON")));
    }
  };

  if (!cards) return <p class="muted">Loading…</p>;
  const mine = cards.filter((c) => !c.builtin);
  const builtin = cards.filter((c) => c.builtin);
  return (
    <div class="stack">
      <div class="row between wrap">
        <h2>Templates</h2>
        <label class="btn" style="cursor:pointer">
          Import JSON…
          <input type="file" accept="application/json,.json" hidden onChange={(e) => { const f = (e.currentTarget as HTMLInputElement).files?.[0]; if (f) importFile(f); (e.currentTarget as HTMLInputElement).value = ""; }} />
        </label>
      </div>
      {mine.length ? (
        <>
          <h3 class="muted">My templates</h3>
          <div class="grid">{mine.map((c) => <Card key={c.id} c={c} onOpen={() => setView({ kind: "detail", id: c.id })} onUse={() => onUse(c.id)} />)}</div>
          <h3 class="muted">Built-in</h3>
        </>
      ) : null}
      <div class="grid">{builtin.map((c) => <Card key={c.id} c={c} onOpen={() => setView({ kind: "detail", id: c.id })} onUse={() => onUse(c.id)} />)}</div>
    </div>
  );
}

function Card({ c, onOpen, onUse }: { c: TemplateCard; onOpen: () => void; onUse: () => void }) {
  return (
    <section class="card">
      <div class="row between"><h3>{c.name}</h3>{c.builtin ? null : <Badge kind="accent">mine</Badge>}</div>
      <p class="muted small">{c.stage_count} stages · {c.total_days} days · {c.harvest_style === "continuous" ? "harvest a little at a time" : "harvest all at once"}</p>
      <div class="row wrap" style="gap:4px">
        {c.stages.map((s, i) => <Badge key={i}>{s.name} · {s.days}d</Badge>)}
      </div>
      <div class="small muted">
        {c.ph ? <div>pH {c.ph}</div> : null}
        {c.temperature ? <div>Temperature {c.temperature} {c.temp_unit}</div> : null}
        {c.humidity ? <div>Humidity {c.humidity} %</div> : null}
      </div>
      <div class="row wrap">
        <button class="btn primary" onClick={onUse}>Use template</button>
        <button class="btn" onClick={onOpen}>View</button>
      </div>
    </section>
  );
}

function recurrence(t: Task): string {
  if (t.every > 0) {
    const stop = t.until ? ` until day ${t.until}` : "";
    return `from day ${t.days[0]}, every ${t.every} ${t.every === 1 ? "day" : "days"} after done${stop}`;
  }
  return t.days.length === 1 ? `day ${t.days[0]}` : `days ${t.days.join(", ")}`;
}

function StageBlock({ stage, index, roles, ecUnit }: { stage: Stage; index: number; roles: Record<string, string>; ecUnit: string }) {
  const lo = fromCanonical(stage.ec_min, ecUnit);
  const hi = fromCanonical(stage.ec_max, ecUnit);
  return (
    <section class="card">
      <div class="row between wrap">
        <h3>{index + 1}. {stage.name}</h3>
        <span class="muted small">{stage.days} days{lo !== null && hi !== null ? ` · EC ${lo}–${hi} ${ecUnit}` : ""}</span>
      </div>
      {stage.outcome ? <p class="muted small">Goal: {stage.outcome}</p> : null}
      <div class="stack" style="gap:6px">
        {Object.entries(roles).map(([role, label]) => {
          const s: Schedule | undefined = stage.schedules[role];
          if (!s) return null;
          return (
            <div class="sched-row" key={role}>
              <span>{label}</span>
              <span class="muted small">{describe(s)}</span>
              {s.mode !== "manual" ? (
                <div class="daybar">
                  {profile(s).map(([a, b], i) => <i key={i} style={`left:${(a / 1440) * 100}%;width:${((b - a) / 1440) * 100}%`} />)}
                </div>
              ) : <span />}
            </div>
          );
        })}
      </div>
      {stage.tasks.length ? (
        <details>
          <summary>{stage.tasks.length} tasks</summary>
          <ul style="margin:8px 0 0;padding-left:18px">
            {stage.tasks.map((t, i) => <li key={i}>{t.title} <span class="muted small">— {recurrence(t)}</span></li>)}
          </ul>
        </details>
      ) : null}
    </section>
  );
}

function Detail(props: { id: string; meta: Meta; ecUnit: string; onBack: () => void; onUse: (id: string) => void; onEdit: (id: string) => void }) {
  const [tpl, setTpl] = useState<Template | null>(null);
  const { run } = useAction();
  useEffect(() => {
    setTpl(null);
    api.template(props.id).then(setTpl);
  }, [props.id]);
  if (!tpl) return <p class="muted">Loading…</p>;

  const exportJson = () => {
    const { id: _id, builtin: _b, ...data } = tpl;
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = `${tpl.name.toLowerCase().replace(/[^a-z0-9]+/g, "-")}.json`;
    a.click();
    URL.revokeObjectURL(a.href);
  };
  const ranges = [
    tpl.ph_min !== null && `pH ${tpl.ph_min}–${tpl.ph_max}`,
    tpl.temp_min !== null && `${tpl.temp_min}–${tpl.temp_max} ${tpl.temp_unit}`,
    tpl.humidity_min !== null && `${tpl.humidity_min}–${tpl.humidity_max} % humidity`,
    tpl.harvest_style === "continuous" && "harvested a little at a time",
  ].filter(Boolean);
  return (
    <div class="stack">
      <div class="row wrap">
        <button class="btn ghost" onClick={props.onBack}>← Templates</button>
        <h2 class="grow">{tpl.name}</h2>
        {tpl.builtin ? <Badge>built-in, read-only</Badge> : <Badge kind="accent">mine</Badge>}
      </div>
      <div class="row wrap">
        <button class="btn primary" onClick={() => props.onUse(tpl.id)}>Use template</button>
        <button class="btn" onClick={async () => { const copy = await run(() => api.duplicateTemplate(tpl.id)); if (copy) props.onEdit(copy.id); }}>Duplicate &amp; edit</button>
        {tpl.builtin ? null : <button class="btn" onClick={() => props.onEdit(tpl.id)}>Edit</button>}
        <button class="btn" onClick={exportJson}>Export JSON</button>
        {tpl.builtin ? null : <ConfirmButton label="Delete" class="danger" question={`Delete “${tpl.name}”? Plans already made from it are not affected.`} confirmLabel="Delete" onConfirm={() => run(() => api.deleteTemplate(tpl.id), "Deleted").then((ok) => ok && props.onBack())} />}
      </div>
      <p class="muted">{tpl.stages.length} stages · {tpl.stages.reduce((n, s) => n + s.days, 0)} days{ranges.length ? ` · ${ranges.join(" · ")}` : ""}</p>
      {tpl.stages.map((s, i) => <StageBlock key={i} stage={s} index={i} roles={props.meta.roles} ecUnit={props.ecUnit} />)}
    </div>
  );
}

function Edit({ id, meta, ecUnit, onBack }: { id: string; meta: Meta; ecUnit: string; onBack: () => void }) {
  const [tpl, setTpl] = useState<Template | null>(null);
  useEffect(() => {
    api.template(id).then(setTpl);
  }, [id]);
  if (!tpl) return <p class="muted">Loading…</p>;
  const { id: _id, builtin: _b, ...plan } = tpl;
  return (
    <div class="stack">
      <div class="row"><button class="btn ghost" onClick={onBack}>← Back</button><h2>Edit template</h2></div>
      <PlanEditor
        initial={plan as Plan}
        slots={Object.entries(meta.roles).map(([key, label]) => ({ key, label }))}
        ecUnit={ecUnit}
        stageTypes={meta.stage_types}
        taskTypes={meta.task_types}
        hint="schedules are for roles; you pick the devices when you use the template"
        onSave={async (data) => {
          const saved = await api.saveTemplate(id, data);
          const { id: _i, builtin: _bb, ...rest } = saved;
          return rest as Plan;
        }}
        onClose={onBack}
      />
    </div>
  );
}
