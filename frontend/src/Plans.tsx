import { useEffect, useState } from "preact/hooks";

import { api } from "./api";
import { PlanEditor } from "./PlanEditor";
import { RoleMapper } from "./RoleMapper";
import { guessRoles, invert, type RoleMap } from "./roles";
import type { Meta, Plan, Snapshot, TemplateCard } from "./types";
import { Badge, ConfirmButton, Dialog, Field, useAction } from "./ui";

/** The running grows that use a plan. */
function runningGrows(snap: Snapshot, planId: string) {
  return snap.grows.filter((g) => g.plan?.id === planId);
}

interface Props {
  snap: Snapshot;
  meta: Meta;
  onSnap: (s: Snapshot) => void;
  onStart: (planId: string) => void;
}

export function Plans({ snap, meta, onSnap, onStart }: Props) {
  const [plans, setPlans] = useState<Record<string, Plan> | null>(null);
  const [editing, setEditing] = useState<string | null>(null);
  const [dialog, setDialog] = useState<"new" | "template" | null>(null);
  const { run } = useAction();

  const load = () => api.plans(snap.id).then(setPlans);
  useEffect(() => {
    load();
  }, [snap.id]);

  if (!plans) return <p class="muted">Loading…</p>;

  if (editing && plans[editing]) {
    return (
      <div class="stack">
        <div class="row">
          <button class="btn ghost" onClick={() => setEditing(null)}>← All plans</button>
          <h2>{plans[editing].name}</h2>
          {runningGrows(snap, editing).length ? <Badge kind="ok">running</Badge> : null}
        </div>
        <PlanEditor
          key={editing}
          initial={plans[editing]}
          slots={snap.devices.map((d) => ({ key: d.id, label: d.name }))}
          ecUnit={snap.ec_unit}
          stageTypes={meta.stage_types}
          taskTypes={meta.task_types}
          hint={runningGrows(snap, editing).length ? "running — saved changes apply right away" : undefined}
          onSave={async (plan) => {
            const saved = (await api.savePlan(snap.id, editing, plan)).plan;
            setPlans({ ...plans, [editing]: saved });
            return saved;
          }}
          extra={
            <button class="btn" onClick={() => setDialog("template")}>Save as template…</button>
          }
        />
        {dialog === "template" ? (
          <SaveAsTemplate snap={snap} meta={meta} planId={editing} planName={plans[editing].name} onClose={() => setDialog(null)} />
        ) : null}
      </div>
    );
  }

  const entries = Object.entries(plans);
  return (
    <div class="stack">
      <div class="row between wrap">
        <h2>Your plans</h2>
        <div class="row">
          <button class="btn primary" onClick={() => setDialog("new")}>New plan…</button>
        </div>
      </div>
      {entries.length === 0 ? (
        <div class="card empty">
          <p class="muted">No plans yet. Start from one of the built-in templates, or build one from scratch.</p>
          <button class="btn primary" onClick={() => setDialog("new")}>New plan…</button>
        </div>
      ) : null}
      <div class="grid">
        {entries.map(([id, plan]) => {
          const growing = runningGrows(snap, id);
          const running = growing.length > 0;
          return (
            <section class="card" key={id}>
              <div class="row between">
                <h3>{plan.name}</h3>
                {running ? <Badge kind="ok">{growing.length > 1 || snap.grows.length > 1 ? growing.map((g) => g.name).join(", ") : "running"}</Badge> : null}
              </div>
              <p class="muted small">
                {plan.stages.length} stages · {plan.stages.reduce((n, s) => n + s.days, 0)} days
                {plan.ph_min !== null ? ` · pH ${plan.ph_min}–${plan.ph_max}` : ""}
              </p>
              <div class="row wrap">
                <button class="btn" onClick={() => setEditing(id)}>Edit</button>
                <button class="btn" onClick={() => onStart(id)}>{snap.grows.length ? "Add as a grow…" : "Start grow…"}</button>
                <ConfirmButton label="Delete" class="danger" confirmLabel="Delete"
                  question={running ? `“${plan.name}” is running. Deleting it ends ${growing.length > 1 ? "those grows" : "the grow"}.` : `Delete “${plan.name}”?`}
                  onConfirm={() => run(() => api.deletePlan(snap.id, id), "Deleted").then((s) => { if (s) onSnap(s); load(); })} />
              </div>
            </section>
          );
        })}
      </div>
      {dialog === "new" ? (
        <NewPlan snap={snap} meta={meta} onClose={() => setDialog(null)} onCreated={(id) => { setDialog(null); load().then(() => setEditing(id)); }} />
      ) : null}
    </div>
  );
}

function NewPlan({ snap, meta, onClose, onCreated }: { snap: Snapshot; meta: Meta; onClose: () => void; onCreated: (id: string) => void }) {
  const [templates, setTemplates] = useState<TemplateCard[]>([]);
  const [template, setTemplate] = useState<string>("");
  const [name, setName] = useState("");
  const [roles, setRoles] = useState<RoleMap>({});
  const { run, busy } = useAction();
  const devices = snap.devices;
  useEffect(() => {
    api.templates().then(setTemplates);
    setRoles(guessRoles(Object.keys(meta.roles), devices));
  }, []);
  return (
    <Dialog title="New plan" onClose={onClose}>
      <Field label="Start from">
        <select value={template} onChange={(e) => setTemplate((e.currentTarget as HTMLSelectElement).value)}>
          <option value="">A blank plan</option>
          {templates.map((t) => <option value={t.id} key={t.id}>{t.name}{t.builtin ? "" : " (mine)"} — {t.stage_count} stages</option>)}
        </select>
      </Field>
      <Field label="Name (optional)"><input type="text" value={name} onInput={(e) => setName((e.currentTarget as HTMLInputElement).value)} /></Field>
      {template ? (
        <>
          <h3>Which of your devices is which?</h3>
          <RoleMapper roles={meta.roles} devices={devices} value={roles} onChange={setRoles} />
        </>
      ) : null}
      <div class="row" style="justify-content:flex-end">
        <button class="btn" onClick={onClose}>Cancel</button>
        <button class="btn primary" disabled={busy}
          onClick={async () => {
            const made = await run(() => api.createPlan(snap.id, { template: template || undefined, role_map: template ? roles : undefined, name: name || undefined }));
            if (made) onCreated(made.plan_id);
          }}>Create</button>
      </div>
    </Dialog>
  );
}

function SaveAsTemplate({ snap, meta, planId, planName, onClose }: { snap: Snapshot; meta: Meta; planId: string; planName: string; onClose: () => void }) {
  const [name, setName] = useState(planName);
  const [roles, setRoles] = useState<RoleMap>(() => guessRoles(Object.keys(meta.roles), snap.devices));
  const { run, busy } = useAction();
  return (
    <Dialog title="Save as template" onClose={onClose}>
      <p class="muted small">Templates describe roles, not your devices. Choose which of your devices plays each role; others are left out.</p>
      <Field label="Template name"><input type="text" value={name} onInput={(e) => setName((e.currentTarget as HTMLInputElement).value)} /></Field>
      <RoleMapper roles={meta.roles} devices={snap.devices} value={roles} onChange={setRoles} />
      <div class="row" style="justify-content:flex-end">
        <button class="btn" onClick={onClose}>Cancel</button>
        <button class="btn primary" disabled={busy || !name.trim()}
          onClick={async () => {
            const made = await run(() => api.templateFromPlan({ system_id: snap.id, plan_id: planId, device_roles: invert(roles), name }), "Saved to Templates");
            if (made) onClose();
          }}>Save</button>
      </div>
    </Dialog>
  );
}
