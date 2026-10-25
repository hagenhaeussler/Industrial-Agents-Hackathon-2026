import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

// Development proxies. The building API serves buildings and routes (python -m building_api serve).
// The voice server issues ElevenLabs conversation tokens; it runs on Railway, so no local voice server is needed.
const buildingApi = process.env.BUILDING_API ?? "http://127.0.0.1:8010";
const voiceServer = process.env.VOICE_SERVER ?? "https://voice-agent-production-653b.up.railway.app";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    proxy: {
      "/api/voice": { target: voiceServer, changeOrigin: true },
      "/api": { target: buildingApi, changeOrigin: true },
    },
  },
  test: { environment: "happy-dom", include: ["src/**/*.test.{ts,tsx}"] },
});
