// Regenerates src/api/schema.gen.ts from ../../server/openapi.json.
// openapi-typescript needs the TypeScript 5 compiler API, while the app compiles with TypeScript 7,
// so the generator runs from its own pinned tool directory.
import { existsSync, mkdirSync, writeFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';

const app = fileURLToPath(new URL('..', import.meta.url));
const tool = `${app}node_modules/.cache/openapi-gen`;
if (!existsSync(`${tool}/node_modules/.bin/openapi-typescript`)) {
  mkdirSync(tool, { recursive: true });
  writeFileSync(`${tool}/package.json`, JSON.stringify({ name: 'openapi-gen', private: true }));
  Bun.spawnSync(['bun', 'add', '--exact', 'openapi-typescript@7.13.0', 'typescript@5.9.3'], { cwd: tool, stdout: 'inherit', stderr: 'inherit' });
}
const run = Bun.spawnSync([`${tool}/node_modules/.bin/openapi-typescript`, `${app}../../server/openapi.json`, '-o', `${app}src/api/schema.gen.ts`], { stdout: 'inherit', stderr: 'inherit' });
process.exit(run.exitCode ?? 1);
