import { fileURLToPath } from 'node:url';
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

const repo = fileURLToPath(new URL('../..', import.meta.url));
const api = process.env.TYB_API ?? 'http://127.0.0.1:8000';

export default defineConfig(({ command }) => ({
  plugins: [react()],
  // dev only: lets `?mock=1` read any kit building from data/ (production builds get an empty string)
  define: { 'import.meta.env.TYB_REPO_ROOT': JSON.stringify(command === 'serve' ? repo : '') },
  // demo/scenario.json and data/ live at the repository root
  server: { fs: { allow: [repo] }, proxy: { '/api': api, '/health': api, '/ws': { target: api, ws: true } } },
}));
