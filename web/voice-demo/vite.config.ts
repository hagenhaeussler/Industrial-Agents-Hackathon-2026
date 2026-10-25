import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// The voice server (python -m voice_agent serve) issues conversation tokens.
// Set VOICE_SERVER to use a deployed server instead, for example the Railway URL.
const voiceServer = process.env.VOICE_SERVER ?? "http://127.0.0.1:8000";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: { proxy: { "/api": { target: voiceServer, changeOrigin: true } } },
});
