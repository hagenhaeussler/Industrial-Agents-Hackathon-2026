import { fileURLToPath } from 'node:url';
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

const repo = fileURLToPath(new URL('../..', import.meta.url));
const api = process.env.TYB_API ?? 'http://127.0.0.1:8000';

export default defineConfig({
  plugins: [react()],
  // demo/scenario.json lives at the repository root
  server: { fs: { allow: [repo] }, proxy: { '/api': api, '/health': api, '/ws': { target: api, ws: true } } },
});
