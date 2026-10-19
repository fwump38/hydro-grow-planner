// Guided setup for a system: name it, group its lights into zones, then add its devices.

import { useEffect, useState } from "preact/hooks";

import { api } from "./api";
import { DevicesEditor, ZonesEditor, type Edit } from "./SetupParts";
import type { EntityRow, Meta, SystemConfig } from "./types";
import { useAction } from "./ui";

interface Props {
  meta: Meta;
  /** Set up this existing system (at the zones step); without one, start by naming a new system. */
  systemId?: string;
  /** The system now exists: remember it so the panel keeps showing this setup. */
  onCreated: (id: string) => void;
  onDone: (id: string) => void;
}

const STEPS = ["Name", "Zones", "Devices"];
const clone = <T,>(v: T): T => JSON.parse(JSON.stringify(v));

export function Setup({ meta, systemId, onCreated, onDone }: Props) {
  const [id, setId] = useState<string | undefined>(systemId);
  const [step, setStep] = useState(systemId ? 1 : 0);
  const [name, setName] = useState("Grow System");
  const [draft, setDraft] = useState<SystemConfig | null>(null);
  const [entities, setEntities] = useState<EntityRow[]>([]);
  const { run, busy } = useAction();

  useEffect(() => {
    if (!id) return;
    api.config(id).then((c) => setDraft(clone(c)));
  }, [id]);
  useEffect(() => {
    api.entities(["switch", "light", "fan", "input_boolean"]).then(setEntities);
  }, []);

  const edit: Edit = (mutate) => {
    if (!draft) return;
    const next = clone(draft);
    mutate(next);
    setDraft(next);
  };

  const create = async () => {
    const created = await run(() => api.createSystem(name));
    if (!created) return;
    setId(created.id);
    onCreated(created.id);
    setStep(1);
  };

  const save = async (fields: Partial<SystemConfig>, next: () => void) => {
    if (!id) return;
    if (await run(() => api.saveConfig(id, fields))) next();
  };

  const named = draft?.zones.filter((z) => z.name.trim()) ?? [];

  return (
    <section class="card stack" aria-label="Set up your system">
      <div class="steps" aria-label="Steps">
        {STEPS.map((label, i) => <span key={label} class={i === step ? "on" : ""}>{i + 1}. {label}</span>)}
      </div>

      {step === 0 ? (
        <form
          class="stack"
          onSubmit={(e) => {
            e.preventDefault();
            create();
          }}
        >
          <h2>Welcome</h2>
          <p class="muted">
            A grow system is one tower or tray: its lights, pump and sensors. Name yours, then we'll set up its zones and devices.
          </p>
          <input type="text" aria-label="System name" style="max-width:320px" value={name} onInput={(e) => setName((e.currentTarget as HTMLInputElement).value)} />
          <div><button class="btn primary" type="submit" disabled={busy || !name.trim()}>Next</button></div>
        </form>
      ) : null}

      {step === 1 && draft ? (
        <div class="stack">
          <h2>Zones</h2>
          <p class="muted">
            A zone is a set of lights that run together, such as <em>Layers 1+2</em>. Each grow you start takes a free zone, and
            the zones can be at different stages with different lighting. The pump and reservoir are shared by every zone.
          </p>
          <ZonesEditor draft={draft} edit={edit} />
          <div class="row" style="justify-content:space-between">
            <button class="btn" onClick={() => onDone(id as string)}>Skip setup</button>
            <button class="btn primary" disabled={busy || named.length === 0} onClick={() => save({ zones: named }, () => { setDraft({ ...draft, zones: named }); setStep(2); })}>Next</button>
          </div>
        </div>
      ) : null}

      {step === 2 && draft ? (
        <div class="stack">
          <h2>Devices</h2>
          <p class="muted">
            Add each light and your pump. Give a light a role (center or side) and its zone, and give the pump the pump role.
            Starting a grow then picks everything up on its own.
          </p>
          <DevicesEditor draft={draft} edit={edit} entities={entities} all={entities} meta={meta} />
          <div class="row" style="justify-content:space-between">
            <button class="btn" onClick={() => setStep(1)}>Back</button>
            <button class="btn primary" disabled={busy} onClick={() => save({ devices: draft.devices.filter((d) => d.entity_id) }, () => onDone(id as string))}>Finish</button>
          </div>
        </div>
      ) : null}
    </section>
  );
}
