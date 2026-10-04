// Start or change a grow: template → devices → stage and date → review.

import { useEffect, useMemo, useState } from "preact/hooks";

import { ApiError, api, type StartArgs } from "./api";
import { addDays, dayLabel, shortDate, today } from "./format";
import { RoleMapper } from "./RoleMapper";
import { guessRoles } from "./roles";
import type { Meta, Plan, Preview, Snapshot, TemplateCard } from "./types";
import { Badge, Dialog, Field, NumberInput, Switch, useAction } from "./ui";

interface Props {
  snap: Snapshot;
  meta: Meta;
  /** Preselect a template ("builtin:…"/"custom:…") or one of this system's plans. */
  initial?: { template?: string; plan?: string };
  onClose: () => void;
  onDone: (snap: Snapshot) => void;
}

type Source = { kind: "template"; id: string } | { kind: "plan"; id: string } | null;
const STEPS = ["Template", "Devices", "Stage & date", "Review"];

function daysBetween(from: string, to: string): number {
  return Math.round((new Date(`${to}T00:00:00`).getTime() - new Date(`${from}T00:00:00`).getTime()) / 86_400_000);
}

export function Wizard({ snap, meta, initial, onClose, onDone }: Props) {
  const [templates, setTemplates] = useState<TemplateCard[]>([]);
  const [plans, setPlans] = useState<Record<string, Plan>>({});
  const [source, setSource] = useState<Source>(
    initial?.plan ? { kind: "plan", id: initial.plan } : initial?.template ? { kind: "template", id: initial.template } : null,
  );
  const [step, setStep] = useState(source ? (initial?.plan ? 2 : 1) : 0);
  const [roles, setRoles] = useState<Record<string, string>>(() => guessRoles(Object.keys(meta.roles), snap.devices));
  const [stageNames, setStageNames] = useState<{ name: string; days: number }[]>([]);
  const [stage, setStage] = useState(snap.stage?.number ?? 1);
  const [started, setStarted] = useState(snap.stage?.started ?? today());
  const [includePast, setIncludePast] = useState(false);
  const [night, setNight] = useState(snap.night_lighting);
  const [preview, setPreview] = useState<Preview | null>(null);
  const [previewError, setPreviewError] = useState<string | null>(null);
  const { run, busy } = useAction();

  useEffect(() => {
    api.templates().then(setTemplates);
    api.plans(snap.id).then(setPlans);
  }, []);

  // Learn the stage names/lengths of whatever was picked.
  useEffect(() => {
    if (!source) return;
    const load = source.kind === "plan" ? Promise.resolve(plans[source.id]) : api.template(source.id);
    load.then((p) => {
      if (!p) return;
      setStageNames(p.stages.map((s) => ({ name: s.name, days: s.days })));
      setStage((current) => Math.min(Math.max(current, 1), p.stages.length));
    });
  }, [source?.kind, source?.id, plans]);

  const stageInfo = stageNames[stage - 1];
  const dayOfStage = daysBetween(started, today()) + 1;

  const args = useMemo(
    (): StartArgs => ({
      ...(source?.kind === "plan" ? { plan: source.id } : { template: source?.id, role_map: roles }),
      stage,
      stage_started: started,
      include_past_tasks: includePast,
    }),
    [source?.kind, source?.id, roles, stage, started, includePast],
  );

  useEffect(() => {
    if (step !== 3 || !source) return;
    setPreview(null);
    setPreviewError(null);
    api.previewStart(snap.id, args).then(setPreview).catch((e: unknown) => setPreviewError(e instanceof ApiError ? e.message : String(e)));
  }, [step, args]);

  const pick = (next: Source) => {
    setSource(next);
    setStep(next?.kind === "template" ? 1 : 2);
  };

  const confirm = async () => {
    if (!source) return;
    const result = await run(async () => {
      let planId = source.kind === "plan" ? source.id : "";
      let created = false;
      if (source.kind === "template") {
        planId = (await api.createPlan(snap.id, { template: source.id, role_map: roles })).plan_id;
        created = true;
      }
      try {
        return await api.startGrow(snap.id, {
          plan: planId,
          stage,
          stage_started: started,
          include_past_tasks: includePast,
          night_lighting: night,
        });
      } catch (err) {
        if (created) await api.deletePlan(snap.id, planId).catch(() => {});
        throw err;
      }
    }, "Grow started");
    if (result) onDone(result);
  };

  const back = () => {
    if (step === 2 && source?.kind === "plan") setStep(0);
    else setStep(Math.max(0, step - 1));
  };

  return (
    <Dialog title={snap.active ? "Change grow" : "Start a grow"} onClose={onClose}>
      <div class="steps" aria-label="Steps">
        {STEPS.map((label, i) => <span key={label} class={i === step ? "on" : ""}>{i + 1}. {label}</span>)}
      </div>

      {step === 0 ? (
        <div class="stack" style="max-height:50vh;overflow:auto">
          {Object.keys(plans).length ? (
            <>
              <h3 class="muted">My plans</h3>
              {Object.entries(plans).map(([id, p]) => (
                <button class="btn" style="text-align:left" key={id} onClick={() => pick({ kind: "plan", id })}>
                  {p.name} <span class="muted small">— {p.stages.length} stages</span>
                </button>
              ))}
              <h3 class="muted">Templates</h3>
            </>
          ) : null}
          {templates.map((t) => (
            <button class="btn" style="text-align:left" key={t.id} onClick={() => pick({ kind: "template", id: t.id })}>
              {t.name} <span class="muted small">— {t.stage_count} stages, {t.total_days} days{t.builtin ? "" : " · mine"}</span>
            </button>
          ))}
        </div>
      ) : null}

      {step === 1 ? (
        <>
          <p class="muted small">Templates describe lights and a pump by role. Choose which of your devices plays each one.</p>
          <RoleMapper roles={meta.roles} devices={snap.devices} value={roles} onChange={setRoles} />
        </>
      ) : null}

      {step === 2 ? (
        <div class="stack">
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
          <label class="row"><Switch label="Night lighting" checked={night} onChange={setNight} /> Night lighting (lights run 12 hours shifted)</label>
        </div>
      ) : null}

      {step === 3 ? (
        previewError ? <p class="error-text" role="alert">{previewError}</p> : !preview ? <p class="muted">Working it out…</p> : <Review p={preview} replacing={snap.active} />
      ) : null}

      <div class="row" style="justify-content:space-between">
        <button class="btn" onClick={step === 0 ? onClose : back}>{step === 0 ? "Cancel" : "Back"}</button>
        {step === 3 ? (
          <button class="btn primary" disabled={busy || !preview} onClick={confirm}>{snap.active ? "Switch to this grow" : "Start grow"}</button>
        ) : step > 0 ? (
          <button class="btn primary" disabled={!source || (step === 2 && stageNames.length === 0)} onClick={() => setStep(step + 1)}>Next</button>
        ) : <span />}
      </div>
    </Dialog>
  );
}

function Review({ p, replacing }: { p: Preview; replacing: boolean }) {
  return (
    <div class="stack" style="max-height:55vh;overflow:auto">
      {replacing ? <div class="callout small">This replaces the running grow. Its task progress is reset.</div> : null}
      <div>
        <strong>{p.plan}</strong>
        <div class="muted small">
          Stage {p.stage_number} of {p.stage_count}: {p.stage} — day {p.stage_day} of {p.stage_days}
          <br />Grow started {shortDate(p.grow_started)} · expected end {shortDate(p.expected_end)}
        </div>
      </div>
      <div>
        <h3>Right now</h3>
        {p.devices.map((d, i) => (
          <div class="row" key={i}><span class="grow">{d.name}</span>{d.desired === null ? <Badge>left alone</Badge> : <Badge kind={d.desired ? "ok" : undefined}>{d.desired ? "on" : "off"}</Badge>}</div>
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
