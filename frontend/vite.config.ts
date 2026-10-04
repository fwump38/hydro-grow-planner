import preact from "@preact/preset-vite";
import { defineConfig } from "vitest/config";

// Home Assistant serves the panel under a long ingress path, so every URL must be
// relative ("./"), never root-relative.
export default defineConfig({
  base: "./",
  plugins: [preact()],
  build: { outDir: "../backend/grow_planner/static", emptyOutDir: true },
  server: { proxy: { "/api": "http://localhost:8099" } },
  test: { environment: "node", include: ["src/**/*.test.ts"] },
});
