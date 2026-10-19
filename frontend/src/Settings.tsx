import { useEffect, useMemo, useState } from "preact/hooks";

import { api } from "./api";
import { setDirty } from "./guard";
import { dayLabel } from "./format";
import type { EntityRow, Meta, Metric, Snapshot, SystemConfig, SystemRow } from "./types";
import { ConfirmButton, Field, NumberInput, useAction } from "./ui";
import { DevicesEditor, EntityPicker, ZonesEditor } from "./SetupParts";

interface Props {
  snap: Snapshot;
  meta: Meta;
  systems: SystemRow[];
  onSnap: (s: Snapshot) => void;
  onSelect: (id: string) => void;
  onChanged: () => void;
  /** Walk through zones and devices for a system. */
  onSetup: (id: string) => void;
}

const clone = <T,>(v: T): T => JSON.parse(JSON.stringify(v));

const SENSORS: [Metric, string, string[]][] = [
  ["ph", "pH sensor", ["sensor"]],
  ["ec", "EC sensor", ["sensor"]],
  ["temperature", "Room temperature sensor", ["sensor"]],
  ["humidity", "Room humidity sensor", ["sensor"]],
];

export function Settings({ snap, meta, systems, onSnap, onSelect, onChanged, onSetup }: Props) {
  const [saved, setSaved] = useState<SystemConfig | null>(null);
  const [draft, setDraft] = useState<SystemConfig | null>(null);
  const [entities, setEntities] = useState<EntityRow[]>([]);
  const [newName, setNewName] = useState("");
  const { run, busy } = useAction();

  useEffect(() => {
    setSaved(null);
    api.config(snap.id).then((c) => { setSaved(c); setDraft(clone(c)); });
  }, [snap.id]);
  useEffect(() => {
    api.entities(["switch", "light", "fan", "input_boolean", "sensor", "todo"]).then(setEntities);
  }, []);

  const dirty = useMemo(() => JSON.stringify(draft) !== JSON.stringify(saved), [draft, saved]);
  useEffect(() => {
    setDirty(dirty);
    return () => setDirty(false);
  }, [dirty]);

  if (!draft || !saved) return <p class="muted">Loading…</p>;
  const edit = (mutate: (c: SystemConfig) => void) => {
    const next = clone(draft);
    mutate(next);
    setDraft(next);
  };
  const switchable = entities.filter((e) => ["switch", "light", "fan", "input_boolean"].includes(e.entity_id.split(".")[0]));
  const sensors = entities.filter((e) => e.entity_id.startsWith("sensor."));
  const todos = entities.filter((e) => e.entity_id.startsWith("todo."));
  const unitChanged = draft.ec_unit !== saved.ec_unit;

  const save = async () => {
    const result = await run(() => api.saveConfig(snap.id, draft), "Settings saved");
    if (result) {
      onSnap(result);
      const fresh = await api.config(snap.id);
      setSaved(fresh);
      setDraft(clone(fresh));
      onChanged();
    }
  };

  return (
    <div class="stack">
      <section class="card">
        <h2>Grow system</h2>
        <Field label="Name"><input type="text" value={draft.name} onInput={(e) => edit((c) => (c.name = (e.currentTarget as HTMLInputElement).value))} /></Field>
        <div class="row wrap">
          {systems.length > 1 ? (
            <select aria-label="Switch system" style="width:auto" value={snap.id} onChange={(e) => onSelect((e.currentTarget as HTMLSelectElement).value)}>
              {systems.map((s) => <option value={s.id} key={s.id}>{s.name}</option>)}
            </select>
          ) : null}
          <input type="text" style="width:200px" placeholder="Add another system" aria-label="New system name" value={newName} onInput={(e) => setNewName((e.currentTarget as HTMLInputElement).value)} />
          <button class="btn" disabled={busy || !newName.trim()} onClick={async () => { const s = await run(() => api.createSystem(newName), "System created"); if (s) { setNewName(""); await onChanged(); onSelect(s.id); onSetup(s.id); } }}>Add</button>
          <span class="grow" />
          <ConfirmButton label="Delete this system" class="danger" confirmLabel="Delete" question={`Delete “${snap.name}”, its plans, tasks and Home Assistant entities?`}
            onConfirm={() => run(() => api.deleteSystem(snap.id), "System deleted").then((ok) => ok !== undefined && onChanged())} />
        </div>
      </section>

      <section class="card">
        <ZonesEditor draft={draft} edit={edit} />
      </section>

      <section class="card">
        <DevicesEditor draft={draft} edit={edit} entities={switchable} all={entities} meta={meta} />
      </section>

      <section class="card">
        <h2>Sensors</h2>
        <p class="muted small">Optional. With a sensor the value is read automatically; without one you record it by hand.</p>
        <div class="grid">
          {SENSORS.map(([metric, label]) => (
            <Field label={label} key={metric}>
              <EntityPicker label={label} value={draft.sensors[metric]} entities={sensors} onChange={(v) => edit((c) => (c.sensors[metric] = v))} />
            </Field>
          ))}
        </div>
      </section>

      <section class="card">
        <h2>Water readings</h2>
        <div class="grid">
          <Field label="EC unit" hint="Plans are stored in mS/cm; values you enter and see use this unit.">
            <select value={draft.ec_unit} onChange={(e) => edit((c) => (c.ec_unit = (e.currentTarget as HTMLSelectElement).value))}>
              {meta.ec_units.map((u) => <option value={u} key={u}>{u}{u === "ppm 500" ? " (TDS/NaCl)" : u === "ppm 700" ? " (442/KCl)" : u === "mS/cm" ? " (EC)" : ""}</option>)}
            </select>
          </Field>
          {draft.sensors.ec ? (
            <Field label="EC sensor reports in" hint="“ppm” alone is ambiguous, so pick the scale your meter uses.">
              <select value={draft.ec_sensor_unit ?? ""} onChange={(e) => edit((c) => (c.ec_sensor_unit = (e.currentTarget as HTMLSelectElement).value || null))}>
                <option value="">Detect from the sensor</option>
                {meta.ec_units.map((u) => <option value={u} key={u}>{u}</option>)}
              </select>
            </Field>
          ) : null}
          <Field label="Remind me to take a reading every (days)">
            <NumberInput value={draft.reading_interval_days} step={1} min={1} max={60} onChange={(v) => edit((c) => (c.reading_interval_days = v ?? 3))} ariaLabel="Reading interval days" />
          </Field>
        </div>
        {unitChanged ? <div class="callout small">Changing the EC unit republishes the Home Assistant EC entities in the new unit. History recorded before the change stays in the old unit.</div> : null}
      </section>

      <section class="card">
        <h2>Tasks &amp; reminders</h2>
        <div class="grid">
          <Field label="Daily reminder time"><input type="time" value={draft.reminder_time.slice(0, 5)} onInput={(e) => edit((c) => (c.reminder_time = (e.currentTarget as HTMLInputElement).value))} /></Field>
          <Field label="Mirror tasks to this Home Assistant to-do list" hint="Any to-do list works, e.g. a Local To-do list or an iCloud Reminders list. The app only adds, checks off and removes its own items; it never changes anything else on the list. Checking a task off there works too.">
            <EntityPicker label="To-do list" value={draft.todo_entity} entities={todos} placeholder="e.g. todo.grow_tasks" onChange={(v) => edit((c) => (c.todo_entity = v))} />
          </Field>
          {draft.todo_entity ? (
            <label class="check"><input type="checkbox" checked={!!draft.todo_adopt} onChange={(e) => edit((c) => (c.todo_adopt = (e.currentTarget as HTMLInputElement).checked))} />Turn items I add to this list into tasks (only items added after you switch this on)</label>
          ) : null}
        </div>
      </section>

      <section class="card">
        <div class="row between">
          <h2>System upkeep</h2>
          <button class="btn small" onClick={() => edit((c) => c.maintenance.push({ id: `new-${Date.now()}`, title: "", note: "", task_type: "reminder", every: 14, enabled: true, covers: [] }))}>+ Add task</button>
        </div>
        <p class="muted small">
          Jobs for the system itself, whatever is growing: changing the water, cleaning, calibrating. They repeat every N days of the system running
          {snap.system_day ? ` (day ${snap.system_day} now)` : ""}, counted from the oldest running grow's start date, and from when you last did each one. The defaults are for a small
          closed-loop kit; change them to suit yours.
        </p>
        {draft.maintenance.length === 0 ? <p class="muted">No upkeep tasks.</p> : null}
        {draft.maintenance.map((m, i) => {
          const info = snap.maintenance.find((x) => x.id === m.id);
          return (
            <div class="task-edit" key={m.id}>
              <div class="cols2">
                <Field label="Task"><input type="text" value={m.title} onInput={(e) => edit((c) => (c.maintenance[i].title = (e.currentTarget as HTMLInputElement).value))} /></Field>
                <Field label="Every (days)">
                  <NumberInput value={m.every} step={1} min={1} max={365} onChange={(v) => edit((c) => (c.maintenance[i].every = v ?? 14))} ariaLabel={`Days between ${m.title || "tasks"}`} />
                </Field>
              </div>
              <details>
                <summary class="muted small">How to do it</summary>
                <textarea rows={4} aria-label={`Instructions for ${m.title}`} value={m.note} onInput={(e) => edit((c) => (c.maintenance[i].note = (e.currentTarget as HTMLTextAreaElement).value))} />
              </details>
              <div class="row between wrap">
                <label class="check"><input type="checkbox" checked={m.enabled} onChange={(e) => edit((c) => (c.maintenance[i].enabled = (e.currentTarget as HTMLInputElement).checked))} />Remind me</label>
                <span class="muted small">
                  {info?.last_done ? `Last done ${dayLabel(info.last_done)}` : "Not done yet"}
                  {m.enabled && info?.next_due ? ` · next ${dayLabel(info.next_due)}` : ""}
                </span>
                <button class="btn small danger" onClick={() => edit((c) => c.maintenance.splice(i, 1))}>Remove</button>
              </div>
            </div>
          );
        })}
      </section>

      <div class="save-bar">
        <span class="grow muted small">{dirty ? "Unsaved changes" : "All changes saved"}</span>
        <button class="btn" disabled={!dirty || busy} onClick={() => setDraft(clone(saved))}>Discard</button>
        <button class="btn primary" disabled={!dirty || busy} onClick={save}>Save settings</button>
      </div>

      <Events meta={meta} />
    </div>
  );
}

const EXAMPLE = `automation:
  - alias: Grow tasks due
    triggers:
      - trigger: event
        event_type: hydro_grow_planner_tasks_due
    actions:
      - action: notify.mobile_app_YOUR_PHONE
        data:
          title: "Grow tasks ({{ trigger.event.data.count }})"
          message: >
            {% for t in trigger.event.data.tasks %}• {{ t.title }}
            {% endfor %}`;

function Events({ meta }: { meta: Meta }) {
  const { run } = useAction();
  return (
    <section class="card">
      <h2>Events for your automations</h2>
      <p class="muted small">
        The app doesn't send notifications itself. It fires these events on the Home Assistant bus, so you can notify however you like. “Send test” fires a sample (marked <code>test: true</code>).
      </p>
      <p class="muted small">
        To watch them in Home Assistant (Developer tools → Events → Listen to events), enter one exact event name below, or <code>*</code> for everything (prefix patterns like <code>hydro_grow_planner_*</code> don’t match).
      </p>
      {meta.events.map((e) => (
        <details key={e.event}>
          <summary><code>{e.event}</code></summary>
          <p class="muted small" style="margin:6px 0">{e.when}</p>
          <pre class="code">{JSON.stringify(e.example, null, 2)}</pre>
          <button class="btn small" style="margin-top:6px" onClick={() => run(() => api.testEvent(e.event), "Test event fired")}>Send test</button>
        </details>
      ))}
      <h3>Example: phone notification</h3>
      <pre class="code">{EXAMPLE}</pre>
    </section>
  );
}
