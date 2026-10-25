import { defineConfig } from "vitest/config";

// The playground is a development page. It reads buildings from the Python API (python -m building_api serve).
export default defineConfig({
  root: "playground",
  server: { proxy: { "/api": process.env.BUILDING_API ?? "http://127.0.0.1:8000" } },
  build: { outDir: "../dist-playground", emptyOutDir: true },
  test: { root: ".", include: ["src/**/*.test.ts"] },
});
