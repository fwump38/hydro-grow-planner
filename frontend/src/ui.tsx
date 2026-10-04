// Small shared UI building blocks.

import type { ComponentChildren } from "preact";
import { createContext } from "preact";
import { useContext, useEffect, useRef, useState } from "preact/hooks";

import { ApiError } from "./api";

// -- toasts ---------------------------------------------------------------------------

type Notify = (message: string, kind?: "ok" | "bad") => void;
export const ToastContext = createContext<Notify>(() => {});
export const useToast = () => useContext(ToastContext);

export function useToastState() {
  const [toast, setToast] = useState<{ message: string; kind: "ok" | "bad" } | null>(null);
  const timer = useRef<number>();
  const notify: Notify = (message, kind = "ok") => {
    setToast({ message, kind });
    window.clearTimeout(timer.current);
    timer.current = window.setTimeout(() => setToast(null), kind === "bad" ? 6000 : 2500);
  };
  return { toast, notify };
}

/** Run an action, showing any error as a toast. Returns whether it succeeded. */
export function useAction() {
  const notify = useToast();
  const [busy, setBusy] = useState(false);
  const run = async <T,>(action: () => Promise<T>, success?: string): Promise<T | undefined> => {
    setBusy(true);
    try {
      const result = await action();
      if (success) notify(success);
      return result;
    } catch (err) {
      notify(err instanceof ApiError || err instanceof Error ? err.message : String(err), "bad");
      return undefined;
    } finally {
      setBusy(false);
    }
  };
  return { run, busy };
}

// -- form pieces ------------------------------------------------------------------------

export function Field(props: {
  label: string;
  error?: string;
  hint?: string;
  children: ComponentChildren;
  class?: string;
}) {
  return (
    <label class={`field ${props.error ? "invalid" : ""} ${props.class ?? ""}`}>
      <span class="label">{props.label}</span>
      {props.children}
      {props.error ? <span class="error-text">{props.error}</span> : null}
      {props.hint && !props.error ? <span class="small">{props.hint}</span> : null}
    </label>
  );
}

export function Segmented<T extends string>(props: {
  value: T;
  options: { value: T; label: string }[];
  onChange: (value: T) => void;
  label?: string;
}) {
  return (
    <div class="seg" role="group" aria-label={props.label}>
      {props.options.map((o) => (
        <button
          type="button"
          key={o.value}
          aria-pressed={props.value === o.value}
          onClick={() => props.onChange(o.value)}
        >
          {o.label}
        </button>
      ))}
    </div>
  );
}

export function Switch(props: {
  checked: boolean;
  onChange: (checked: boolean) => void;
  label: string;
  disabled?: boolean;
}) {
  return (
    <span class="switch">
      <input
        type="checkbox"
        role="switch"
        aria-label={props.label}
        checked={props.checked}
        disabled={props.disabled}
        onChange={(e) => props.onChange((e.currentTarget as HTMLInputElement).checked)}
      />
      <span class="track" />
    </span>
  );
}

/** A number field that keeps what you type (including "6.") and reports a number or null. */
export function NumberInput(props: {
  value: number | null | undefined;
  onChange: (value: number | null) => void;
  step?: number | string;
  min?: number;
  max?: number;
  placeholder?: string;
  ariaLabel?: string;
}) {
  const [text, setText] = useState(props.value == null ? "" : String(props.value));
  const last = useRef(props.value);
  useEffect(() => {
    if (props.value !== last.current && Number(text) !== props.value) {
      setText(props.value == null ? "" : String(props.value));
    }
    last.current = props.value;
  }, [props.value]);
  return (
    <input
      type="number"
      inputMode="decimal"
      aria-label={props.ariaLabel}
      value={text}
      step={props.step ?? "any"}
      min={props.min}
      max={props.max}
      placeholder={props.placeholder}
      onInput={(e) => {
        const raw = (e.currentTarget as HTMLInputElement).value;
        setText(raw);
        const parsed = raw.trim() === "" ? null : Number(raw);
        last.current = parsed !== null && Number.isFinite(parsed) ? parsed : null;
        props.onChange(last.current);
      }}
    />
  );
}

// -- dialogs -----------------------------------------------------------------------------

export function Dialog(props: {
  title: string;
  children: ComponentChildren;
  onClose: () => void;
}) {
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && props.onClose();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);
  return (
    <div class="dialog-backdrop" onClick={props.onClose}>
      <div class="dialog" role="dialog" aria-modal="true" aria-label={props.title} onClick={(e) => e.stopPropagation()}>
        <h2>{props.title}</h2>
        {props.children}
      </div>
    </div>
  );
}

/** A button that asks before doing something destructive. */
export function ConfirmButton(props: {
  label: string;
  question: string;
  confirmLabel?: string;
  onConfirm: () => void;
  class?: string;
  disabled?: boolean;
}) {
  const [open, setOpen] = useState(false);
  return (
    <>
      <button type="button" class={`btn ${props.class ?? ""}`} disabled={props.disabled} onClick={() => setOpen(true)}>
        {props.label}
      </button>
      {open ? (
        <Dialog title={props.label} onClose={() => setOpen(false)}>
          <p>{props.question}</p>
          <div class="row" style="justify-content:flex-end">
            <button type="button" class="btn" onClick={() => setOpen(false)}>Cancel</button>
            <button
              type="button"
              class="btn primary"
              onClick={() => {
                setOpen(false);
                props.onConfirm();
              }}
            >
              {props.confirmLabel ?? "Confirm"}
            </button>
          </div>
        </Dialog>
      ) : null}
    </>
  );
}

export function Badge(props: { kind?: "ok" | "warn" | "bad" | "accent"; children: ComponentChildren }) {
  return <span class={`badge ${props.kind ?? ""}`}>{props.children}</span>;
}

export function errorAt(errors: { path: string; message: string }[], path: string): string | undefined {
  return errors.find((e) => e.path === path)?.message;
}
