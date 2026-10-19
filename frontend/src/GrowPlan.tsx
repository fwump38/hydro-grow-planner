// A running grow's own plan: its schedules, tasks and targets. Editing it changes only this grow.

import { useEffect, useState } from "preact/hooks";

import { api } from "./api";
import { PlanEditor } from "./PlanEditor";
import type { Meta, Plan, Snapshot } from "./types";
import { Dialog, Field, useAction } from "./ui";

interface Props {
  snap: Snapshot;
  meta: Meta;
  growId: string;
  onBack: () => void;
}

export function GrowPlan({ snap, meta, growId, onBack }: Props) {
  const grow = snap.grows.find((g) => g.id === growId);
  const [plan, setPlan] = useState<Plan | null>(null);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    api.growPlan(snap.id, growId).then(setPlan);
  }, [snap.id, growId]);

  if (!grow) return <button class="btn ghost" onClick={onBack}>← Overview</button>;
  if (!plan) return <p class="muted">Loading…</p>;
  return (
    <div class="stack">
      <div class="row">
        <button class="btn ghost" onClick={onBack}>← Overview</button>
        <h2>{grow.name}</h2>
      </div>
      <PlanEditor
        key={growId}
        initial={plan}
        slots={snap.devices.map((d) => ({ key: d.id, label: d.name }))}
        ecUnit={snap.ec_unit}
        stageTypes={meta.stage_types}
        taskTypes={meta.task_types}
        hint="saved changes apply to this grow right away"
        onSave={async (next) => {
          const saved = (await api.saveGrowPlan(snap.id, growId, next)).plan;
          setPlan(saved);
          return saved;
        }}
        extra={<button class="btn" onClick={() => setSaving(true)}>Save as template…</button>}
      />
      {saving ? <SaveAsTemplate snap={snap} growId={growId} name={grow.name} onClose={() => setSaving(false)} /> : null}
    </div>
  );
}

function SaveAsTemplate({ snap, growId, name: initial, onClose }: { snap: Snapshot; growId: string; name: string; onClose: () => void }) {
  const [name, setName] = useState(initial);
  const { run, busy } = useAction();
  return (
    <Dialog title="Save as template" onClose={onClose}>
      <p class="muted small">
        Templates describe roles (center lights, side lights, pump), not your devices. Devices without a role in Settings are left out.
      </p>
      <Field label="Template name"><input type="text" value={name} onInput={(e) => setName((e.currentTarget as HTMLInputElement).value)} /></Field>
      <div class="row" style="justify-content:flex-end">
        <button class="btn" onClick={onClose}>Cancel</button>
        <button class="btn primary" disabled={busy || !name.trim()}
          onClick={async () => {
            const made = await run(() => api.templateFromGrow({ system_id: snap.id, grow_id: growId, name }), "Saved to Templates");
            if (made) onClose();
          }}>Save</button>
      </div>
    </Dialog>
  );
}
