import type { Snapshot } from "./types";
import { Badge } from "./ui";

const KINDS: Record<string, "ok" | "warn" | "bad" | "accent" | undefined> = {
  alert: "bad",
  device: "accent",
  reading: "ok",
  stage: "warn",
  grow: "warn",
};

export function Activity({ snap }: { snap: Snapshot }) {
  if (snap.activity.length === 0) return <div class="card empty muted">Nothing has happened yet.</div>;
  return (
    <section class="card">
      <h2>Activity</h2>
      {snap.activity.map((a, i) => {
        const at = new Date(a.at);
        return (
          <div class="task" key={i}>
            <span class="muted small nowrap" style="width:130px">
              {at.toLocaleDateString(undefined, { month: "short", day: "numeric" })}{" "}
              {at.toLocaleTimeString(undefined, { hour: "2-digit", minute: "2-digit" })}
            </span>
            <Badge kind={KINDS[a.kind]}>{a.kind}</Badge>
            <span class="grow">{a.message}</span>
          </div>
        );
      })}
    </section>
  );
}
