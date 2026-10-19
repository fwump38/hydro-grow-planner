import type { DeviceRef, RoleMap } from "./roles";
import { Field } from "./ui";

/**
 * For each template role, tick which of your devices play it. A role can drive several
 * devices (one plug per pair of layers); a device can only play one role.
 * `note` adds a hint after a device's name, e.g. which grow already uses it.
 */
export function RoleMapper(props: {
  roles: Record<string, string>;
  devices: DeviceRef[];
  value: RoleMap;
  onChange: (value: RoleMap) => void;
  note?: (deviceId: string) => string | undefined;
}) {
  const roleOf = (deviceId: string) => Object.keys(props.value).find((r) => props.value[r]?.includes(deviceId));
  const toggle = (role: string, deviceId: string, on: boolean) => {
    const current = props.value[role] ?? [];
    props.onChange({
      ...props.value,
      [role]: on ? [...current.filter((d) => d !== deviceId), deviceId] : current.filter((d) => d !== deviceId),
    });
  };
  return (
    <div class="stack">
      {Object.entries(props.roles).map(([role, label]) => (
        <Field label={label} key={role}>
          <div class="stack" style="gap:4px" role="group" aria-label={label}>
            {props.devices.map((d) => {
              const elsewhere = roleOf(d.id);
              const takenByOther = elsewhere !== undefined && elsewhere !== role;
              const note = props.note?.(d.id);
              return (
                <label class="check" key={d.id} style={takenByOther ? "opacity:.5" : ""}>
                  <input
                    type="checkbox"
                    checked={props.value[role]?.includes(d.id) ?? false}
                    disabled={takenByOther}
                    onChange={(e) => toggle(role, d.id, (e.currentTarget as HTMLInputElement).checked)}
                  />
                  {d.name} <span class="muted small">({d.entity_id}){note ? ` · ${note}` : ""}</span>
                </label>
              );
            })}
            {props.devices.length ? <span class="muted small">{props.value[role]?.length ? "" : "Not used"}</span> : null}
          </div>
        </Field>
      ))}
      {props.devices.length === 0 ? <p class="muted small">Add devices under Settings first.</p> : null}
    </div>
  );
}
