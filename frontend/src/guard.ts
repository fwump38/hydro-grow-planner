// Unsaved-changes guard: editors register themselves while dirty, and navigation
// asks before throwing the edits away.

let dirty = false;

export function setDirty(value: boolean): void {
  dirty = value;
  window.onbeforeunload = value ? () => "" : null;
}

export function confirmLeave(): boolean {
  return !dirty || window.confirm("You have unsaved changes. Leave without saving?");
}
