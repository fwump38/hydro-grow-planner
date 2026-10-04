// The panel is served from Home Assistant's own origin (ingress), so it can read
// the active theme's colours from the parent page and follow light/dark mode.

const VARS = [
  "--primary-color",
  "--primary-background-color",
  "--card-background-color",
  "--primary-text-color",
  "--secondary-text-color",
  "--divider-color",
  "--error-color",
  "--success-color",
  "--warning-color",
];

function brightness(color: string): number | null {
  const m = color.trim().match(/^#([0-9a-f]{3}|[0-9a-f]{6})$/i);
  if (m) {
    const hex = m[1].length === 3 ? [...m[1]].map((c) => c + c).join("") : m[1];
    const [r, g, b] = [0, 2, 4].map((i) => parseInt(hex.slice(i, i + 2), 16));
    return (r * 299 + g * 587 + b * 114) / 1000;
  }
  const rgb = color.match(/rgba?\((\d+)[ ,]+(\d+)[ ,]+(\d+)/);
  if (rgb) return (Number(rgb[1]) * 299 + Number(rgb[2]) * 587 + Number(rgb[3]) * 114) / 1000;
  return null;
}

function apply(): boolean {
  try {
    const parent = window.parent.document.documentElement;
    if (parent === document.documentElement) return false;
    const style = window.parent.getComputedStyle(parent);
    let found = false;
    for (const name of VARS) {
      const value = style.getPropertyValue(name).trim();
      if (value) {
        document.documentElement.style.setProperty(name, value);
        found = true;
      }
    }
    const background = style.getPropertyValue("--primary-background-color");
    const level = background ? brightness(background) : null;
    if (level !== null) {
      document.documentElement.dataset.theme = level < 128 ? "dark" : "light";
    }
    return found;
  } catch {
    return false; // not embedded, or cross-origin: fall back to the system theme
  }
}

export function initTheme(): void {
  if (!apply()) return;
  try {
    const observer = new MutationObserver(apply);
    observer.observe(window.parent.document.documentElement, {
      attributes: true,
      attributeFilter: ["style", "class"],
    });
  } catch {
    /* ignore */
  }
}
