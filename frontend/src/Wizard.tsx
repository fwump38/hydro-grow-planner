// Start, add or change a grow: template and zone → name, stage and date with a live review.
// The grow keeps its own copy of the template, which can be edited afterwards.

import { useEffect, useMemo, useState } from "preact/hooks";

import { ApiError, api, type StartArgs } from "./api";
import { addDays, dayLabel, shortDate, today } from "./format";
import { busyWith, defaultZones, zoneLabel } from "./roles";
import type { Meta, Preview, Snapshot, TemplateCard } from "./types";
import { Badge, Dialog, Field, NumberInput, Switch, useAction } from "./ui";

interface Props {
  snap: Snapshot;
  meta: Meta;
  /** Preselect a template ("builtin:…"/"custom:…"), or replace a running grow (id). */
  initial?: { template?: string; replace?: string };
  onClose: () => void;
  onDone: (snap: Snapshot) => void;
  /** Close this and walk through setting up zones and devices. */
  onSetupZones: () => void;
}

const STEPS = ["Template & zone", "Details & review"];

function daysBetween(from: string, to: string): number {
  return Math.round((new Date(`${to}T00:00:00`).getTime() - new Date(`${from}T00:00:00`).getTime()) / 86_400_000);
}

export function Wizard({ snap, initial, onClose, onDone, onSetupZones }: Props) {
  const [templates, setTemplates] = useState<TemplateCard[]>([]);
  const [template, setTemplate] = useState<string | null>(initial?.template ?? null);
  const [step, setStep] = useState(0);
  const replacing = snap.grows.find((g) => g.id === initial?.replace);
  // Zones (groups of lights) are set up in Settings or the setup walkthrough.
  const useZones = snap.zones.length > 0;
  const [zoneIds, setZoneIds] = useState<string[]>(() =>
    replacing
      ? snap.zones.filter((z) => snap.devices.some((d) => d.zone === z.id && d.drivers.some((x) => x.grow_id === replacing.id))).map((z) => z.id)
      : defaultZones(snap.zones),
  );
  const [name, setName] = useState(replacing?.name ?? "");
  const [nameEdited, setNameEdited] = useState(Boolean(replacing));
  const [stageNames, setStageNames] = useState<{ name: string; days: number }[]>([]);
  const [stage, setStage] = useState(replacing?.stage?.number ?? 1);
  const [started, setStarted] = useState(replacing?.stage?.started ?? today());
  const [includePast, setIncludePast] = useState(false);
  const [night, setNight] = useState(replacing?.night_lighting ?? false);
  // Changing the plan mid-grow doesn't restart the grow's clock.
  const [keepStart, setKeepStart] = useState(true);
  const [preview, setPreview] = useState<Preview | null>(null);
  const [previewError, setPreviewError] = useState<string | null>(null);
  const { run, busy } = useAction();

  useEffect(() => {
    api.templates().then(setTemplates);
  }, []);

  // Learn the stage names/lengths of the template.
  useEffect(() => {
    if (!template) return;
    api.template(template).then((p) => {
      if (!nameEdited && !useZones) setName(p.name);
      setStageNames(p.stages.map((s) => ({ name: s.name, days: s.days })));
      setStage((current) => Math.min(Math.max(current, 1), p.stages.length));
    });
  }, [template]);

  // Name a new grow after its zones until the user types their own.
  useEffect(() => {
    if (!nameEdited && useZones && zoneIds.length) setName(zoneLabel(snap.zones, zoneIds));
  }, [zoneIds]);

  const stageInfo = stageNames[stage - 1];
  const dayOfStage = daysBetween(started, today()) + 1;

  const args = useMemo(
    (): StartArgs => ({
      template: template ?? undefined,
      zones: zoneIds,
      stage,
      stage_started: started,
      include_past_tasks: includePast,
      replace: replacing?.id,
      night_lighting: night,
      keep_grow_start: replacing ? keepStart : undefined,
    }),
    [template, zoneIds, stage, started, includePast, night, keepStart],
  );

  useEffect(() => {
    if (step !== 1 || !template) return;
    setPreview(null);
    setPreviewError(null);
    api.previewStart(snap.id, args).then(setPreview).catch((e: unknown) => setPreviewError(e instanceof ApiError ? e.message : String(e)));
  }, [step, args]);

  const needsZone = zoneIds.length === 0;
  const sharedZones = useZones ? snap.zones.filter((z) => zoneIds.includes(z.id) && busyWith(z, replacing?.name).length) : [];

  const confirm = async () => {
    if (!template) return;
    const result = await run(
      () =>
        api.startGrow(snap.id, {
          ...args,
          name: name.trim() || undefined,
        }),
      replacing ? "Grow changed" : "Grow started",
    );
    if (result) onDone(result);
  };

  const back = () => {
    setStep(Math.max(0, step - 1));
  };

  return (
    <Dialog title={replacing ? `Change ${replacing.name}` : snap.grows.length ? "Add a grow" : "Start a grow"} onClose={onClose}>
      <div class="steps" aria-label="Steps">
        {STEPS.map((label, i) => <span key={label} class={i === step ? "on" : ""}>{i + 1}. {label}</span>)}
      </div>

      {step === 0 ? (
        <>
          <div class="stack" style="max-height:34vh;overflow:auto">
            {templates.map((t) => (
              <button
                class={`btn${template === t.id ? " primary" : ""}`}
                style="text-align:left"
                key={t.id}
                onClick={() => setTemplate(t.id)}
              >
                {t.name} <span class="muted small">— {t.stage_count} stages, {t.total_days} days{t.builtin ? "" : " · mine"}</span>
              </button>
            ))}
          </div>

          {template && useZones ? (
            <div class="stack" style="gap:4px" role="group" aria-label="Zones">
              <h3>Which zone?</h3>
              {snap.zones.map((z) => {
                const busy = busyWith(z, replacing?.name);
                return (
                  <label class="check" key={z.id} style={busy.length ? "opacity:.6" : ""}>
                    <input
                      type="checkbox"
                      checked={zoneIds.includes(z.id)}
                      onChange={(e) => {
                        const on = (e.currentTarget as HTMLInputElement).checked;
                        setZoneIds(on ? [...zoneIds, z.id] : zoneIds.filter((x) => x !== z.id));
                      }}
                    />
                    {z.name}{" "}
                    {busy.length ? <span class="muted small">· in use by {busy.join(", ")}</span> : null}
                    {snap.devices.some((d) => d.zone === z.id) ? null : <span class="muted small">· no lights yet</span>}
                  </label>
                );
              })}
              <span class="muted small">The pump is shared by every grow and picked up automatically.</span>
              {sharedZones.length ? (
                <div class="callout small">{sharedZones.map((z) => z.name).join(", ")} already runs a grow. Both grows will drive its lights, so a light is on whenever either wants it.</div>
              ) : null}
            </div>
          ) : null}

          {!useZones ? (
            <div class="callout stack">
              <strong>Set up your zones first</strong>
              <span class="small">A zone is the set of lights one grow takes over, e.g. “Layers 1+2”. Once your lights are in zones, starting a grow is just a template and a zone.</span>
              <div><button class="btn primary" onClick={onSetupZones}>Set up zones…</button></div>
            </div>
          ) : null}
        </>
      ) : null}

      {step === 1 ? (
        <div class="stack">
          <Field label="Grow name" hint="Tells grows apart on tasks and entities, e.g. “Layers 1+2”">
            <input
              type="text"
              value={name}
              onInput={(e) => {
                setName((e.currentTarget as HTMLInputElement).value);
                setNameEdited(true);
              }}
            />
          </Field>
          <p class="muted small">Already growing? Tell it where you are so schedules and tasks line up.</p>
          <Field label="Current stage">
            <select value={stage} onChange={(e) => setStage(Number((e.currentTarget as HTMLSelectElement).value))}>
              {stageNames.map((s, i) => <option value={i + 1} key={i}>{i + 1}. {s.name} ({s.days} days)</option>)}
            </select>
          </Field>
          <div class="cols2">
            <Field label="This stage started on">
              <input type="date" value={started} max={today()} onInput={(e) => setStarted((e.currentTarget as HTMLInputElement).value || today())} />
            </Field>
            <Field label="…which makes today day" hint={stageInfo ? `of ${stageInfo.days} planned` : undefined}>
              <NumberInput value={dayOfStage} step={1} min={1} onChange={(v) => v && v >= 1 && setStarted(addDays(today(), -(v - 1)))} ariaLabel="Day of stage" />
            </Field>
          </div>
          <div class="row wrap small">
            <span class="muted">Quick:</span>
            <button class="btn small" onClick={() => setStarted(today())}>Starting today</button>
            <button class="btn small" onClick={() => setStarted(addDays(today(), -7))}>A week ago</button>
          </div>
          <label class="check"><input type="checkbox" checked={includePast} onChange={(e) => setIncludePast((e.currentTarget as HTMLInputElement).checked)} />Also add tasks from days already passed (as overdue)</label>
          {replacing?.grow_started ? (
            <label class="check"><input type="checkbox" checked={keepStart} onChange={(e) => setKeepStart((e.currentTarget as HTMLInputElement).checked)} />Keep counting the grow from {shortDate(replacing.grow_started)} (it's the same plants, just a different plan). This sets when system upkeep falls due.</label>
          ) : null}
          <label class="row"><Switch label="Night lighting" checked={night} onChange={setNight} /> Night lighting (this grow's lights run 12 hours shifted)</label>
          <hr />
          {previewError ? <p class="error-text" role="alert">{previewError}</p> : !preview ? <p class="muted">Working it out…</p> : <Review p={preview} replacing={replacing?.name} name={name} />}
        </div>
      ) : null}

      <div class="row" style="justify-content:space-between">
        <button class="btn" onClick={step === 0 ? onClose : back}>{step === 0 ? "Cancel" : "Back"}</button>
        {step === 1 ? (
          <button class="btn primary" disabled={busy || !preview} onClick={confirm}>{replacing ? "Switch to this plan" : "Start grow"}</button>
        ) : (
          <button class="btn primary" disabled={!template || needsZone} onClick={() => setStep(1)}>Next</button>
        )}
      </div>
    </Dialog>
  );
}

function Review({ p, replacing, name }: { p: Preview; replacing?: string; name: string }) {
  return (
    <div class="stack">
      {replacing ? <div class="callout small">This replaces {replacing}. Its task progress is reset.</div> : null}
      <div>
        <strong>{name.trim() && name.trim() !== p.plan ? `${name.trim()} — ${p.plan}` : p.plan}</strong>
        <div class="muted small">
          Stage {p.stage_number} of {p.stage_count}: {p.stage} — day {p.stage_day} of {p.stage_days}
          <br />Grow started {shortDate(p.grow_started)} · expected end {shortDate(p.expected_end)}
        </div>
      </div>
      <div>
        <h3>Right now</h3>
        {p.devices.map((d, i) => (
          <div class="row" key={i}>
            <span class="grow">{d.name}{d.shared_with.length ? <span class="muted small"> · shared with {d.shared_with.join(", ")}</span> : null}</span>
            {d.desired === null ? <Badge>left alone</Badge> : <Badge kind={d.desired ? "ok" : undefined}>{d.desired ? "on" : "off"}</Badge>}</div>
        ))}
      </div>
      <div>
        <h3>Tasks that will appear</h3>
        {p.tasks.length === 0 ? <p class="muted small">None right now.</p> : null}
        {p.tasks.map((t, i) => (
          <div class="row small" key={i}>
            <span class="grow">{t.title}{t.recurring ? " ↻" : ""}</span>
            <span class={t.overdue ? "badge bad" : "muted"}>{t.overdue ? "overdue" : dayLabel(t.due)}</span>
          </div>
        ))}
        {p.skipped_tasks.length ? <p class="muted small">Skipped (their day has passed): {p.skipped_tasks.join(", ")}</p> : null}
      </div>
      <p class="muted small">You'll be prompted to check if this stage is done on {shortDate(p.stage_check_due)}. It never moves on by itself.</p>
    </div>
  );
}
