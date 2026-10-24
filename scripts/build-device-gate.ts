/** Run after the normal SPA build: bun scripts/build-device-gate.ts (from repo root). */
import { resolve } from 'node:path'

const repo = resolve(import.meta.dir, '..')
const app = resolve(repo, 'web/app')
const entry = resolve(app, 'src/camera/ar/deviceGatePage.ts')
if (!await Bun.file(entry).exists()) throw new Error('Device-gate source is not present in web/app.')
const result = await Bun.build({
  entrypoints: [entry], outdir: resolve(app, 'dist'), naming: 'devtest.js', target: 'browser', format: 'esm', minify: true,
})
if (!result.success) {
  for (const log of result.logs) console.error(log)
  process.exit(1)
}
// Vite copies public/devtest.html; also copy here for direct device-gate-only builds.
await Bun.write(resolve(app, 'dist/devtest.html'), Bun.file(resolve(app, 'public/devtest.html')))
console.log(`Device gate bundled: ${result.outputs.map(output => `${output.path} (${output.size} bytes)`).join(', ')}`)
