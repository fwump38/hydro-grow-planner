import { useEffect, useState } from "preact/hooks";

import { api } from "./api";
import type { DoseResult, Meta, NutrientLine, Snapshot, SystemConfig } from "./types";
import { Badge, ConfirmButton, Field, NumberInput, useAction } from "./ui";

function age(iso: string | null): string {
  if (!iso) return "at an unknown time";
  const minutes = Math.max(0, Math.round((Date.now() - new Date(iso).getTime()) / 60_000));
  if (minutes < 60) return `${minutes} min ago`;
  if (minutes < 48 * 60) return `${Math.round(minutes / 60)} h ago`;
  return `${Math.round(minutes / 1440)} days ago`;
}

/** Works out how much of each nutrient to add with new water to reach the grows' target EC. */
export function NutrientCard({ snap, onSnap }: { snap: Snapshot; onSnap: (s: Snapshot) => void }) {
  const { run, busy } = useAction();
  const r = snap.reservoir;
  const ecMetric = snap.metrics.ec;
  const [added, setAdded] = useState<number | null>(null);
  const [ec, setEc] = useState<number | null>(null);
  const [target, setTarget] = useState<number | null>(null);
  const [result, setResult] = useState<DoseResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  const noEc = ecMetric.value === null;
  // An EC typed here replaces the stored one, so the stale warning no longer applies.
  const needsReading = (noEc || r.ec_stale) && ec === null;

  useEffect(() => {
    setResult(null);
    setError(null);
    if (!r.capacity || !added || added <= 0 || needsReading) return;
    let current = true;
    const timer = window.setTimeout(() => {
      api
        .calculateNutrients(snap.id, { added, ec, target_ec: target })
        .then((res) => current && setResult(res))
        .catch((err) => current && setError(err instanceof Error ? err.message : String(err)));
    }, 250);
    return () => {
      current = false;
      window.clearTimeout(timer);
    };
  }, [snap.id, added, ec, target, needsReading, r.capacity, r.volume_unit, snap.ec_unit, ecMetric.value, ecMetric.min, ecMetric.max]);

  const record = async () => {
    const s = await run(() => api.record(snap.id, { ec }), "EC recorded");
    if (s) {
      onSnap(s);
      setEc(null);
    }
  };
  const unit = r.volume_unit;
  const range = ecMetric.range ? `${ecMetric.range} ${snap.ec_unit}` : "no EC range in the plan";

  return (
    <section class="card" aria-label="Add water and nutrients">
      <div class="row between wrap">
        <h2>Add water &amp; nutrients</h2>
        <Badge>{r.nutrient_line}</Badge>
      </div>
      {!r.capacity ? (
        <p class="muted">Set your tank capacity under <a href="#/settings">Settings → Tank &amp; nutrients</a> to use this.</p>
      ) : (
        <>
          <p class="muted small">
            Tank holds {r.capacity} {unit}. Target EC is the middle of the running grows' range ({range}).
          </p>
          {needsReading ? (
            <div class="callout" role="alert">
              <strong>
                {noEc ? "No EC reading yet." : `The EC reading is ${age(r.ec_updated)} (older than ${r.stale_hours} h).`}
              </strong>
              <span class="small">Measure the water now and enter it below so the dose is right.</span>
            </div>
          ) : null}
          <div class="cols2">
            <Field label={`Water to add (${unit})`}>
              <NumberInput value={added} onChange={setAdded} min={0} step="0.1" ariaLabel="Water to add" placeholder="e.g. 3.4" />
            </Field>
            <Field
              label={`EC now (${snap.ec_unit})`}
              hint={ec === null && !noEc ? `Using the ${r.ec_stale ? "stale " : ""}reading from ${age(r.ec_updated)}` : undefined}
            >
              <NumberInput value={ec} onChange={setEc} min={0} ariaLabel="Current EC" placeholder={noEc ? "measure it" : String(ecMetric.value)} />
            </Field>
          </div>
          <details>
            <summary class="muted small">Use a different target EC</summary>
            <Field label={`Target EC (${snap.ec_unit})`}>
              <NumberInput value={target} onChange={setTarget} min={0} ariaLabel="Target EC" placeholder="middle of the range" />
            </Field>
          </details>
          {ec !== null ? (
            <div class="row wrap">
              <button class="btn small" type="button" disabled={busy} onClick={record}>Also record this as the current EC</button>
            </div>
          ) : null}
          {error ? <p class="error-text" role="alert">{error}</p> : null}
          {result ? <DoseTable result={result} /> : null}
        </>
      )}
    </section>
  );
}

function DoseTable({ result }: { result: DoseResult }) {
  const u = result.volume_unit;
  return (
    <div class="stack">
      <p class="small">
        Adding {result.added} {u} fills the tank to {result.capacity} {u}. Water already in the tank ({result.current_volume} {u}) is at{" "}
        {result.current_ec ?? "?"} {result.ec_unit}, which dilutes to {result.diluted_ec} {result.ec_unit}. Target {result.target_ec} {result.ec_unit}.
      </p>
      {result.needs_nutrients ? (
        <table class="tasks" aria-label="Nutrient amounts">
          <thead>
            <tr>
              <th>Nutrient</th>
              <th>Total for {result.added} {u}</th>
              <th>Per {u} added</th>
            </tr>
          </thead>
          <tbody>
            {result.products.map((p) => (
              <tr key={p.id}>
                <td>{p.short}</td>
                <td><strong>{p.ml} ml</strong><div class="muted small">{p.weight} {result.weight_unit}</div></td>
                <td>{p.ml_per_unit} ml<div class="muted small">{p.weight_per_unit} {result.weight_unit}</div></td>
              </tr>
            ))}
          </tbody>
        </table>
      ) : null}
      <p class="muted small">
        Dosing for {result.stages.map((s) => `${s.grow}: ${s.stage} (${s.column})`).join("; ")}.
      </p>
      {result.warnings.map((w) => <div class="callout small" key={w}>{w}</div>)}
    </div>
  );
}

// -- settings ------------------------------------------------------------------------------------

const tmp = () => `new-${Date.now()}-${Math.floor(Math.random() * 1000)}`;

function blankLine(): NutrientLine {
  const product = tmp();
  return {
    id: tmp(),
    name: "My nutrients",
    products: [{ id: product, name: "Part A", short: "A", density: 1.0 }],
    stages: [{ id: tmp(), name: "Full strength", ec: 2.0, stage_types: [], doses: { [product]: 2 } }],
  };
}

function copyOf(line: NutrientLine): NutrientLine {
  const ids = new Map(line.products.map((p) => [p.id, tmp()]));
  return {
    id: tmp(),
    name: `${line.name} (copy)`,
    products: line.products.map((p) => ({ ...p, id: ids.get(p.id) as string })),
    stages: line.stages.map((s) => ({
      ...s,
      id: tmp(),
      stage_types: [...s.stage_types],
      doses: Object.fromEntries(Object.entries(s.doses).map(([k, v]) => [ids.get(k) as string, v])),
    })),
  };
}

/** Tank size, how fresh an EC reading must be, and which nutrient line (with its dose chart) to use. */
export function NutrientSettings({ draft, edit, meta, volume }: {
  /** The volume unit in effect (the setting, else Home Assistant's). */
  volume: string;
  draft: SystemConfig;
  edit: (mutate: (c: SystemConfig) => void) => void;
  meta: Meta;
}) {
  const builtin = meta.builtin_nutrients;
  const lines = [...builtin, ...draft.nutrients.custom];
  const index = draft.nutrients.custom.findIndex((l) => l.id === draft.nutrients.active);
  const line = index >= 0 ? draft.nutrients.custom[index] : null;
  const shown = lines.find((l) => l.id === draft.nutrients.active) ?? builtin[0];
  const add = (l: NutrientLine) => edit((c) => { c.nutrients.custom.push(l); c.nutrients.active = l.id; });
  const set = (mutate: (l: NutrientLine) => void) => edit((c) => mutate(c.nutrients.custom[index]));

  return (
    <section class="card">
      <h2>Tank &amp; nutrients</h2>
      <div class="grid">
        <Field label={`Total water capacity (${volume})`} hint="What the system holds when full, so the calculator knows what's already in it. Uses the volume unit from Settings → Units.">
          <NumberInput value={draft.capacity} min={0} step="0.1" onChange={(v) => edit((c) => (c.capacity = v))} ariaLabel="Tank capacity" />
        </Field>
        <Field label="Ask for a fresh EC reading after (hours)" hint="The calculator asks you to measure again when the last EC reading is older than this.">
          <NumberInput value={draft.ec_stale_hours} min={1} max={1440} step={1} onChange={(v) => edit((c) => (c.ec_stale_hours = v ?? 24))} ariaLabel="EC stale hours" />
        </Field>
        <Field label="Nutrient line">
          <select value={draft.nutrients.active} onChange={(e) => edit((c) => (c.nutrients.active = (e.currentTarget as HTMLSelectElement).value))}>
            {builtin.map((l) => <option value={l.id} key={l.id}>{l.name} (built in)</option>)}
            {draft.nutrients.custom.map((l) => <option value={l.id} key={l.id}>{l.name || "Unnamed"}</option>)}
          </select>
        </Field>
      </div>
      <div class="row wrap">
        <button class="btn small" type="button" onClick={() => add(blankLine())}>+ Add my own nutrients</button>
        <button class="btn small" type="button" onClick={() => add(copyOf(shown))}>Copy “{shown.name}” to edit</button>
        {line ? (
          <ConfirmButton label="Delete this line" class="small danger" confirmLabel="Delete" question={`Delete “${line.name}”?`}
            onConfirm={() => edit((c) => { c.nutrients.custom.splice(index, 1); c.nutrients.active = builtin[0].id; })} />
        ) : null}
      </div>

      {line ? (
        <div class="stack">
          <Field label="Name"><input type="text" value={line.name} onInput={(e) => set((l) => (l.name = (e.currentTarget as HTMLInputElement).value))} /></Field>
          <h3>Products</h3>
          <p class="muted small">Density (g/ml) is on the label or data sheet; it lets the calculator show weights for dosing on a scale.</p>
          {line.products.map((p, i) => (
            <div class="cols2" key={p.id}>
              <Field label="Name"><input type="text" value={p.name} onInput={(e) => set((l) => (l.products[i].name = (e.currentTarget as HTMLInputElement).value))} /></Field>
              <div class="row">
                <Field label="Short name"><input type="text" value={p.short} onInput={(e) => set((l) => (l.products[i].short = (e.currentTarget as HTMLInputElement).value))} /></Field>
                <Field label="g/ml"><NumberInput value={p.density} min={0} onChange={(v) => set((l) => (l.products[i].density = v ?? 1))} ariaLabel={`Density of ${p.name}`} /></Field>
                <button class="btn small danger" type="button" aria-label={`Remove ${p.name}`} disabled={line.products.length < 2} onClick={() => set((l) => l.products.splice(i, 1))}>✕</button>
              </div>
            </div>
          ))}
          <div><button class="btn small" type="button" onClick={() => set((l) => l.products.push({ id: tmp(), name: "", short: "", density: 1.0 }))}>+ Add product</button></div>

          <h3>Dose chart</h3>
          <p class="muted small">
            One column per feeding stage, from the bottle's chart: ml of each product per US gallon of water, and the EC that mix gives (mS/cm).
            Tick the plan stage types each column feeds; stages not ticked anywhere use the column with the nearest EC.
          </p>
          {line.stages.map((s, i) => (
            <div class="task-edit" key={s.id}>
              <div class="cols2">
                <Field label="Column name"><input type="text" value={s.name} onInput={(e) => set((l) => (l.stages[i].name = (e.currentTarget as HTMLInputElement).value))} /></Field>
                <Field label="EC this gives (mS/cm)"><NumberInput value={s.ec} min={0} onChange={(v) => set((l) => (l.stages[i].ec = v ?? 1))} ariaLabel={`EC of ${s.name}`} /></Field>
              </div>
              <div class="grid">
                {line.products.map((p) => (
                  <Field label={`${p.short || p.name} (ml/gal)`} key={p.id}>
                    <NumberInput value={s.doses[p.id] ?? 0} min={0} onChange={(v) => set((l) => (l.stages[i].doses[p.id] = v ?? 0))} ariaLabel={`${p.name} dose for ${s.name}`} />
                  </Field>
                ))}
              </div>
              <details>
                <summary class="muted small">Stage types: {s.stage_types.join(", ") || "none"}</summary>
                <div class="row wrap">
                  {meta.stage_types.map((t) => (
                    <label class="check" key={t}>
                      <input type="checkbox" checked={s.stage_types.includes(t)} onChange={(e) => set((l) => {
                        const types = l.stages[i].stage_types.filter((x) => x !== t);
                        if ((e.currentTarget as HTMLInputElement).checked) types.push(t);
                        l.stages[i].stage_types = types;
                      })} />{t}
                    </label>
                  ))}
                </div>
              </details>
              <div class="row"><span class="grow" /><button class="btn small danger" type="button" disabled={line.stages.length < 2} onClick={() => set((l) => l.stages.splice(i, 1))}>Remove column</button></div>
            </div>
          ))}
          <div><button class="btn small" type="button" onClick={() => set((l) => l.stages.push({ id: tmp(), name: "", ec: 2.0, stage_types: [], doses: {} }))}>+ Add column</button></div>
        </div>
      ) : (
        <ReadOnlyChart line={shown} />
      )}
    </section>
  );
}

function ReadOnlyChart({ line }: { line: NutrientLine }) {
  return (
    <details>
      <summary class="muted small">Dose chart for {line.name} (ml per US gallon)</summary>
      <table class="tasks">
        <thead>
          <tr><th></th>{line.stages.map((s) => <th key={s.id}>{s.name}</th>)}</tr>
        </thead>
        <tbody>
          {line.products.map((p) => (
            <tr key={p.id}><td>{p.short} <span class="muted small">{p.density} g/ml</span></td>{line.stages.map((s) => <td key={s.id}>{s.doses[p.id] ?? 0}</td>)}</tr>
          ))}
          <tr><td>EC (mS/cm)</td>{line.stages.map((s) => <td key={s.id}>{s.ec}</td>)}</tr>
        </tbody>
      </table>
    </details>
  );
}
