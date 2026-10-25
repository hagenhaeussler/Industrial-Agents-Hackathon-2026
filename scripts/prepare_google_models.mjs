/** Derived GLBs from building.json only; no provider requests or keys. Run from the repository root. */
import {createRequire} from 'node:module';
import {readFile,mkdir,writeFile} from 'node:fs/promises';
import {createHash} from 'node:crypto';
import {execFileSync} from 'node:child_process';
import path from 'node:path';
const require = createRequire(new URL('../web/package.json',import.meta.url));
const {createServer} = await import(require.resolve('vite'));
// Three's exporter uses FileReader in browsers. Node provides Blob and ArrayBuffer, so adapt the read.
globalThis.FileReader = class {
  result = null; onloadend = null;
  readAsArrayBuffer(blob) { void blob.arrayBuffer().then(result => {this.result=result;this.onloadend?.();}); }
};
const [sourcePath] = process.argv.slice(2);
if (!sourcePath || path.basename(sourcePath) !== 'building.json') throw new Error('Pass the source building.json path');
const source = await readFile(sourcePath,'utf8'), document = JSON.parse(source);
const cataloguePath = 'web/public/maps/buildings.json';
const catalogue = JSON.parse(await readFile(cataloguePath,'utf8'));
const building = catalogue.buildings.find(b => b.id === document.building.id);
if (!building?.localFrame) throw new Error('A verified geographic frame is required');
const server = await createServer({configFile:false,root:path.resolve('web'),cacheDir:path.resolve('web/node_modules/.vite-google-models'),server:{middlewareMode:true,hmr:false,ws:false,watch:null},appType:'custom'});
try {
  const {compileScene} = await server.ssrLoadModule('/@fs/'+path.resolve('packages/building-view/src/scene/compile.ts'));
  const {floorGlb} = await server.ssrLoadModule('/@fs/'+path.resolve('packages/building-view/src/export/FloorGlb.ts'));
  const {planToModel} = await server.ssrLoadModule('/src/explore/model-placement.ts');
  const scene = compileScene(document);
  const prefix = '/maps/models/'+encodeURIComponent(building.id);
  const folder = path.resolve('web/public'+prefix);
  await mkdir(folder,{recursive:true});
  const floors=[],rooms={};
  await mkdir(path.join(folder,'rooms'),{recursive:true});
  for (const [index,floor] of scene.floors.entries()) {
    const data = await floorGlb(floor,point => planToModel(building,point));
    const hash = createHash('sha256').update(Buffer.from(data)).digest('hex').slice(0,12);
    const file = `floor-${index}-${hash}.glb`;
    await writeFile(path.join(folder,file),Buffer.from(data));
    floors.push({id:floor.id,level:floor.level,elevation:floor.elevation,height:floor.height,src:prefix+'/'+file});
    for (const room of floor.spaces.filter(s=>s.type==='room')) {
      const bytes=Buffer.from(await floorGlb({...floor,spaces:[room],walls:[],assets:[]},point=>planToModel(building,point),{spaceColor:'#dcff58',lift:.18}));
      const roomFile='room-'+createHash('sha256').update(room.id).digest('hex').slice(0,16)+'-'+createHash('sha256').update(bytes).digest('hex').slice(0,12)+'.glb';
      await writeFile(path.join(folder,'rooms',roomFile),bytes);rooms[room.id]=prefix+'/rooms/'+roomFile;
    }
    console.log(`${floor.name}: ${(data.byteLength/1024).toFixed(0)} KiB`);
  }
  const sha = value => createHash('sha256').update(value).digest('hex');
  const mask = JSON.parse(execFileSync(process.env.MODEL_PYTHON ?? path.resolve('.venv/bin/python'),['-c',
    'import sys,json; from scripts.prepare_campus import google_mask; b=json.load(sys.stdin); print(json.dumps(google_mask(b["outline"],b["center"][1])))'],
    {input:JSON.stringify({outline:building.outline,center:building.center}),encoding:'utf8'}));
  const manifest = {buildingId:building.id,sourceSha256:sha(source),frameSha256:sha(JSON.stringify(building.localFrame)),anchor:building.center,mask,maskPaddingM:3,floors,rooms};
  await writeFile(path.join(folder,'manifest.json'),JSON.stringify(manifest)+'\n');
  building.googleIndoorModel = prefix+'/manifest.json';
  await writeFile(cataloguePath,JSON.stringify(catalogue)+'\n');
  console.log(`Prepared ${Object.keys(rooms).length} room highlights; loaded individually on selection.`);
} finally { await server.close(); }
