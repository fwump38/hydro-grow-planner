// Pieces of setting up a system, shared by Settings and the setup walkthrough.

import { useMemo } from "preact/hooks";

import type { DeviceConfig, EntityRow, Meta, SystemConfig } from "./types";
import { Field } from "./ui";

export type Edit = (mutate: (c: SystemConfig) => void) => void;

export function EntityPicker(props: { value: string | null; entities: EntityRow[]; onChange: (v: string | null) => void; label: string; placeholder?: string }) {
  const listId = useMemo(() => `entities-${Math.random().toString(36).slice(2)}`, []);
  const known = props.entities.find((e) => e.entity_id === props.value);
  return (
    <>
      <input
        type="text"
        aria-label={props.label}
        list={listId}
        placeholder={props.placeholder ?? "Search by name or entity id"}
        value={props.value ?? ""}
        onInput={(e) => {
          const text = (e.currentTarget as HTMLInputElement).value.trim();
          const byName = props.entities.find((x) => x.name.toLowerCase() === text.toLowerCase());
          props.onChange(byName ? byName.entity_id : text || null);
        }}
      />
      <datalist id={listId}>
        {props.entities.map((e) => <option value={e.entity_id} key={e.entity_id}>{e.name}</option>)}
      </datalist>
      {props.value && !known ? <span class="error-text">Home Assistant doesn't know this entity right now</span> : known ? <span class="small muted">{known.name}</span> : null}
    </>
  );
}

/** Zones: groups of lights that one grow takes over. */
export function ZonesEditor({ draft, edit }: { draft: SystemConfig; edit: Edit }) {
  return (
    <>
        <div class="row between"><h2>Zones</h2><button class="btn small" onClick={() => edit((c) => c.zones.push({ id: `z_${Math.random().toString(36).slice(2, 10)}`, name: "" }))}>+ Add zone</button></div>
        <p class="muted small">A zone is the lights one grow takes over, e.g. “Layers 1+2”. Starting a grow picks a free zone; the pump is shared by every grow.</p>
        {draft.zones.length === 0 && draft.devices.length ? <p class="muted">No zones yet. Add one, then give each light a role and a zone below.</p> : null}
        {draft.zones.map((z, i) => (
          <div class="row" key={z.id}>
            <input type="text" class="grow" aria-label="Zone name" placeholder="e.g. Layers 1+2" value={z.name} onInput={(e) => edit((c) => (c.zones[i].name = (e.currentTarget as HTMLInputElement).value))} />
            <button class="btn small danger" onClick={() => edit((c) => {
              const [gone] = c.zones.splice(i, 1);
              c.devices.forEach((d) => { if (d.zone === gone.id) d.zone = null; });
            })}>Remove</button>
          </div>
        ))}
    </>
  );
}

/** Devices, each with a role (and for lights, a zone). */
export function DevicesEditor({ draft, edit, entities, all, meta }: { draft: SystemConfig; edit: Edit; entities: EntityRow[]; all: EntityRow[]; meta: Meta }) {
  return (
    <>
        <div class="row between"><h2>Devices</h2><button class="btn small" onClick={() => edit((c) => c.devices.push({ name: "", entity_id: "", light: false, role: "", zone: null }))}>+ Add device</button></div>
        <p class="muted small">Anything with an on/off: switches, lights, fans. Give each a role so templates find it on their own.</p>
        {draft.devices.length === 0 ? <p class="muted">No devices yet.</p> : null}
        {draft.devices.map((d: DeviceConfig, i) => (
          <div class="task-edit" key={d.id ?? i}>
            <div class="cols2">
              <Field label="Name"><input type="text" value={d.name} onInput={(e) => edit((c) => (c.devices[i].name = (e.currentTarget as HTMLInputElement).value))} /></Field>
              <Field label="Entity">
                <EntityPicker label={`Entity for ${d.name || "device"}`} value={d.entity_id || null} entities={entities} onChange={(v) => edit((c) => {
                  c.devices[i].entity_id = v ?? "";
                  if (!c.devices[i].name && v) c.devices[i].name = all.find((e) => e.entity_id === v)?.name ?? v;
                })} />
              </Field>
            </div>
            <div class="cols2">
              <Field label="Role">
                <select value={d.role} onChange={(e) => edit((c) => {
                  const role = (e.currentTarget as HTMLSelectElement).value;
                  c.devices[i].role = role;
                  if (role.endsWith("_lights")) c.devices[i].light = true;
                  if (!role.endsWith("_lights")) c.devices[i].zone = null;
                })}>
                  <option value="">Other</option>
                  {Object.entries(meta.roles).map(([role, label]) => <option value={role} key={role}>{label}</option>)}
                </select>
              </Field>
              {d.role.endsWith("_lights") ? (
                <Field label="Zone">
                  <select value={d.zone ?? ""} onChange={(e) => edit((c) => (c.devices[i].zone = (e.currentTarget as HTMLSelectElement).value || null))}>
                    <option value="">None</option>
                    {draft.zones.map((z) => <option value={z.id} key={z.id}>{z.name || "(unnamed)"}</option>)}
                  </select>
                </Field>
              ) : d.role === "water_pump" ? <span class="muted small">Shared by every grow</span> : null}
            </div>
            <div class="row between">
              <label class="check"><input type="checkbox" checked={d.light} onChange={(e) => edit((c) => (c.devices[i].light = (e.currentTarget as HTMLInputElement).checked))} />Grow light (follows Night lighting)</label>
              <button class="btn small danger" onClick={() => edit((c) => c.devices.splice(i, 1))}>Remove</button>
            </div>
          </div>
        ))}
    </>
  );
}
