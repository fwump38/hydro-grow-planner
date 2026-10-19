import { useCallback, useEffect, useRef, useState } from "preact/hooks";

import { api, watch } from "./api";
import { Activity } from "./Activity";
import { confirmLeave } from "./guard";
import { Overview } from "./Overview";
import { Plans } from "./Plans";
import { Settings } from "./Settings";
import { Templates } from "./Templates";
import { Wizard } from "./Wizard";
import type { Meta, Snapshot, SystemRow } from "./types";
import { ToastContext, useAction, useToastState } from "./ui";

const TABS = [
  ["overview", "Overview"],
  ["plans", "Plan"],
  ["templates", "Templates"],
  ["activity", "Activity"],
  ["settings", "Settings"],
] as const;
type Tab = (typeof TABS)[number][0];

function readHash(): Tab {
  const name = window.location.hash.replace(/^#\/?/, "");
  return (TABS.find(([key]) => key === name)?.[0] ?? "overview") as Tab;
}

function remembered(): string | null {
  try {
    return localStorage.getItem("grow-system");
  } catch {
    return null;
  }
}

function Welcome({ onCreated }: { onCreated: (id: string) => void }) {
  const [name, setName] = useState("Grow System");
  const { run, busy } = useAction();
  return (
    <form
      class="card empty"
      onSubmit={async (e) => {
        e.preventDefault();
        const created = await run(() => api.createSystem(name));
        if (created) onCreated(created.id);
      }}
    >
      <h2>Welcome</h2>
      <p class="muted">
        A grow system is one tower or tray: its lights, pump and sensors. Name yours, then add the devices next.
      </p>
      <input
        type="text"
        aria-label="System name"
        style="max-width:320px"
        value={name}
        onInput={(e) => setName((e.currentTarget as HTMLInputElement).value)}
      />
      <button class="btn primary" type="submit" disabled={busy || !name.trim()}>Create grow system</button>
    </form>
  );
}

export function App() {
  const { toast, notify } = useToastState();
  const [tab, setTab] = useState<Tab>(readHash());
  const [meta, setMeta] = useState<Meta | null>(null);
  const [systems, setSystems] = useState<SystemRow[] | null>(null);
  const [sid, setSid] = useState<string | null>(remembered());
  const [snap, setSnap] = useState<Snapshot | null>(null);
  const [wizard, setWizard] = useState<{ template?: string; plan?: string; replace?: string } | null>(null);
  const [error, setError] = useState<string | null>(null);
  const sidRef = useRef(sid);
  sidRef.current = sid;

  useEffect(() => {
    const onHash = () => setTab(readHash());
    window.addEventListener("hashchange", onHash);
    return () => window.removeEventListener("hashchange", onHash);
  }, []);

  const loadSystems = useCallback(async () => {
    try {
      const rows = await api.systems();
      setSystems(rows);
      setError(null);
      const current = rows.find((r) => r.id === sidRef.current) ?? rows[0];
      setSid(current ? current.id : null);
      if (current) {
        try {
          localStorage.setItem("grow-system", current.id);
        } catch {
          /* private mode */
        }
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  }, []);

  const reload = useCallback(async () => {
    if (!sidRef.current) return;
    try {
      setSnap(await api.system(sidRef.current));
    } catch {
      /* the next change event retries */
    }
  }, []);

  useEffect(() => {
    api.meta().then(setMeta).catch((e) => setError(String(e)));
    loadSystems();
  }, []);
  useEffect(() => {
    setSnap(null);
    reload();
  }, [sid]);
  useEffect(() => {
    let timer: number | undefined;
    const stop = watch(() => {
      window.clearTimeout(timer);
      timer = window.setTimeout(() => {
        reload();
        loadSystems();
      }, 150);
    });
    return () => {
      stop();
      window.clearTimeout(timer);
    };
  }, []);

  const go = (next: Tab) => {
    if (next !== tab && !confirmLeave()) return;
    window.location.hash = `#/${next}`;
  };
  const select = (id: string) => {
    if (id !== sid && !confirmLeave()) return;
    setSid(id);
  };

  if (error && !systems) {
    return <div class="shell"><div class="card page" role="alert">Can't reach the app: {error}</div></div>;
  }
  if (!systems || !meta) return <div class="shell"><p class="muted page">Loading…</p></div>;

  return (
    <ToastContext.Provider value={notify}>
      <div class="shell">
        <header class="topbar">
          <div class="row between">
            <h1 style="font-size:1.25rem">🌱 Grow Planner</h1>
            {systems.length > 1 ? (
              <select aria-label="Grow system" style="width:auto" value={sid ?? ""} onChange={(e) => select((e.currentTarget as HTMLSelectElement).value)}>
                {systems.map((s) => <option value={s.id} key={s.id}>{s.name}</option>)}
              </select>
            ) : null}
          </div>
          <nav class="tabs" aria-label="Sections">
            {TABS.map(([key, label]) => (
              <button key={key} class="tab" aria-current={tab === key ? "page" : undefined} onClick={() => go(key)}>{label}</button>
            ))}
          </nav>
        </header>
        <main class="page">
          {systems.length === 0 ? (
            <Welcome
              onCreated={async (id) => {
                try {
                  localStorage.setItem("grow-system", id);
                } catch {
                  /* private mode */
                }
                setSid(id);
                await loadSystems();
                go("settings");
              }}
            />
          ) : !snap ? (
            <p class="muted">Loading…</p>
          ) : tab === "overview" ? (
            <Overview snap={snap} onSnap={setSnap} onStart={(replace) => setWizard({ replace })} />
          ) : tab === "plans" ? (
            <Plans snap={snap} meta={meta} onSnap={setSnap} onStart={(plan) => setWizard({ plan })} />
          ) : tab === "templates" ? (
            <Templates meta={meta} ecUnit={snap.ec_unit} onUse={(template) => setWizard({ template })} />
          ) : tab === "activity" ? (
            <Activity snap={snap} />
          ) : (
            <Settings snap={snap} meta={meta} systems={systems} onSnap={setSnap} onSelect={select} onChanged={loadSystems} />
          )}
        </main>
        {wizard && snap ? (
          <Wizard
            snap={snap}
            meta={meta}
            initial={wizard}
            onClose={() => setWizard(null)}
            onDone={(next) => {
              setSnap(next);
              setWizard(null);
              go("overview");
            }}
          />
        ) : null}
        {toast ? <div class={`toast ${toast.kind}`} role="status">{toast.message}</div> : null}
      </div>
    </ToastContext.Provider>
  );
}
