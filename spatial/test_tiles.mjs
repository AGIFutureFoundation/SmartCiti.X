/**
 * The world tiles, held by their bytes.
 *
 * spatial/build.py cuts the GIS-based worlds (13 Louisiana parishes, 9 Bay
 * Area counties, 4 authored wilds, the campuses that have halls) into glTF 2.0
 * binary tiles, and writes one plain-JSON manifest per
 * world in the shape the Sneeze project's own example docs 01 and 02 show.
 *
 * WHAT THIS SUITE HOLDS. Every tile is a valid glTF 2.0 container by its own
 * bytes (magic, version, declared length, JSON chunk, BIN chunk, buffer
 * length, bufferView and accessor bounds, POSITION min/max equal to the data,
 * every index in range, every float finite, normals unit length, no
 * extension, no texture); every anchor is a GeoPose Basic-YPR exactly and
 * equals the registry that owns its position; every tile is inside its byte
 * budget; every tile and layer carries a provenance word and the tile takes
 * the weakest; the manifests use only fields the field table lists, and the
 * table marks each field documented (with the Sneeze URL) or proposed.
 *
 * WHAT IT DOES NOT HOLD. That Sneeze or Artemis loads any of it. Nothing was
 * run in either. The suite says so in its last line.
 *
 * The validator is `validateGlb`; its own drills (mutated bytes -> the named
 * rule fails) run first, so a green run shows the detectors work.
 */
import { createHash } from 'node:crypto';
import { existsSync, readFileSync, statSync, readdirSync, mkdtempSync, rmSync } from 'node:fs';
import { pathToFileURL } from 'node:url';
import { extname } from 'node:path';
import { execFileSync } from 'node:child_process';
import { tmpdir } from 'node:os';
import { join } from 'node:path';

let n = 0;
const ok = (m, c) => { if (!c) { console.error('FAIL', m); process.exit(1); } n++; console.log('  ok ', m); };

const HERE = new URL('.', import.meta.url);
const ROOTP = new URL('..', import.meta.url).pathname;
const R = (p) => JSON.parse(readFileSync(new URL(p, import.meta.url)));
const sha = (b) => createHash('sha256').update(b).digest('hex');

// ---- ceilings this suite owns: the builder's budget may not be raised past them
const CEIL_TILE_BYTES = 750_000;
const CEIL_TOTAL_BYTES = 8_000_000;
const SREF_MAX = 128;
const TIERS = ['RECORDED', 'DERIVED', 'SCHEMATIC', 'AUTHORED'];
const FLAT_LAYERS = /^(ground|water|streets-collector|streets-arterial|terrain)$/;
const UNKNOWN_H = 'UNKNOWN - not held by this bundle; 0.0 is a placeholder, not a measurement';

// ------------------------------------------------------------ the validator ---
const COMP = { 5120: 1, 5121: 1, 5122: 2, 5123: 2, 5125: 4, 5126: 4 };
const NCOMP = { SCALAR: 1, VEC2: 2, VEC3: 3, VEC4: 4, MAT4: 16 };

/** Returns { fails: [ruleName...], gltf, bin, reads } for one .glb buffer. */
function validateGlb(buf) {
  const fails = [];
  const bad = (rule) => { if (!fails.includes(rule)) fails.push(rule); };
  let gltf = null, bin = null;
  const reads = {};
  if (buf.length < 20 || buf.toString('latin1', 0, 4) !== 'glTF') { bad('magic'); return { fails, gltf, bin, reads }; }
  if (buf.readUInt32LE(4) !== 2) bad('version');
  if (buf.readUInt32LE(8) !== buf.length) bad('declared-length');
  if (buf.length % 4 !== 0) bad('four-byte-aligned');
  let off = 12;
  const chunks = [];
  while (off + 8 <= buf.length) {
    const len = buf.readUInt32LE(off), type = buf.toString('latin1', off + 4, off + 8);
    if (off + 8 + len > buf.length) { bad('chunk-overrun'); break; }
    if (len % 4 !== 0) bad('chunk-aligned');
    chunks.push({ type, start: off + 8, len });
    off += 8 + len;
  }
  if (off !== buf.length) bad('chunk-overrun');
  if (!chunks.length || chunks[0].type !== 'JSON') { bad('json-chunk-first'); return { fails, gltf, bin, reads }; }
  try { gltf = JSON.parse(buf.toString('utf8', chunks[0].start, chunks[0].start + chunks[0].len)); } catch { bad('json-parse'); return { fails, gltf, bin, reads }; }
  const binChunk = chunks[1];
  if (!binChunk || binChunk.type !== 'BIN\0') bad('bin-chunk');
  else bin = buf.subarray(binChunk.start, binChunk.start + binChunk.len);
  if (!gltf.asset || gltf.asset.version !== '2.0') bad('asset-version');
  if ((gltf.extensionsRequired ?? []).length || (gltf.extensionsUsed ?? []).length) bad('no-extensions');
  if ((gltf.images ?? []).length || (gltf.textures ?? []).length) bad('no-textures');
  if ((gltf.animations ?? []).length || (gltf.skins ?? []).length) bad('no-animation-or-skin');
  if (!gltf.buffers || gltf.buffers.length !== 1 || !bin || gltf.buffers[0].byteLength > bin.length || bin.length - gltf.buffers[0].byteLength > 3) bad('buffer-length');
  const views = gltf.bufferViews ?? [], acc = gltf.accessors ?? [];
  for (const v of views) {
    if (!bin || v.buffer !== 0 || v.byteOffset + v.byteLength > bin.length || v.byteOffset % 4 !== 0) bad('view-bounds');
  }
  const accRead = (ai) => {
    const a = acc[ai], v = views[a?.bufferView];
    if (!a || !v || !bin) { bad('accessor-bounds'); return null; }
    const cs = COMP[a.componentType], nc = NCOMP[a.type];
    if (!cs || !nc) { bad('accessor-bounds'); return null; }
    if ((a.byteOffset ?? 0) % cs !== 0 || (a.byteOffset ?? 0) + a.count * nc * cs > v.byteLength) { bad('accessor-bounds'); return null; }
    const out = new Array(a.count * nc);
    const base = bin.byteOffset + v.byteOffset + (a.byteOffset ?? 0);
    const dv = new DataView(bin.buffer, base, a.count * nc * cs);
    for (let i = 0; i < out.length; i++) {
      out[i] = a.componentType === 5126 ? dv.getFloat32(i * 4, true)
        : a.componentType === 5125 ? dv.getUint32(i * 4, true) : dv.getUint16(i * 2, true);
    }
    return { a, nc, out };
  };
  if (!gltf.scenes || gltf.scene === undefined || !gltf.scenes[gltf.scene]) bad('scene');
  for (const nd of gltf.nodes ?? []) if (nd.mesh !== undefined && !(gltf.meshes ?? [])[nd.mesh]) bad('node-mesh-ref');
  const prims = [];
  for (const m of gltf.meshes ?? []) {
    for (const pr of m.primitives) {
      if (pr.mode !== 4) bad('triangles-only');
      if (pr.material === undefined || !(gltf.materials ?? [])[pr.material]) bad('material-ref');
      const P = accRead(pr.attributes.POSITION), N = pr.attributes.NORMAL === undefined ? null : accRead(pr.attributes.NORMAL);
      const I = pr.indices === undefined ? null : accRead(pr.indices);
      if (!P || !I) { bad('primitive-complete'); continue; }
      if (P.a.type !== 'VEC3' || P.a.componentType !== 5126) bad('position-vec3-float');
      const nv = P.a.count;
      let min = [Infinity, Infinity, Infinity], max = [-Infinity, -Infinity, -Infinity];
      for (let i = 0; i < nv; i++) for (let k = 0; k < 3; k++) {
        const x = P.out[i * 3 + k];
        if (!Number.isFinite(x)) bad('finite');
        min[k] = Math.min(min[k], x); max[k] = Math.max(max[k], x);
      }
      const eq = (u, w) => Array.isArray(u) && u.length === 3 && u.every((q, k) => Math.abs(q - w[k]) <= 1e-4 * Math.max(1, Math.abs(w[k])));
      if (!eq(P.a.min, min) || !eq(P.a.max, max)) bad('position-min-max');
      if (I.nc !== 1 || ![5123, 5125].includes(I.a.componentType)) bad('index-type');
      if (I.out.length % 3 !== 0) bad('index-multiple-of-3');
      for (const ix of I.out) if (ix >= nv) { bad('index-range'); break; }
      if (N) {
        if (N.a.count !== nv) bad('normal-count');
        for (let i = 0; i < nv; i++) {
          const l = Math.hypot(N.out[i * 3], N.out[i * 3 + 1], N.out[i * 3 + 2]);
          if (!(Math.abs(l - 1) < 1e-3)) { bad('normal-unit'); break; }
        }
      }
      if (pr.attributes.COLOR_0 !== undefined) {
        const C = accRead(pr.attributes.COLOR_0);
        if (!C || C.a.count !== nv) bad('color-count');
      }
      prims.push({ pr, P, I, N, min, max });
    }
  }
  reads.prims = prims;
  return { fails, gltf, bin, reads };
}

/** Triangle normals' y component sign over a primitive: [up, down, flat] counts. */
function facing(prim) {
  const { P, I } = prim;
  let up = 0, down = 0, flat = 0;
  for (let t = 0; t < I.out.length; t += 3) {
    const a = I.out[t] * 3, b = I.out[t + 1] * 3, c = I.out[t + 2] * 3;
    const ux = P.out[b] - P.out[a], uz = P.out[b + 2] - P.out[a + 2];
    const vx = P.out[c] - P.out[a], vz = P.out[c + 2] - P.out[a + 2];
    const ny = uz * vx - ux * vz;
    if (Math.abs(ny) < 1e-9) flat++; else if (ny > 0) up++; else down++;
  }
  return { up, down, flat };
}

// ------------------------------------------------------------------ inputs ---
const reg = R('./registry/tiles.json');
const fab = R('./registry/fabric.json');
const gp = R('./registry/geopose.json');
const parishes = R('../parishes/registry/parishes.json');
const bay = R('../bayarea/registry/bayarea.json');
const wilds = R('../wilds/registry/wilds.json');
const geo3d = R('../geo3d/registry/geo3d.json');
const geoReg = R('../geo/registry/campuses_geo.json');
// The tiles are a build output (dist/sneeze/, gitignored): this suite builds them fresh into a temp dir
// with the same module spatial/build.py uses, and holds those bytes. Nothing is read from a committed .glb
// because nothing committed is one.
const BUILD_DIR = mkdtempSync(join(tmpdir(), 'tiles-'));
process.on('exit', () => { try { rmSync(BUILD_DIR, { recursive: true, force: true }); } catch { /* best effort */ } });
const SNEEZE = pathToFileURL(BUILD_DIR + '/');
const BUILT = (() => {
  const py = `import sys,json,pathlib\nsys.path.insert(0,${JSON.stringify(ROOTP + 'spatial')})\nimport tiles\nroot=pathlib.Path(${JSON.stringify(ROOTP)})\n`
    + `gp=json.load(open(root/'spatial/registry/geopose.json'))\nref={p['subject']['ref']:p for p in gp['poses']}\n`
    + `d=tiles.build(root,pathlib.Path(sys.argv[1]),ref,${JSON.stringify(UNKNOWN_H)})\nprint(json.dumps({t['id']:t['sha256'] for t in d['tiles']}))`;
  return JSON.parse(execFileSync('python3', ['-I', '-c', py, BUILD_DIR], { encoding: 'utf8' }));
})();
const tileFile = (t) => new URL(t.reference, SNEEZE);
const tiles = reg.tiles;
const byId = new Map(tiles.map((t) => [t.id, t]));
const tileBuf = new Map(tiles.map((t) => [t.id, existsSync(tileFile(t)) ? readFileSync(tileFile(t)) : Buffer.alloc(0)]));
const val = new Map(tiles.map((t) => [t.id, validateGlb(tileBuf.get(t.id))]));

/* ------------------------------------------------- the validator's own drills --- */
{
  const sample = tileBuf.get('campus-oakland') ?? Buffer.alloc(0);
  ok('the validator passes an untouched tile (the drill baseline)', sample.length > 0 && validateGlb(sample).fails.length === 0);
  const mut = (name, rule, f) => {
    const b = Buffer.from(sample); const r = f(b) ?? b;
    ok(`validator drill - ${name} fails rule "${rule}"`, validateGlb(r).fails.includes(rule));
  };
  mut('a wrong magic', 'magic', (b) => { b.write('glTX', 0, 'latin1'); });
  mut('version 1', 'version', (b) => { b.writeUInt32LE(1, 4); });
  mut('a declared length that is not the file length', 'declared-length', (b) => { b.writeUInt32LE(b.length + 4, 8); });
  mut('a truncated file', 'declared-length', (b) => b.subarray(0, b.length - 8));
  mut('a JSON chunk of the wrong type', 'json-chunk-first', (b) => { b.write('BIN\0', 16, 'latin1'); });
  mut('an asset version other than 2.0', 'asset-version', (b) => { b.write('"version":"1.0"', b.indexOf('"version":"2.0"'), 'latin1'); });
  mut('an extensionsUsed entry', 'no-extensions', (b) => rewrapJson(b, (t) => t.replace('"scene":0', '"extensionsUsed":["X_y"],"scene":0')));
  mut('an index past the last vertex', 'index-range', (b) => {
    const g = validateGlb(b); const pr = g.reads.prims[0]; const v = g.gltf.bufferViews[pr.I.a.bufferView];
    const at = g.bin.byteOffset + v.byteOffset; b.writeUInt16LE(60000, at); });
  mut('a NaN position', 'finite', (b) => {
    const g = validateGlb(b); const pr = g.reads.prims[0]; const v = g.gltf.bufferViews[pr.P.a.bufferView];
    b.writeFloatLE(NaN, g.bin.byteOffset + v.byteOffset); });
  mut('a position that leaves its declared min/max', 'position-min-max', (b) => {
    const g = validateGlb(b); const pr = g.reads.prims[0]; const v = g.gltf.bufferViews[pr.P.a.bufferView];
    b.writeFloatLE(1e6, g.bin.byteOffset + v.byteOffset); });
  mut('a normal that is not unit length', 'normal-unit', (b) => {
    const g = validateGlb(b); const pr = g.reads.prims[0]; const v = g.gltf.bufferViews[pr.N.a.bufferView];
    b.writeFloatLE(5, g.bin.byteOffset + v.byteOffset); });
}
function rewrapJson(buf, f) {
  // re-wrap a mutated JSON chunk into a well-formed .glb with the original BIN, so only the mutated rule fails
  const jl = buf.readUInt32LE(12); const bin = buf.subarray(20 + jl);
  let js = Buffer.from(f(buf.toString('utf8', 20, 20 + jl).trimEnd()), 'utf8');
  js = Buffer.concat([js, Buffer.alloc((4 - (js.length % 4)) % 4, 0x20)]);
  const head = Buffer.alloc(12); head.write('glTF', 0, 'latin1'); head.writeUInt32LE(2, 4);
  const jh = Buffer.alloc(8); jh.writeUInt32LE(js.length, 0); jh.write('JSON', 4, 'latin1');
  head.writeUInt32LE(12 + 8 + js.length + bin.length, 8);
  return Buffer.concat([head, jh, js, bin]);
}

/* ------------------------------------------------------- the registry itself --- */
ok('the registry names its tiles, manifests, budget, verified sources and field table',
  Array.isArray(reg.tiles) && Array.isArray(reg.manifests) && reg.budget && Array.isArray(reg.verified)
  && Array.isArray(reg.field_status) && reg.honesty && typeof reg.map_module_url === 'string');

{
  const code = ['spatial/build.py', 'spatial/tiles.py', 'spatial/wilds_heights.mjs'];
  const covers = reg.source_stamp_covers;
  ok('the registry source_stamp is the sha256 of every file in source_stamp_covers, in order (code first, then every input)',
    JSON.stringify(covers.slice(0, 3)) === JSON.stringify(code) && new Set(covers).size === covers.length
    && covers.every((f) => existsSync(ROOTP + f))
    && reg.source_stamp === createHash('sha256').update(Buffer.concat(covers.map((f) => readFileSync(ROOTP + f)))).digest('hex').slice(0, 16));
  // What the tile build really opens, observed: run it under a Python audit hook that records every file
  // opened for reading inside the repository while tiles.build runs (the pose input is read first, outside it).
  const opened = (() => {
    const dir = mkdtempSync(join(tmpdir(), 'tiles-audit-'));
    try {
      const py = `import sys,json,pathlib\nsys.path.insert(0,${JSON.stringify(ROOTP + 'spatial')})\nimport tiles\nroot=pathlib.Path(${JSON.stringify(ROOTP)})\n`
        + `gp=json.load(open(root/'spatial/registry/geopose.json'))\nref={p['subject']['ref']:p for p in gp['poses']}\nseen=set()\n`
        + `def hook(ev,args):\n  if ev=='open' and isinstance(args[0],str) and (len(args)<2 or args[1] is None or 'r' in str(args[1]) and not any(c in str(args[1]) for c in 'wax+')):\n    seen.add(args[0])\n`
        + `sys.addaudithook(hook)\ntiles.build(root,pathlib.Path(sys.argv[1]),ref,'x')\n`
        + `R=str(root)+'/'\nprint(json.dumps(sorted(p[len(R):] for p in seen if p.startswith(R) and '__pycache__' not in p and not p.startswith(R+'dist/'))))`;
      return JSON.parse(execFileSync('python3', ['-I', '-c', py, dir], { encoding: 'utf8' }));
    } finally { rmSync(dir, { recursive: true, force: true }); }
  })();
  ok(`the covers list includes every file the Python tile build opens for reading (observed: ${opened.length} files, from the parish and county map files to the four registries)`,
    opened.length > 40 && opened.every((f) => covers.includes(f) || f.endsWith('.py') && covers.includes('spatial/tiles.py')));
  const wh = readFileSync(ROOTP + 'spatial/wilds_heights.mjs', 'utf8');
  const nodeReads = [...wh.matchAll(/(?:from\s+|new URL\()'(\.\.\/[^']+)'/g)].map((m) => m[1].replace(/^\.\.\//, ''));
  ok('the covers list includes every file the node height script names (its registry and its import wilds/core.mjs), read from the script itself',
    nodeReads.length >= 2 && nodeReads.every((f) => covers.includes(f)) && covers.includes('wilds/core.mjs'));
  ok('the covers list includes the geo registry the campus anchors are computed from, and each campus anchor equals it',
    covers.includes('geo/registry/campuses_geo.json')
    && tiles.filter((t) => t.kind === 'campus').every((t) => { const c = geoReg.campuses[t.id.slice(7)]; const p = t.anchor.geopose.position; return p.lat === c.lat && p.lon === c.lng && t.anchor.provenance.position_horizontal === c.provenance; }));
}

{
  const campusesWithHalls = Object.entries(geo3d.campuses).filter(([, c]) => c.halls_count > 0).map(([k]) => k);
  const want = {
    parish: Object.keys(parishes.parishes).length,
    county: Object.keys(bay.counties).length,
    wild: wilds.worlds.length,
    campus: campusesWithHalls.length,
  };
  const got = { parish: 0, county: 0, wild: 0, campus: 0 };
  for (const t of tiles) got[t.kind]++;
  ok(`one tile per region the source registries hold: ${want.parish} parishes, ${want.county} counties, ${want.wild} wilds, ${want.campus} campuses with halls`,
    JSON.stringify(got) === JSON.stringify(want));
  ok('tile ids are unique and each is {kind}-{key} of its source record',
    new Set(tiles.map((t) => t.id)).size === tiles.length
    && Object.keys(parishes.parishes).every((f) => byId.has(`parish-${f}`))
    && Object.keys(bay.counties).every((f) => byId.has(`county-${f}`))
    && wilds.worlds.every((w) => byId.has(`wild-${w.id}`))
    && campusesWithHalls.every((c) => byId.has(`campus-${c}`)));
  ok('every campus without halls is listed as not exported with its registry reason, never given an invented tile',
    reg.campuses_without_tile.length === Object.keys(geo3d.campuses).length - campusesWithHalls.length
    && reg.campuses_without_tile.every((c) => geo3d.campuses[c.campus].halls_count === 0 && c.why === geo3d.campuses[c.campus].note && !byId.has(`campus-${c.campus}`)));
}

/* ------------------------------------------------ every tile is a valid glTF 2.0 --- */
ok('every tile file exists and is on disk where the registry says', tiles.every((t) => existsSync(tileFile(t)) && t.file === `dist/sneeze/${t.reference}`));
ok('every tile begins with the ASCII magic "glTF" and is glTF version 2',
  tiles.every((t) => { const b = tileBuf.get(t.id); return b.toString('latin1', 0, 4) === 'glTF' && b.readUInt32LE(4) === 2; }));
ok('every tile declares its own byte length exactly, in four-byte chunks',
  tiles.every((t) => { const b = tileBuf.get(t.id); return b.readUInt32LE(8) === b.length && b.length % 4 === 0 && !val.get(t.id).fails.includes('chunk-aligned'); }));
ok('every tile has a JSON chunk first (parses as JSON) and a BIN chunk after it',
  tiles.every((t) => { const f = val.get(t.id).fails; return !f.includes('json-chunk-first') && !f.includes('json-parse') && !f.includes('bin-chunk') && !f.includes('chunk-overrun'); }));
ok('every tile passes every container rule of the validator (accessors in bounds, min/max true, indices in range, floats finite, normals unit)',
  tiles.every((t) => val.get(t.id).fails.length === 0));
ok('no tile uses an extension, a texture, an animation or a skin: nothing a loader must guess at',
  tiles.every((t) => { const g = val.get(t.id).gltf; return g && !g.extensionsUsed && !g.extensionsRequired && !g.images && !g.textures && !g.animations && !g.skins; }));
ok('every tile has one scene, one node, one mesh whose primitives are triangles with a material each',
  tiles.every((t) => { const g = val.get(t.id).gltf; return g.scenes.length === 1 && g.nodes.length === 1 && g.meshes.length === 1
    && g.meshes[0].primitives.length === t.layers.length && g.meshes[0].primitives.every((p) => p.mode === 4 && g.materials[p.material]); }));
ok('the layers in the registry are the primitives in the file, in order, with the same vertex and triangle counts',
  tiles.every((t) => { const g = val.get(t.id).gltf; const pr = val.get(t.id).reads.prims;
    return t.layers.every((ly, i) => g.meshes[0].primitives[i].extras.layer === ly.name
      && pr[i].P.a.count === ly.vertices && pr[i].I.out.length / 3 === ly.triangles); }));
ok('the flat layers (ground, water, streets, terrain) face up on every triangle: a tile seen from above is not inside out',
  tiles.every((t) => val.get(t.id).reads.prims.every((p, i) => { if (!FLAT_LAYERS.test(t.layers[i].name)) return true; const f = facing(p); return f.down === 0 && f.up > 0; })));
ok('the registry bytes and sha256 are the file\'s own',
  tiles.every((t) => t.bytes === tileBuf.get(t.id).length && t.sha256 === sha(tileBuf.get(t.id))));
ok('the registry bounding box is the accessors\' own min/max (to 0.01 m)',
  tiles.every((t) => { const pr = val.get(t.id).reads.prims;
    for (let k = 0; k < 3; k++) {
      const mn = Math.min(...pr.map((p) => p.min[k])), mx = Math.max(...pr.map((p) => p.max[k]));
      if (Math.abs(mn - t.bbox_gltf_m.min[k]) > 0.011 || Math.abs(mx - t.bbox_gltf_m.max[k]) > 0.011) return false;
    } return true; }));

/* --------------------------------------------------------------- the budget --- */
{
  const sizes = tiles.map((t) => tileBuf.get(t.id).length);
  const total = sizes.reduce((a, b) => a + b, 0);
  ok(`every tile is within ${CEIL_TILE_BYTES} bytes (largest ${Math.max(...sizes)})`, sizes.every((s) => s <= CEIL_TILE_BYTES));
  ok(`the tiles total at most ${CEIL_TOTAL_BYTES} bytes (${total})`, total <= CEIL_TOTAL_BYTES);
  ok('the registry budget is no looser than this suite\'s ceilings and its totals are the disk\'s',
    reg.budget.tile_max_bytes <= CEIL_TILE_BYTES && reg.budget.total_max_bytes <= CEIL_TOTAL_BYTES
    && reg.budget.total_bytes === total && reg.budget.largest_tile_bytes === Math.max(...sizes)
    && reg.budget.sreference_max_bytes === SREF_MAX);
  const dirFiles = readdirSync(new URL('tiles/', SNEEZE)).filter((f) => f.endsWith('.glb')).sort();
  ok('the tiles directory holds exactly the registry\'s files: nothing stale left behind, nothing unlisted',
    JSON.stringify(dirFiles) === JSON.stringify(tiles.map((t) => t.reference.slice(6)).sort()));
}

/* ----------------------------------------------------------------- provenance --- */
ok('every tile and every layer carries a provenance word from the vocabulary, a source string and a note',
  tiles.every((t) => TIERS.includes(t.provenance) && t.layers.length > 0
    && t.layers.every((ly) => TIERS.includes(ly.provenance) && ly.source.length > 20 && ly.note.length > 20)));
ok('a tile\'s provenance is the WEAKEST word among its layers: never more recorded than its least-recorded layer',
  tiles.every((t) => t.provenance === t.layers.map((l) => l.provenance).sort((a, b) => TIERS.indexOf(b) - TIERS.indexOf(a))[0]));
ok('the provenance is inside the file too: asset extras, every material and every primitive agree with the registry',
  tiles.every((t) => { const g = val.get(t.id).gltf; const ex = g.asset.extras;
    return ex.provenance === t.provenance && ex.tile === t.id
      && t.layers.every((ly, i) => ex.provenance_layers[ly.name] === ly.provenance
        && g.materials[g.meshes[0].primitives[i].material].extras.provenance === ly.provenance
        && g.meshes[0].primitives[i].extras.provenance === ly.provenance); }));
ok('georeferenced region tiles carry the DERIVED ground (outline converted from RECORDED Census data) and AUTHORED streets and water, said in their sources',
  tiles.filter((t) => ['parish', 'county'].includes(t.kind)).every((t) => {
    const g = t.layers.find((l) => l.name === 'ground');
    return g.provenance === 'DERIVED' && /RECORDED/.test(g.source) && /Census/.test(g.source)
      && t.layers.filter((l) => l.name !== 'ground').every((l) => l.provenance === 'AUTHORED' && /AUTHORED/.test(l.source));
  }));
ok('wilds terrain is AUTHORED and says it is not real elevation; campus halls are SCHEMATIC and say they are not a building anyone built',
  tiles.filter((t) => t.kind === 'wild').every((t) => t.provenance === 'AUTHORED' && /NOT real elevation/.test(t.layers[0].note))
  && tiles.filter((t) => t.kind === 'campus').every((t) => t.provenance === 'SCHEMATIC' && /not a building/.test(t.layers[0].note)));
ok('the layers the builder could not export are named, not hidden: local street counts, hidden wilds caches',
  tiles.filter((t) => ['parish', 'county'].includes(t.kind)).every((t) => Number.isInteger(t.counts.streets_local_not_exported))
  && tiles.filter((t) => t.kind === 'wild').every((t) => Number.isInteger(t.counts.caches_not_exported)));

/* --------------------------------------------- geometry held against the registries --- */
{
  const lookup = (t) => (t.kind === 'parish' ? parishes.parishes[t.id.slice(7)] : bay.counties[t.id.slice(7)]);
  const region = tiles.filter((t) => ['parish', 'county'].includes(t.kind));
  ok('every region tile\'s ground vertices are the registry outline\'s vertices (east, 0, -north) to 0.05 m, and any extra vertex is a self-crossing the builder counted',
    region.every((t) => {
      const rec = lookup(t); const g = val.get(t.id).reads.prims[0];
      const cell = new Map();
      for (const [e, nn] of rec.outline_local_m.flatMap((poly) => poly[0])) {
        const k = `${Math.round(e)},${Math.round(-nn)}`; (cell.get(k) ?? cell.set(k, []).get(k)).push([e, -nn]);
      }
      const near = (x, z) => {
        for (let dx = -1; dx <= 1; dx++) for (let dz = -1; dz <= 1; dz++) {
          for (const [e, zz] of cell.get(`${Math.round(x) + dx},${Math.round(z) + dz}`) ?? []) if (Math.hypot(e - x, zz - z) < 0.05) return true;
        }
        return false;
      };
      const extra = new Set();
      for (let i = 0; i < g.P.a.count; i++) {
        if (!near(g.P.out[i * 3], g.P.out[i * 3 + 2])) extra.add(`${g.P.out[i * 3].toFixed(2)},${g.P.out[i * 3 + 2].toFixed(2)}`);
      }
      return extra.size <= t.counts.outline_self_crossings_split;
    }));
  ok('every region tile\'s ground area is the registry\'s own area_km2 for that region to within 1% (the coarse outline, filled)',
    region.every((t) => { const a = lookup(t).area_km2; return Math.abs(t.counts.ground_area_km2_triangulated - a) / a < 0.01; }));
  ok('every region tile exports exactly the arterial and collector streets and the channels and ponds its map file holds',
    region.every((t) => {
      const maps = t.kind === 'parish' ? 'parishes' : 'bayarea'; const key = t.id.slice(7);
      const sf = R(`../${maps}/maps/streets/${key}.json`), wf = R(`../${maps}/maps/world/${key}.json`);
      return t.counts.streets_arterial === sf.classes.arterial.length && t.counts.streets_collector === sf.classes.collector.length
        && t.counts.streets_local_not_exported === sf.classes.local.length
        && t.counts.channels === wf.water.channels.length && t.counts.ponds === wf.water.ponds.length;
    }));
  ok('the streets are drawn at the registry\'s class widths: an arterial ribbon is as wide as the streets file says (to 1 m)',
    region.every((t) => {
      const maps = t.kind === 'parish' ? 'parishes' : 'bayarea';
      const sf = R(`../${maps}/maps/streets/${t.id.slice(7)}.json`);
      const li = t.layers.findIndex((l) => l.name === 'streets-arterial'); if (li < 0) return true;
      const p = val.get(t.id).reads.prims[li]; const nVert = p.P.a.count / 2;
      // first polyline's first left/right pair is vertex 0 and vertex nVertOfThatLine; measure the first pair's separation
      const first = sf.classes.arterial[0].filter((q, i, arr) => i === 0 || q.join() !== arr[i - 1].join()); const m = first.length;
      const a = [p.P.out[0], p.P.out[2]], b = [p.P.out[m * 3], p.P.out[m * 3 + 2]];
      return Math.abs(Math.hypot(a[0] - b[0], a[1] - b[1]) - sf.widths_m.arterial) < 1 && nVert > 0;
    }));
  ok('the campus tiles extrude exactly the halls the geo3d registry lists (111 hall footprints across the campuses with halls), each at its registry height',
    tiles.filter((t) => t.kind === 'campus').every((t) => {
      const halls = geo3d.campuses[t.id.slice(7)].halls; const p = val.get(t.id).reads.prims[0];
      const hmax = Math.max(...halls.map((h) => h.h));
      return t.counts.halls === halls.length && p.P.a.count === halls.length * 20 && Math.abs(p.max[1] - hmax) < 1e-3;
    }));
  const wildGrid = tiles.filter((t) => t.kind === 'wild');
  ok('the wilds terrain is a grid of the registry\'s size over the registry\'s extent, and its heights are the page\'s own terrain function (re-run here)',
    wildGrid.every((t) => {
      const w = wilds.worlds.find((x) => `wild-${x.id}` === t.id); const ex = w.extent_m; const nn = reg.budget.wilds_grid_n;
      const out = JSON.parse(execFileSync('node', [ROOTP + 'spatial/wilds_heights.mjs', String(nn)], { encoding: 'utf8', maxBuffer: 1 << 26 }));
      const grid = out[w.id].grid; const p = val.get(t.id).reads.prims[0];
      if (p.P.a.count !== nn * nn || Math.abs(p.max[0] - ex / 2) > 1e-3 || Math.abs(p.min[2] + ex / 2) > 1e-3) return false;
      for (let i = 0; i < nn * nn; i += 97) if (Math.abs(p.P.out[i * 3 + 1] - grid[i]) > 0.01) return false;
      return true;
    }));
  ok('every tile built fresh from the registries has the sha256 tiles.json records: the build is deterministic and the committed record is current',
    tiles.every((t) => BUILT[t.id] === t.sha256) && Object.keys(BUILT).length === tiles.length);
  ok('a dist/sneeze left on disk (a gitignored build output), if present, holds exactly the recorded bytes: no stale build is mistaken for current',
    !existsSync(ROOTP + 'dist/sneeze/tiles') || tiles.every((t) => { const p = ROOTP + 'dist/sneeze/' + t.reference; return existsSync(p) && sha(readFileSync(p)) === t.sha256; })
      && readdirSync(ROOTP + 'dist/sneeze/tiles').filter((f) => f.endsWith('.glb')).length === tiles.length);
}

/* ------------------------------------------------------------------- anchors --- */
const geo = tiles.filter((t) => t.anchor);
ok('exactly the georeferenced tiles (parishes, counties, campuses) have an anchor; the wilds have none and say why',
  geo.length === tiles.filter((t) => t.kind !== 'wild').length
  && tiles.filter((t) => t.kind === 'wild').every((t) => t.anchor === null && /not on the globe/.test(t.no_anchor_because) && /No latitude or longitude is invented/.test(t.no_anchor_because)));
ok('the wilds worlds really are off the globe in their own registry (on_globe false, coordinates "none")',
  wilds.worlds.every((w) => w.geolocation.on_globe === false && /^none/.test(w.geolocation.coordinates)));
ok('every anchor is a GeoPose 1.0 Basic-YPR exactly: position{lat,lon,h}, orientation{yaw,pitch,roll}, nothing else, all finite',
  geo.every((t) => { const g = t.anchor.geopose;
    return JSON.stringify(Object.keys(g)) === '["position","orientation"]'
      && JSON.stringify(Object.keys(g.position)) === '["lat","lon","h"]'
      && JSON.stringify(Object.keys(g.orientation)) === '["yaw","pitch","roll"]'
      && [...Object.values(g.position), ...Object.values(g.orientation)].every((v) => typeof v === 'number' && Number.isFinite(v)); }));
ok('every anchor latitude is within ±90 and longitude within ±180',
  geo.every((t) => Math.abs(t.anchor.geopose.position.lat) <= 90 && Math.abs(t.anchor.geopose.position.lon) <= 180));
ok('every anchor has height 0.0 with the UNKNOWN sidecar: this bundle holds no height, and a zero is a placeholder, never a measurement',
  geo.every((t) => t.anchor.geopose.position.h === 0 && t.anchor.provenance.h_provenance === UNKNOWN_H
    && t.anchor.provenance.h_provenance === gp.poses[0].provenance.h_provenance));
ok('every anchor orientation is the identity and its sidecar says why (east/north/up by construction, or SCHEMATIC north-up) - no heading is invented',
  geo.every((t) => { const o = t.anchor.geopose.orientation; const s = t.anchor.provenance.orientation_provenance;
    return o.yaw === 0 && o.pitch === 0 && o.roll === 0
      && (t.kind === 'campus' ? /^SCHEMATIC/.test(s) && /no heading/.test(s) : /^DERIVED/.test(s) && /east\/north\/up by construction/.test(s) && /not checked/.test(s)); }));
ok('every anchor carries a horizontal-position provenance word from the vocabulary and a source string',
  geo.every((t) => TIERS.includes(t.anchor.provenance.position_horizontal) && t.anchor.provenance.source.length > 20));
ok('a parish or county anchor is its registry frame origin to the digit (DERIVED: the area-weighted centroid of the coarse outline)',
  geo.filter((t) => t.kind !== 'campus').every((t) => {
    const rec = (t.kind === 'parish' ? parishes.parishes : bay.counties)[t.id.slice(t.kind === 'parish' ? 7 : 7)];
    const o = rec.frame.origin; const p = t.anchor.geopose.position;
    return p.lat === o.lat && p.lon === o.lng && t.anchor.provenance.position_horizontal === 'DERIVED'; }));
ok('a parish or county anchor lies inside the longitude and latitude range of its own recorded outline',
  geo.filter((t) => t.kind !== 'campus').every((t) => {
    const rec = (t.kind === 'parish' ? parishes.parishes : bay.counties)[t.id.slice(7)];
    const pts = rec.outline.polygons.flatMap((poly) => poly.flat());
    const lo = Math.min(...pts.map((q) => q[0])), hi = Math.max(...pts.map((q) => q[0]));
    const la = Math.min(...pts.map((q) => q[1])), lb = Math.max(...pts.map((q) => q[1]));
    const p = t.anchor.geopose.position; return p.lon >= lo && p.lon <= hi && p.lat >= la && p.lat <= lb; }));
ok('a campus tile\'s anchor is the campus pose geopose.json already holds, byte for byte, with its own provenance word',
  geo.filter((t) => t.kind === 'campus').every((t) => {
    const ref = gp.poses.find((p) => p.subject.ref === `campus:${t.id.slice(7)}`);
    return t.anchor.pose_ref === ref.subject.ref && JSON.stringify(t.anchor.geopose) === JSON.stringify(ref.geopose)
      && t.anchor.provenance.position_horizontal === ref.provenance.position_horizontal; }));
ok('a region tile\'s world_m placement is its anchor converted through the registry\'s shared metre frame (within 1 m): anchors and manifests agree',
  geo.filter((t) => t.kind !== 'campus').every((t) => {
    const w = (t.kind === 'parish' ? parishes : bay).frames.world.origin; const R_E = 6371008.8; const rad = Math.PI / 180;
    const p = t.anchor.geopose.position;
    const e = R_E * Math.cos(w.lat * rad) * (p.lon - w.lng) * rad, nn = R_E * (p.lat - w.lat) * rad;
    return Math.hypot(e - t.world_m[0], nn - t.world_m[1]) < 1.0; }));

/* ------------------------------------------------------------------ manifests --- */
const OK_TOP = ['Container', 'Services', 'Modules', 'Data'];
const OK_DATA = ['Scene', 'Anchors', 'Provenance'];
const OK_NODE = ['Head', 'Name', 'Resource', 'Transform', 'aChildren'];
const mf = new Map(reg.manifests.map((m) => [m.id, { m, doc: existsSync(new URL(m.id + '.json', SNEEZE)) ? JSON.parse(readFileSync(new URL(m.id + '.json', SNEEZE))) : null }]));
const walk = (node, fn, parent = null) => { fn(node, parent); (node.aChildren ?? []).forEach((c) => walk(c, fn, node)); };
const sceneRefs = (doc) => { const out = []; walk(doc.Data.Scene, (nd) => out.push(nd.Resource.sReference)); return out; };

ok('every manifest file exists, parses as JSON, and its bytes and sha256 are the registry\'s own',
  [...mf.values()].every(({ m, doc }) => { const f = new URL(m.id + '.json', SNEEZE); return doc && statSync(f).size === m.bytes && sha(readFileSync(f)) === m.sha256 && m.file === `dist/sneeze/${m.id}.json`; }));
ok('the manifests directory holds exactly the registry\'s manifests',
  JSON.stringify(readdirSync(SNEEZE).filter((f) => f.endsWith('.json')).sort()) === JSON.stringify(reg.manifests.map((m) => m.id + '.json').sort()));
ok('every manifest has exactly Container, Services, Modules and Data at the top (the shape of the Sneeze example docs) and nothing else',
  [...mf.values()].every(({ doc }) => JSON.stringify(Object.keys(doc)) === JSON.stringify(OK_TOP)));
ok('Services is the empty list in every manifest: no service is invented, and the docs disagree on the service shape',
  [...mf.values()].every(({ doc }) => Array.isArray(doc.Services) && doc.Services.length === 0));
ok('there is no Primary or primary block in any manifest (the docs spell it both ways)',
  [...mf.values()].every(({ doc }) => !('Primary' in doc) && !('primary' in doc)));
ok('every manifest\'s one module is the stock map module URL (https, ends in map.wasm), with no hash pinned because the file was not reachable',
  [...mf.values()].every(({ doc }) => doc.Modules.length === 1 && JSON.stringify(Object.keys(doc.Modules[0])) === '["sUrl"]'
    && doc.Modules[0].sUrl === reg.map_module_url && /^https:\/\/.+\/map\.wasm$/.test(doc.Modules[0].sUrl)));
ok('Data holds only Scene, Anchors and Provenance; every node holds only Head, Name, Resource, Transform and aChildren; every Transform only Position',
  [...mf.values()].every(({ doc }) => Object.keys(doc.Data).every((k) => OK_DATA.includes(k)) && (() => {
    let good = true;
    walk(doc.Data.Scene, (nd) => {
      if (!Object.keys(nd).every((k) => OK_NODE.includes(k))) good = false;
      if (nd.Transform && !(JSON.stringify(Object.keys(nd.Transform)) === '["Position"]')) good = false;
      if (JSON.stringify(Object.keys(nd.Resource)) !== '["sReference"]') good = false;
      if (nd.Head.Self !== 'P-?' || JSON.stringify(Object.keys(nd.Head)) !== '["Self"]') good = false;
      if (typeof nd.Name !== 'string' || !nd.Name.length) good = false;
    });
    return good; })()));
ok(`every sReference is relative (no scheme, no leading slash), at most ${SREF_MAX} bytes, and resolves to a tile file that exists`,
  [...mf.values()].every(({ doc }) => sceneRefs(doc).every((r) => !/^[a-z]+:\/\//i.test(r) && !r.startsWith('/') && !r.includes('..')
    && Buffer.byteLength(r) <= SREF_MAX && existsSync(new URL(r, SNEEZE)) && tiles.some((t) => t.reference === r))));
ok('each manifest places exactly the tiles it lists, each once, and every tile is in exactly one manifest',
  [...mf.values()].every(({ m, doc }) => JSON.stringify(sceneRefs(doc).sort()) === JSON.stringify(m.tiles.map((id) => byId.get(id).reference).sort()))
  && tiles.every((t) => reg.manifests.filter((m) => m.tiles.includes(t.id)).length === 1));
ok('a world with several tiles roots its tree at the first tile (Position = its world_m) and offsets each child from it (child Position = child world_m - root world_m, Z 0)',
  [...mf.values()].filter(({ m }) => m.tiles.length > 1).every(({ m, doc }) => {
    const root = byId.get(m.tiles[0]); const sc = doc.Data.Scene;
    if (sc.Resource.sReference !== root.reference) return false;
    if (Math.abs(sc.Transform.Position[0] - root.world_m[0]) > 0.011 || Math.abs(sc.Transform.Position[1] - root.world_m[1]) > 0.011 || sc.Transform.Position[2] !== 0) return false;
    return (sc.aChildren ?? []).length === m.tiles.length - 1 && sc.aChildren.every((c) => {
      const t = tiles.find((x) => x.reference === c.Resource.sReference);
      return Math.abs(c.Transform.Position[0] - (t.world_m[0] - root.world_m[0])) < 0.02 && Math.abs(c.Transform.Position[1] - (t.world_m[1] - root.world_m[1])) < 0.02 && c.Transform.Position[2] === 0;
    }); }));
ok('a tile\'s world_m is its registry frame origin in the shared metre frame (parishes, counties)',
  tiles.filter((t) => t.kind === 'parish' || t.kind === 'county').every((t) => {
    const rec = (t.kind === 'parish' ? parishes.parishes : bay.counties)[t.id.slice(7)]; return JSON.stringify(rec.frame.origin_in_world_m) === JSON.stringify(t.world_m); }));
ok('single-tile worlds (wilds, campuses) have no Transform on the root: the tile origin is the scene origin',
  [...mf.values()].filter(({ m }) => m.tiles.length === 1).every(({ doc }) => !('Transform' in doc.Data.Scene) && !doc.Data.Scene.aChildren));
ok('Data.Anchors in each manifest is exactly the GeoPose of each georeferenced tile in it, and Data.Provenance is the tile provenance word',
  [...mf.values()].every(({ m, doc }) => {
    const want = m.tiles.map((id) => byId.get(id)).filter((t) => t.anchor);
    return doc.Data.Anchors.length === want.length && want.every((t, i) => doc.Data.Anchors[i].Tile === t.id
      && JSON.stringify(doc.Data.Anchors[i].GeoPose) === JSON.stringify(t.anchor.geopose))
      && m.tiles.every((id) => doc.Data.Provenance[id] === byId.get(id).provenance); }));
ok('each manifest says it is unsigned plain JSON and proposed, not loaded in any metaverse browser',
  reg.manifests.every((m) => /unsigned plain JSON/.test(m.envelope) && /not signed/.test(m.envelope) && /^proposed/.test(m.status) && /not loaded in Sneeze, Artemis/.test(m.status)));

/* ------------------------------------------- documented versus proposed fields --- */
const FS = reg.field_status;
ok('every field row is either documented (citing at least one verified fact) or proposed (citing none): nothing unverified passes as documented',
  FS.every((f) => (f.status === 'documented' && f.verified_ids.length > 0) || (f.status === 'proposed' && f.verified_ids.length === 0)));
ok('every verified id a field cites exists in the verified list, and every verified fact has an id, a fact and a MetaversalCorp primary URL',
  FS.every((f) => f.verified_ids.every((id) => reg.verified.some((v) => v.id === id)))
  && reg.verified.every((v) => v.id && v.fact.length > 30 && /^https:\/\/(github\.com|raw\.githubusercontent\.com)\/MetaversalCorp\//.test(v.url))
  && new Set(reg.verified.map((v) => v.id)).size === reg.verified.length);
ok('every manifest field this suite lets through (Container, Services, Modules[].sUrl, Data.Scene, Head.Self, Name, Resource.sReference, Transform.Position, aChildren) has a documented row',
  ['manifest.Container', 'manifest.Services', 'manifest.Modules[].sUrl', 'manifest.Data.Scene', 'node.Head.Self', 'node.Name', 'node.Resource.sReference', 'node.Transform.Position', 'node.aChildren']
    .every((k) => FS.some((f) => f.field === k && f.status === 'documented')));
ok('the fields the docs do not say are marked proposed: the GeoPose sidecar, the provenance sidecar, east/north world axes, any component reading GeoPose, child-fabric attachment, camera scale, frame budget and signing',
  [/Data\.Anchors/, /Data\.Provenance/, /east\/north/, /GeoPose anchor consumed/, /attaching one manifest/, /camera/, /frame budget/, /signing/]
    .every((re) => FS.some((f) => re.test(f.field) && f.status === 'proposed')));
ok('the primary-source facts include: GLB sniffed by magic, Y-up to Z-up conversion, plain JSON allowed but discouraged, relative URLs, own hosting, and that no doc read mentions GeoPose',
  ['glb-loaded', 'glb-axes', 'unsigned-caveat', 'relative-urls', 'own-hosting', 'no-geopose-doc'].every((id) => reg.verified.some((v) => v.id === id)));

/* ------------------------------------------------------------------ honesty --- */
const H = reg.honesty;
ok('the honesty block says: nothing was opened in Sneeze or Artemis and nothing was run',
  /no tile and no manifest/.test(H.not_loaded) && /Sneeze,\s+Artemis/.test(H.not_loaded) && /nothing was\s+run/.test(H.not_loaded));
ok('the honesty block says the stock map module was unreachable, is not vendored or hashed, and that the deployer must host their own copy',
  /could not reach/.test(H.map_module) && /not vendored/.test(H.map_module) && /no hash is pinned/.test(H.map_module) && /host\s+their own copy/.test(H.map_module));
ok('the honesty block says the manifests are unsigned and that no key or certificate is held or invented',
  /plain unsigned JSON/.test(H.unsigned) && /none is held and none is invented/.test(H.unsigned));
ok('the honesty block says the Sneeze docs are the implementer\'s own, partly unfinished, internally inconsistent, and not a standard',
  /implementer/.test(H.documentation_status) && /partially\s+implemented/.test(H.documentation_status) && /disagree/.test(H.documentation_status) && /not an OMBI or MSF\s+standard/.test(H.documentation_status));
ok('the honesty block says GeoPose is a sidecar no Sneeze component is known to read, and the axes are proposed',
  /no Sneeze\s+component is known to read it/.test(H.geopose_is_a_sidecar) && /no document read says, so it is proposed/.test(H.axes));
ok('the honesty block says the geometry is not a survey, the outlines are coarse, streets and water are AUTHORED, the ground is flat, and what is not exported',
  /not a survey/.test(H.geometry) && /coarse/.test(H.geometry) && /AUTHORED procedural/.test(H.geometry) && /flat at 0 m/.test(H.geometry) && /local streets/.test(H.geometry));
ok('the honesty block says the wilds are off the globe and carry no anchor',
  /no latitude or longitude/.test(H.wilds_not_on_globe) && /no anchor and none is invented/.test(H.wilds_not_on_globe));
ok('the honesty block says there is no map service, RMAP or SMAP endpoint and the scale behaviour is proposed',
  /no RMAP or SMAP endpoint exists here/.test(H.scale) && /proposed/.test(H.scale));
ok('fabric.json carries a world_tiles block that points at tiles.json, lists the same manifests and the same byte total, and says proposed / not loaded',
  fab.world_tiles && fab.world_tiles.registry === 'spatial/registry/tiles.json' && fab.world_tiles.tiles === tiles.length
  && JSON.stringify(fab.world_tiles.manifests) === JSON.stringify(reg.manifests.map((m) => m.file))
  && fab.world_tiles.total_bytes === reg.budget.total_bytes && /^proposed/.test(fab.world_tiles.status) && fab.world_tiles.directory === 'dist/sneeze/' && /built on demand/.test(fab.world_tiles.build_output) && /not loaded in Sneeze/.test(fab.world_tiles.status));
ok('fabric.json\'s static-files honesty line names the tiles as the exception to "no file on disk" instead of contradicting them',
  /world tiles/.test(fab.honesty.static_files_only_no_rmap) && /dist\/sneeze\//.test(fab.honesty.static_files_only_no_rmap) && /built on\s+demand/.test(fab.honesty.static_files_only_no_rmap) && /not served by the\s+Pages site/.test(fab.honesty.static_files_only_no_rmap));
ok('fabric.json\'s sources list the Sneeze repository as read from the project itself, with the docs-only and unreachable-site caveat',
  fab.sources.some((s) => /Sneeze engine source and docs/.test(s.what) && /MetaversalCorp/.test(s.url) && /nothing was run/.test(s.provenance) && /omb\.wiki/.test(s.provenance)));
ok('the registry source_stamp differs from the fabric stamp (tiles are stamped on their own inputs) and the three older registries still carry the builder-only stamp',
  reg.source_stamp !== fab.source_stamp
  && [gp, fab, R('./registry/som.json')].every((d) => d.source_stamp === createHash('sha256').update(readFileSync(new URL('./build.py', import.meta.url))).digest('hex').slice(0, 16)));

/* ---------------------------------------------------------------- the wiki page --- */
{
  const wiki = readFileSync(new URL('../wiki/Spatial-Fabric.md', import.meta.url), 'utf8');
  const sec = wiki.includes('## World tiles for Sneeze') ? wiki.slice(wiki.indexOf('## World tiles for Sneeze')) : '';
  ok('the wiki page has the world-tiles section, labelled proposed and not loaded anywhere',
    /## World tiles for Sneeze \(proposed, not loaded anywhere\)/.test(sec));
  ok('the wiki page lists every tile id, every manifest file and every verified source URL the registry holds',
    tiles.every((t) => sec.includes('`' + t.id + '`')) && reg.manifests.every((m) => sec.includes('`' + m.file + '`'))
    && reg.verified.every((v) => sec.includes(v.url)));
  ok('the wiki page marks every field row documented or proposed exactly as the registry does, and carries the not-claimed lines',
    FS.every((f) => sec.includes('| `' + f.field + '` | **' + f.status + '** |'))
    && sec.includes(H.not_loaded.charAt(0).toUpperCase() + H.not_loaded.slice(1)) && sec.includes('### What is not claimed'));
}

/* ---------------------------------------------------- hygiene of public files --- */
{
  // venue/test.mjs proves no third-party model is redistributed by walking the tree for .glb/.gltf/.fbx;
  // the world tiles must therefore never be committed. Same walk, same skips.
  const heavy = [];
  const walk = (dir) => {
    for (const e of readdirSync(dir, { withFileTypes: true })) {
      if (['node_modules', '.git', '__pycache__', 'dist'].includes(e.name)) continue;
      const p = join(dir, e.name);
      if (e.isDirectory()) walk(p); else if (['.glb', '.gltf', '.fbx'].includes(extname(e.name).toLowerCase())) heavy.push(p);
    }
  };
  walk(ROOTP);
  ok('no .glb, .gltf or .fbx exists anywhere in the tree outside dist/: the tiles are a build output, never committed',
    heavy.length === 0 && existsSync(ROOTP + '.gitignore') && /^\/dist\/\s*$/m.test(readFileSync(ROOTP + '.gitignore', 'utf8')));
  ok('the honesty block says the tiles are built on demand into dist/sneeze/, not committed, not served by the Pages site, and the deployer hosts them with their own map.wasm',
    /dist\/sneeze\//.test(H.build_output) && /not committed/.test(H.build_output) && /Pages\s+site does not serve/.test(H.build_output) && /their own copy of map\.wasm/.test(H.build_output));
  ok('every committed record of the tiles is under spatial/registry/: tiles.json is tracked, spatial/sneeze/ does not exist',
    existsSync(ROOTP + 'spatial/registry/tiles.json') && !existsSync(ROOTP + 'spatial/sneeze'));
}
{
  const files = [new URL('./registry/tiles.json', import.meta.url), ...reg.manifests.map((m) => new URL(m.id + '.json', SNEEZE))];
  const texts = files.map((f) => readFileSync(f, 'utf8'));
  const glbJson = tiles.map((t) => { const b = tileBuf.get(t.id); return b.toString('utf8', 20, 20 + b.readUInt32LE(12)); });
  const PATH = /(^|[^a-z])\/(tmp|home|root|opt|Users)\//;
  // the model-family words are assembled from pieces so this file never carries one as a literal
  const KEY_OR_MODEL = new RegExp(['rk_[A-Za-z0-9]{8,}', 'BEGIN (RSA |EC )?PRIVATE', 'sk-[A-Za-z0-9]{16,}', ['cla', 'ude-'].join(''), ['op', 'us'].join(''), ['son', 'net'].join(''), ['hai', 'ku'].join('')].join('|'), 'i');
  ok('no machine path appears in the tiles registry, a manifest or any tile\'s JSON chunk',
    [...texts, ...glbJson].every((s) => !PATH.test(s)));
  ok('no key material, token or model identifier appears in the registry, a manifest or any tile\'s JSON chunk',
    [...texts, ...glbJson].every((s) => !KEY_OR_MODEL.test(s)));
  ok('no tile claims a named buyer, price, partner or conformance to a standard it did not verify',
    [...texts, ...glbJson].every((s) => !/\b(certified|conformant to|endorsed by|partnered with|licensed to)\b/i.test(s)));
}

console.log(`\nspatial/test_tiles: ${n} checks passed. ${tiles.length} tiles, ${reg.manifests.length} manifests, ${reg.budget.total_bytes} bytes.`);
console.log('NOT measured here: that Sneeze, Artemis or any other metaverse browser loads any of it. Nothing was run in either.');
