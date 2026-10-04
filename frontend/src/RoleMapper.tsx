import type { DeviceRef } from "./roles";
import { Field } from "./ui";

/** One dropdown per template role, choosing which of your devices plays it. */
export function RoleMapper(props: {
  roles: Record<string, string>;
  devices: DeviceRef[];
  value: Record<string, string>;
  onChange: (value: Record<string, string>) => void;
}) {
  return (
    <div class="stack">
      {Object.entries(props.roles).map(([role, label]) => (
        <Field label={label} key={role}>
          <select
            value={props.value[role] ?? ""}
            onChange={(e) => props.onChange({ ...props.value, [role]: (e.currentTarget as HTMLSelectElement).value })}
          >
            <option value="">— not used —</option>
            {props.devices.map((d) => (
              <option value={d.id} key={d.id}>{d.name} ({d.entity_id})</option>
            ))}
          </select>
        </Field>
      ))}
      {props.devices.length === 0 ? <p class="muted small">Add devices under Settings first.</p> : null}
    </div>
  );
}
