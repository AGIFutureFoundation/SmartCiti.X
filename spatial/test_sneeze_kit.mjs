/**
 * The Sneeze test kit (spatial/sneeze_kit/), held by what it does.
 *
 * Nothing in this repository has been loaded in Sneeze or Artemis. The kit is for the day a person can:
 * serve.py (static server), preflight.py (a check anyone can run without Sneeze), template.py + ingest.py
 * (a results format and the recorder that writes spatial/registry/sneeze_runs.json), CHECKLIST.md.
 *
 * WHAT THIS SUITE HOLDS
 *   - the server serves only dist/sneeze/ (every traversal form, symlink, dotfile, other extension -> 404),
 *     with the right types, CORS, Range, HEAD/OPTIONS, and the optional map.wasm door;
 *   - the pre-flight passes on the real build and FAILS BY NAME on a missing tile, a sha mismatch, a wrong
 *     MIME, a missing CORS header, a bad Range answer, an unknown manifest field, a bad sReference, a moved child,
 *     an altered anchor, an unlisted file, a registry row removed;
 *   - the ingest refuses a run with no person / version / date / OS / passing pre-flight / evidence, a different
 *     build, an unknown tile or field, a duplicate; flips only the proposed fields a run proved and whose
 *     per-tile observations support them; writes "observed in <engine> <version>" and never a stronger word;
 *   - every key the results schema requires is refused when missing;
 *   - the committed registry has zero runs and every status as it was ("not loaded").
 * WHAT IT DOES NOT HOLD. That Sneeze or Artemis loads anything. It cannot: nothing here runs either.
 *
 * SNEEZE_KIT_DIR may point at another copy of the kit (a mutation sandbox); --browser adds ONE headless
 * Chromium run proving the server's CORS and Range answers to a page on another origin.
 */
import { createHash } from 'node:crypto';
import { existsSync, readFileSync, writeFileSync, mkdtempSync, mkdirSync, rmSync, cpSync, symlinkSync, readdirSync, statSync } from 'node:fs';
import { spawn, spawnSync } from 'node:child_process';
import { tmpdir } from 'node:os';
import { join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import net from 'node:net';
import http from 'node:http';

let n = 0;
const ok = (m, c) => { if (!c) { console.error('FAIL', m); process.exit(1); } n++; console.log('  ok ', m); };
const sha = (b) => createHash('sha256').update(b).digest('hex');

const KIT = process.env.SNEEZE_KIT_DIR ? resolve(process.env.SNEEZE_KIT_DIR) : fileURLToPath(new URL('./sneeze_kit/', import.meta.url));
const ROOT = resolve(KIT, '..', '..');
const DIST = join(ROOT, 'dist', 'sneeze');
const TILES = join(ROOT, 'spatial', 'registry', 'tiles.json');
const RUNS = join(ROOT, 'spatial', 'registry', 'sneeze_runs.json');
const J = (p) => JSON.parse(readFileSync(p, 'utf8'));
const clone = (o) => JSON.parse(JSON.stringify(o));
const TMP = mkdtempSync(join(tmpdir(), 'sneezekit-'));
process.on('exit', () => { try { rmSync(TMP, { recursive: true, force: true }); } catch { /* best effort */ } });

const py = (script, args = [], opts = {}) => {
  const r = spawnSync('python3', ['-I', join(KIT, script), ...args], { encoding: 'utf8', cwd: TMP, maxBuffer: 1 << 26, ...opts });
  return { code: r.status, out: r.stdout || '', err: r.stderr || '' };
};

// async variant for the cases where THIS process hosts the server the script talks to (spawnSync would block it)
const pyA = (script, args = []) => new Promise((res) => {
  const p = spawn('python3', ['-I', join(KIT, script), ...args], { cwd: TMP });
  let out = '', err = '';
  p.stdout.on('data', (d) => { out += d; }); p.stderr.on('data', (d) => { err += d; });
  p.on('close', (code) => res({ code, out, err }));
});

// ---- the build must be there (it is a gitignored output): build once if not, exactly as the checklist says
const tiles = J(TILES);
const complete = () => existsSync(DIST) && tiles.tiles.every((t) => existsSync(join(DIST, t.reference))) && tiles.manifests.every((m) => existsSync(join(DIST, m.id + '.json')));
if (!complete()) spawnSync('python3', [join(ROOT, 'spatial', 'build.py')], { cwd: ROOT, encoding: 'utf8' });
ok('dist/sneeze/ is built (the kit tests need the real bytes)', complete());

// ------------------------------------------------------------- files, text
const FILES = ['_common.py', 'serve.py', 'preflight.py', 'template.py', 'ingest.py', 'results.schema.json', 'CHECKLIST.md'];
for (const f of FILES) ok(`kit file ${f} exists`, existsSync(join(KIT, f)));
const text = (f) => readFileSync(join(KIT, f), 'utf8');
for (const f of FILES) {
  const t = text(f);
  ok(`${f}: no machine path (no /tmp, /home, /opt, /root, /Users, drive letter)`, !/(^|[\s"'(=])(\/tmp|\/home|\/opt|\/root|\/Users|[A-Z]:\\)/m.test(t));
  ok(`${f}: no email address, no key material`, !/[\w.+-]+@[\w-]+\.[\w.-]+/.test(t) && !/rk_[A-Za-z0-9]{8}/.test(t));
}
const schema = J(join(KIT, 'results.schema.json'));
ok('the results schema is a 2020-12 JSON schema that refuses unknown keys at the top level', schema.$schema.includes('2020-12') && schema.additionalProperties === false);
ok('the schema requires person, date, engine, os, build, preflight, serve, manifests and screenshots',
  ['person', 'date', 'engine', 'os', 'build', 'preflight', 'serve', 'manifests', 'screenshots'].every((k) => schema.required.includes(k)));
ok('the schema only allows Sneeze or Artemis as the engine and has no "claimed" anywhere', JSON.stringify(schema.properties.engine.properties.name.enum) === '["Sneeze","Artemis"]' && !/claimed/i.test(JSON.stringify(schema)));
ok('every observation vocabulary is pass / fail / untested / not_applicable',
  ['appears', 'orientation', 'scale', 'child_position', 'smooth'].every((k) => JSON.stringify(schema.properties.manifests.items.properties.tiles.items.properties[k].enum) === '["pass","fail","untested","not_applicable"]'));

// ------------------------------------------------------------- raw HTTP
function raw(port, requestLine, headers = {}) {
  return new Promise((res) => {
    const s = net.connect(port, '127.0.0.1');
    let buf = Buffer.alloc(0);
    s.on('data', (d) => { buf = Buffer.concat([buf, d]); });
    s.on('error', () => res({ status: 0, headers: {}, body: Buffer.alloc(0) }));
    s.on('close', () => {
      const i = buf.indexOf('\r\n\r\n');
      const head = buf.subarray(0, i < 0 ? buf.length : i).toString('latin1').split('\r\n');
      const hd = {};
      for (const l of head.slice(1)) { const k = l.indexOf(':'); if (k > 0) hd[l.slice(0, k).toLowerCase()] = l.slice(k + 1).trim(); }
      res({ status: Number((head[0] || '').split(' ')[1]) || 0, headers: hd, body: i < 0 ? Buffer.alloc(0) : buf.subarray(i + 4) });
    });
    s.write(`${requestLine}\r\nHost: localhost\r\nConnection: close\r\n${Object.entries(headers).map(([k, v]) => `${k}: ${v}\r\n`).join('')}\r\n`);
  });
}
const GET = (port, path, headers) => raw(port, `GET ${path} HTTP/1.1`, headers);

function startServer(args) {
  return new Promise((res, rej) => {
    const p = spawn('python3', ['-I', join(KIT, 'serve.py'), '--port', '0', ...args], { cwd: TMP });
    let out = '';
    const timer = setTimeout(() => rej(new Error('server did not start: ' + out)), 15000);
    p.stdout.on('data', (d) => { out += d; if (out.includes('Ctrl-C')) { clearTimeout(timer); const m = out.match(/at http:\/\/127\.0\.0\.1:(\d+)\//); res({ port: Number(m[1]), p, text: () => out, stop: () => new Promise((r) => { p.on('close', () => r(out)); p.kill('SIGINT'); }) }); } });
    p.stderr.on('data', () => {});
    p.on('close', () => { clearTimeout(timer); });
  });
}

// =========================================================== the server
const real = await startServer([]);
ok('serve.py prints one full address per manifest, 9 of them, all under 127.0.0.1', tiles.manifests.every((m) => real.text().includes(`http://127.0.0.1:${real.port}/${m.id}.json`)) && (real.text().match(/^ {2}http:\/\/127\.0\.0\.1:\d+\/[a-z0-9-]+\.json$/gm) || []).length === 9);
ok('serve.py says it serves only that folder and (without --map-wasm) does not list local manifests', /only that folder/.test(real.text()) && !/\.local\.json/.test(real.text()));
{
  const m = tiles.manifests[0], t0 = tiles.tiles.find((t) => t.id === m.tiles[0]);
  const a = await GET(real.port, `/${m.id}.json`);
  ok('a manifest is served 200 as application/json with the recorded bytes', a.status === 200 && a.headers['content-type'] === 'application/json' && sha(a.body) === m.sha256);
  const b = await GET(real.port, `/${t0.reference}`);
  ok('a tile is served 200 as model/gltf-binary with the recorded sha256', b.status === 200 && b.headers['content-type'] === 'model/gltf-binary' && sha(b.body) === t0.sha256 && b.body.subarray(0, 4).toString() === 'glTF');
  ok('CORS: Access-Control-Allow-Origin * and Range exposed on a tile', b.headers['access-control-allow-origin'] === '*' && /Content-Range/i.test(b.headers['access-control-expose-headers'] || '') && /Range/.test(b.headers['access-control-allow-headers'] || ''));
  ok('nothing is cached and nothing is sniffed (no-store, nosniff)', b.headers['cache-control'] === 'no-store' && b.headers['x-content-type-options'] === 'nosniff');
  ok('Accept-Ranges: bytes is advertised', b.headers['accept-ranges'] === 'bytes');
  const r1 = await GET(real.port, `/${t0.reference}`, { Range: 'bytes=0-3' });
  ok('Range bytes=0-3 -> 206, the glTF magic, an exact Content-Range', r1.status === 206 && r1.body.toString() === 'glTF' && r1.headers['content-range'] === `bytes 0-3/${t0.bytes}` && r1.headers['content-length'] === '4');
  const r2 = await GET(real.port, `/${t0.reference}`, { Range: 'bytes=-8' });
  ok('a suffix range returns the last 8 bytes', r2.status === 206 && r2.body.equals(b.body.subarray(b.body.length - 8)));
  const r3 = await GET(real.port, `/${t0.reference}`, { Range: `bytes=${t0.bytes - 4}-` });
  ok('an open-ended range returns the tail', r3.status === 206 && r3.body.equals(b.body.subarray(b.body.length - 4)));
  const r4 = await GET(real.port, `/${t0.reference}`, { Range: `bytes=${t0.bytes + 10}-${t0.bytes + 20}` });
  ok('a range past the end -> 416 with Content-Range bytes */size', r4.status === 416 && r4.headers['content-range'] === `bytes */${t0.bytes}`);
  const r5 = await GET(real.port, `/${t0.reference}`, { Range: 'bytes=0-3,10-20' });
  ok('a multi-range request is answered with the whole file (allowed by HTTP), not garbage', r5.status === 200 && r5.body.equals(b.body));
  const r6 = await GET(real.port, `/${t0.reference}`, { Range: 'bytes=0-999999999' });
  ok('a range end beyond the file is clamped to the file', r6.status === 206 && r6.body.equals(b.body));
  const h = await raw(real.port, `HEAD /${t0.reference} HTTP/1.1`);
  ok('HEAD gives the headers and length but no body', h.status === 200 && Number(h.headers['content-length']) === t0.bytes && h.body.length === 0);
  const o = await raw(real.port, `OPTIONS /${t0.reference} HTTP/1.1`, { Origin: 'http://elsewhere.test', 'Access-Control-Request-Method': 'GET', 'Access-Control-Request-Headers': 'range' });
  ok('an OPTIONS preflight answers 204 with the CORS allow headers', o.status === 204 && o.headers['access-control-allow-origin'] === '*' && /GET/.test(o.headers['access-control-allow-methods']) && /Range/i.test(o.headers['access-control-allow-headers']));
  const po = await raw(real.port, `POST /${m.id}.json HTTP/1.1`, { 'Content-Length': '0' });
  ok('POST / PUT / DELETE are 405, nothing can be written', po.status === 405 && (await raw(real.port, `PUT /${m.id}.json HTTP/1.1`)).status === 405 && (await raw(real.port, `DELETE /${m.id}.json HTTP/1.1`)).status === 405);
  const ix = await GET(real.port, '/');
  ok('/ is a generated index listing the 9 manifests (not a directory listing)', ix.status === 200 && /text\/html/.test(ix.headers['content-type']) && tiles.manifests.every((x) => ix.body.toString().includes(`/${x.id}.json`)) && !ix.body.toString().includes('.glb'));
  ok('a directory path (/tiles, /tiles/) is 404, not a listing', (await GET(real.port, '/tiles')).status === 404 && (await GET(real.port, '/tiles/')).status === 404);
  ok('an unknown file is 404 and a long target is refused', (await GET(real.port, '/nope.json')).status === 404 && (await GET(real.port, '/' + 'a'.repeat(3000) + '.json')).status === 414);
  ok('/wasm/map.wasm and <id>.local.json are 404 when --map-wasm was not given', (await GET(real.port, '/wasm/map.wasm')).status === 404 && (await GET(real.port, `/${m.id}.local.json`)).status === 404);
  await GET(real.port, `/${t0.reference}`);
}
{
  const final = await real.stop();
  ok('on exit it reports which tiles the viewer fetched and which it never asked for', /tiles fetched by the viewer: 1 of 29/.test(final) && /never fetched: .*parish-22051/.test(final));
}

// ---- traversal: a sandbox with secrets beside, above and next to the served folder
const SITE = join(TMP, 'site');
mkdirSync(SITE);
cpSync(DIST, join(SITE, 'sneeze'), { recursive: true });
mkdirSync(join(SITE, 'sneeze-evil'));
const MARK = 'SECRET-MARKER-' + sha(String(Math.random())).slice(0, 12);
writeFileSync(join(SITE, 'secret.json'), JSON.stringify({ MARK }));
writeFileSync(join(SITE, 'sneeze-evil', 'secret.json'), JSON.stringify({ MARK }));
writeFileSync(join(SITE, 'sneeze-evil', 'secret.glb'), MARK);
writeFileSync(join(SITE, 'sneeze', '.hidden.json'), JSON.stringify({ MARK }));
writeFileSync(join(SITE, 'sneeze', 'notes.txt'), MARK);
writeFileSync(join(SITE, 'sneeze', 'page.html'), MARK);
mkdirSync(join(SITE, 'sneeze', 'tiles', '.git'));
writeFileSync(join(SITE, 'sneeze', 'tiles', '.git', 'config.json'), MARK);
let linked = true;
try { symlinkSync(join(SITE, 'secret.json'), join(SITE, 'sneeze', 'link.json')); symlinkSync(join(SITE, 'sneeze-evil'), join(SITE, 'sneeze', 'evildir')); } catch { linked = false; }
const sb = await startServer(['--dist', join(SITE, 'sneeze')]);
const attempts = [
  '/../secret.json', '/../../secret.json', '/%2e%2e/secret.json', '/%2E%2E/secret.json', '/tiles/../../secret.json', '/tiles/%2e%2e/%2e%2e/secret.json',
  '/..%2fsecret.json', '/%2e%2e%2fsecret.json', '/tiles/..%2f..%2fsecret.json', '/..%5csecret.json', '/..\\secret.json', '/%252e%252e/secret.json',
  '/%2e%2e/sneeze-evil/secret.json', '/../sneeze-evil/secret.json', '/../sneeze-evil/secret.glb', '/parishes.json/../../secret.json', '/./parishes.json/../../secret.json',
  '//secret.json', '///etc/passwd', '/secret.json%00.glb', '/parishes.json%00', '/%00/secret.json', '/tiles//../../secret.json', '/..;/secret.json', '/%c0%ae%c0%ae/secret.json',
  '/.hidden.json', '/tiles/.git/config.json', '/notes.txt', '/page.html', '/tiles', '/link.json', '/evildir/secret.json', '/evildir/secret.glb',
];
let leaked = [];
for (const a of attempts) {
  const r = await GET(sb.port, a);
  if (r.status === 200 && r.body.toString('latin1').includes(MARK)) leaked.push(a);
  if (r.body.toString('latin1').includes(MARK)) leaked.push('body:' + a);
}
ok(`none of ${attempts.length} traversal / dotfile / other-extension / outside-folder requests returns the secret`, leaked.length === 0 && (leaked.length === 0 || (console.log('   leaked:', leaked), false)));
ok('each of them is a 4xx (404 / 400 / 414), never 200', (await Promise.all(attempts.map((a) => GET(sb.port, a)))).every((r) => r.status >= 400 && r.status < 500));
ok('an absolute-form request target cannot escape either', (await raw(sb.port, 'GET http://localhost/../secret.json HTTP/1.1')).status >= 400 || !(await raw(sb.port, 'GET http://localhost/../secret.json HTTP/1.1')).body.toString().includes(MARK));
if (linked) ok('a symlink inside the folder that points outside it is not followed (file or directory)', (await GET(sb.port, '/link.json')).status === 404 && (await GET(sb.port, '/evildir/secret.json')).status === 404);
ok('the served folder itself still serves (the guard is not just refusing everything)', (await GET(sb.port, '/parishes.json')).status === 200);
await sb.stop();

// ---- the optional map.wasm door
{
  const wasm = join(TMP, 'my_map.wasm');
  const wbytes = Buffer.concat([Buffer.from([0, 0x61, 0x73, 0x6d, 1, 0, 0, 0]), Buffer.from('test module')]);
  writeFileSync(wasm, wbytes);
  const s = await startServer(['--map-wasm', wasm]);
  const w = await GET(s.port, '/wasm/map.wasm');
  ok('--map-wasm serves that one file at /wasm/map.wasm as application/wasm and prints its sha256', w.status === 200 && w.headers['content-type'] === 'application/wasm' && w.body.equals(wbytes) && s.text().includes(sha(wbytes)));
  const lv = await GET(s.port, '/parishes.local.json');
  const asBuilt = J(join(DIST, 'parishes.json')), local = JSON.parse(lv.body.toString());
  const stripped = clone(local); stripped.Modules = asBuilt.Modules;
  ok('<id>.local.json is the as-built manifest with only Modules[].sUrl pointing at wasm/map.wasm', lv.status === 200 && local.Modules[0].sUrl === 'wasm/map.wasm' && JSON.stringify(stripped) === JSON.stringify(asBuilt));
  ok('the .local.json listing is printed, one per manifest', tiles.manifests.every((m) => s.text().includes(`/${m.id}.local.json`)));
  ok('only the one named file is exposed: no other path under /wasm/, no .local.json for an unknown id or a path', (await GET(s.port, '/wasm/other.wasm')).status === 404 && (await GET(s.port, '/nosuch.local.json')).status === 404 && (await GET(s.port, '/tiles/../parishes.local.json')).status === 404 && (await GET(s.port, '/..%2fparishes.local.json')).status === 404);
  ok('the as-built manifests are still served unchanged beside the local ones', sha((await GET(s.port, '/parishes.json')).body) === tiles.manifests.find((m) => m.id === 'parishes').sha256);
  await s.stop();
}

// =========================================================== the pre-flight
const parseFails = (o) => (o.out.match(/^FAIL .*$/gm) || []).map((l) => l.slice(5));
const pfReal = py('preflight.py', ['--out', join(TMP, 'pf.json')]);
const pfOk = (pfReal.out.match(/^ {2}ok /gm) || []).length;
ok(`the pre-flight passes on the real build (${pfOk} checks), exit 0`, pfReal.code === 0 && parseFails(pfReal).length === 0 && pfOk >= 300);
const pfJson = J(join(TMP, 'pf.json'));
ok('its report carries the measured sha256 of all 9 manifests and 29 tiles, equal to the registry, and the build stamp',
  pfJson.passed === true && pfJson.tiles_source_stamp === tiles.source_stamp && tiles.manifests.every((m) => pfJson.manifest_sha256[m.id] === m.sha256) && tiles.tiles.every((t) => pfJson.tile_sha256[t.id] === t.sha256));
ok('it lists the proposed fields the manifests use, and says it does not show Sneeze loads anything', /proposed \(not documented by Sneeze\) fields.*Data\.Anchors/.test(pfReal.out) && /does not show that Sneeze or Artemis loads them/.test(pfReal.out));
{
  const s = await startServer([]);
  const viaUrl = py('preflight.py', ['--url', `http://127.0.0.1:${s.port}/`]);
  ok('the pre-flight also passes against an already-running serve.py (--url)', viaUrl.code === 0 && parseFails(viaUrl).length === 0);
  await s.stop();
}

function sandboxDist(name) {
  const d = join(TMP, name);
  mkdirSync(d);
  cpSync(DIST, join(d, 'dist'), { recursive: true });
  const reg = clone(tiles);
  return { dir: join(d, 'dist'), regPath: join(d, 'tiles.json'), reg, save() { writeFileSync(this.regPath, JSON.stringify(this.reg)); }, run() { this.save(); return py('preflight.py', ['--dist', this.dir, '--registry', this.regPath]); } };
}
function expectFail(name, mutate, wantSubstr) {
  const sbx = sandboxDist(name);
  mutate(sbx);
  const r = sbx.run();
  const fails = parseFails(r);
  ok(`pre-flight mutation "${name}": exit 1 and a FAIL naming "${wantSubstr}"`, r.code === 1 && fails.some((f) => f.includes(wantSubstr)));
  return { r, fails };
}
// editing a manifest AND the registry's record of it, so only the rule under test can fail
function editManifest(sbx, id, fn) {
  const p = join(sbx.dir, id + '.json');
  const doc = J(p);
  fn(doc);
  const txt = JSON.stringify(doc, null, 3) + '\n';
  writeFileSync(p, txt);
  const rec = sbx.reg.manifests.find((m) => m.id === id);
  rec.sha256 = sha(txt); rec.bytes = Buffer.byteLength(txt);
}

expectFail('missing tile', (s) => rmSync(join(s.dir, 'tiles', 'parish-22071.glb')), 'folder holds exactly the files');
expectFail('missing tile (answers 200)', (s) => rmSync(join(s.dir, 'tiles', 'parish-22071.glb')), 'parish-22071 answers 200');
expectFail('missing manifest', (s) => rmSync(join(s.dir, 'bayarea.json')), 'bayarea.json answers 200');
expectFail('sha mismatch (one byte flipped, same length)', (s) => { const p = join(s.dir, 'tiles', 'county-06075.glb'); const b = readFileSync(p); b[b.length - 1] ^= 1; writeFileSync(p, b); }, 'county-06075 bytes equal the recorded sha256');
expectFail('truncated tile', (s) => { const p = join(s.dir, 'tiles', 'wild-delta.glb'); writeFileSync(p, readFileSync(p).subarray(0, 5000)); }, 'wild-delta bytes equal the recorded sha256');
expectFail('not a glb', (s) => { const p = join(s.dir, 'tiles', 'wild-forest.glb'); const b = readFileSync(p); b.write('xxxx', 0); writeFileSync(p, b); }, 'wild-forest starts with the glTF magic');
expectFail('manifest bytes differ from the registry', (s) => { const p = join(s.dir, 'campus-oakland.json'); writeFileSync(p, readFileSync(p, 'utf8').replace('Oakland', 'Oakland ')); }, 'campus-oakland.json bytes equal the recorded sha256');
expectFail('registry sha changed', (s) => { s.reg.tiles.find((t) => t.id === 'parish-22005').sha256 = '0'.repeat(64); }, 'parish-22005 bytes equal the recorded sha256');
expectFail('unlisted extra file', (s) => writeFileSync(join(s.dir, 'tiles', 'extra.glb'), 'glTF'), 'folder holds exactly the files');
expectFail('unlisted extra manifest', (s) => writeFileSync(join(s.dir, 'extra.json'), '{}'), 'folder holds exactly the files');
expectFail('manifest is not JSON', (s) => editManifestRaw(s, 'wilds-canyon', '{ not json'), 'wilds-canyon.json parses as JSON');
function editManifestRaw(sbx, id, txt) {
  writeFileSync(join(sbx.dir, id + '.json'), txt);
  const rec = sbx.reg.manifests.find((m) => m.id === id);
  rec.sha256 = sha(txt); rec.bytes = Buffer.byteLength(txt);
}
const shapeName = (id) => `${id}.json follows the documented manifest shape`;
expectFail('Rotation added to a node (not in the registry table)', (s) => editManifest(s, 'parishes', (d) => { d.Data.Scene.Transform.Rotation = [0, 0, 0, 1]; }), shapeName('parishes'));
expectFail('unknown field directly on a node', (s) => editManifest(s, 'wilds-delta', (d) => { d.Data.Scene.Colour = 'red'; }), shapeName('wilds-delta'));
expectFail('unknown field directly on a child node', (s) => editManifest(s, 'parishes', (d) => { d.Data.Scene.aChildren[1].Mesh = 'x'; }), shapeName('parishes'));
expectFail('Scale added to a child', (s) => editManifest(s, 'bayarea', (d) => { d.Data.Scene.aChildren[0].Transform.Scale = [1, 1, 1]; }), shapeName('bayarea'));
expectFail('unknown Data field', (s) => editManifest(s, 'wilds-delta', (d) => { d.Data.Lighting = {}; }), shapeName('wilds-delta'));
expectFail('lighting block "Primary" added (the docs disagree on it)', (s) => editManifest(s, 'wilds-delta', (d) => { d.Data.Primary = { Ambient: [1, 1, 1] }; }), shapeName('wilds-delta'));
expectFail('unknown top-level field', (s) => editManifest(s, 'campus-oakland', (d) => { d.Extras = 1; }), shapeName('campus-oakland'));
expectFail('lower-case "container" instead of Container', (s) => editManifest(s, 'campus-oakland', (d) => { d.container = d.Container; delete d.Container; }), shapeName('campus-oakland'));
expectFail('Services made non-empty', (s) => editManifest(s, 'campus-oakland', (d) => { d.Services = [{ name: 'x' }]; }), shapeName('campus-oakland'));
expectFail('Head.Self not a class-letter id', (s) => editManifest(s, 'campus-oakland', (d) => { d.Data.Scene.Head.Self = 'oops'; }), shapeName('campus-oakland'));
expectFail('Modules entry without sUrl', (s) => editManifest(s, 'campus-oakland', (d) => { d.Modules = [{}]; }), shapeName('campus-oakland'));
expectFail('malformed sHash', (s) => editManifest(s, 'campus-oakland', (d) => { d.Modules[0].sHash = 'abc'; }), shapeName('campus-oakland'));
expectFail('Position with a NaN-like string', (s) => editManifest(s, 'parishes', (d) => { d.Data.Scene.aChildren[0].Transform.Position = [1, 'x', 0]; }), shapeName('parishes'));
expectFail('sReference made absolute', (s) => editManifest(s, 'campus-oakland', (d) => { d.Data.Scene.Resource.sReference = 'https://example.test/tiles/campus-oakland.glb'; }), shapeName('campus-oakland'));
expectFail('sReference made root-relative', (s) => editManifest(s, 'campus-oakland', (d) => { d.Data.Scene.Resource.sReference = '/tiles/campus-oakland.glb'; }), shapeName('campus-oakland'));
expectFail('sReference over 128 bytes', (s) => editManifest(s, 'campus-oakland', (d) => { d.Data.Scene.Resource.sReference = 'tiles/' + 'a'.repeat(130) + '.glb'; }), shapeName('campus-oakland'));
expectFail('sReference to a tile that does not exist', (s) => editManifest(s, 'campus-oakland', (d) => { d.Data.Scene.Resource.sReference = 'tiles/nope.glb'; }), 'resolves inside the served folder to a registry tile');
expectFail('sReference with a .. step (it would resolve, but it is not the plain path the registry records)', (s) => editManifest(s, 'campus-oakland', (d) => { d.Data.Scene.Resource.sReference = 'tiles/../tiles/campus-oakland.glb'; }), shapeName('campus-oakland'));
expectFail('sReference with a query string', (s) => editManifest(s, 'campus-oakland', (d) => { d.Data.Scene.Resource.sReference = 'tiles/campus-oakland.glb?x=1'; }), shapeName('campus-oakland'));
expectFail('manifest points at another manifest\'s tile', (s) => editManifest(s, 'campus-oakland', (d) => { d.Data.Scene.Resource.sReference = 'tiles/campus-new-orleans.glb'; }), 'references exactly its 1 tile');
expectFail('a child tile dropped from the manifest', (s) => editManifest(s, 'parishes', (d) => { d.Data.Scene.aChildren.pop(); }), 'references exactly its 13 tile');
expectFail('a tile referenced twice', (s) => editManifest(s, 'parishes', (d) => { d.Data.Scene.aChildren.push(d.Data.Scene.aChildren[0]); }), 'references exactly its 13 tile');
expectFail('a child moved by 1 m', (s) => editManifest(s, 'parishes', (d) => { d.Data.Scene.aChildren[3].Transform.Position[0] += 1; }), 'parishes.json child positions equal the recorded offsets');
expectFail('a child position removed', (s) => editManifest(s, 'bayarea', (d) => { delete d.Data.Scene.aChildren[2].Transform; }), 'bayarea.json child positions equal the recorded offsets');
expectFail('an anchor latitude altered', (s) => editManifest(s, 'campus-oakland', (d) => { d.Data.Anchors[0].GeoPose.position.lat += 0.001; }), 'campus-oakland.json GeoPose anchors equal the registry');
expectFail('a provenance word upgraded', (s) => editManifest(s, 'parishes', (d) => { d.Data.Provenance['parish-22005'] = 'RECORDED'; }), 'parishes.json provenance words equal the registry');
expectFail('registry loses the Data.Anchors field row', (s) => { s.reg.field_status = s.reg.field_status.filter((r) => !r.field.startsWith('manifest.Data.Anchors')); }, 'registry field table has a row for manifest.Data.Anchors');
expectFail('...and the manifests then use a field outside the table', (s) => { s.reg.field_status = s.reg.field_status.filter((r) => !r.field.startsWith('manifest.Data.Anchors')); }, 'uses only fields the registry table lists');
expectFail('registry loses the node.Transform.Position row', (s) => { s.reg.field_status = s.reg.field_status.filter((r) => r.field !== 'node.Transform.Position'); }, 'registry field table has a row for node.Transform.Position');
expectFail('dist folder missing', (s) => rmSync(s.dir, { recursive: true }), 'dist folder exists');
{
  const s = sandboxDist('clean-control');
  const r = s.run();
  ok('control: the same sandbox without a mutation passes (so each FAIL above is the mutation)', r.code === 0 && parseFails(r).length === 0);
}
{
  // a one-rule mutation produces only that rule's FAIL (the checks are not all failing together)
  const x = expectFail('single rule isolation', (s) => editManifest(s, 'parishes', (d) => { d.Data.Scene.aChildren[3].Transform.Position[0] += 1; }), 'child positions');
  ok('a moved child fails exactly one check, not the whole run', x.fails.length === 1);
}

// ---- wrong MIME / CORS / Range: a stand-in server that answers differently, checked over --url
function mutantServer(opt) {
  const srv = http.createServer((req, res) => {
    const u = decodeURIComponent(req.url.split('?')[0]);
    const f = resolve(DIST, '.' + u);
    if (!f.startsWith(DIST) || !existsSync(f) || !statSync(f).isFile()) { res.writeHead(404); res.end(); return; }
    const buf = readFileSync(f);
    const isGlb = f.endsWith('.glb');
    const h = { 'Content-Type': isGlb ? (opt.glbType ?? 'model/gltf-binary') : (opt.jsonType ?? 'application/json'), 'Content-Length': buf.length };
    if (!opt.noCors) h['Access-Control-Allow-Origin'] = '*';
    if (req.headers.range && opt.badRange) { res.writeHead(206, { ...h, 'Content-Length': 4, 'Content-Range': 'bytes 0-3/9' }); res.end('XXXX'); return; }
    res.writeHead(200, h); res.end(buf);
  });
  return new Promise((r) => srv.listen(0, '127.0.0.1', () => r(srv)));
}
async function viaMutant(name, opt, want) {
  const srv = await mutantServer(opt);
  const r = await pyA('preflight.py', ['--url', `http://127.0.0.1:${srv.address().port}/`]);
  srv.close();
  const fails = parseFails(r);
  ok(`pre-flight mutation "${name}": exit 1 and a FAIL naming "${want}"`, r.code === 1 && fails.some((f) => f.includes(want)));
  return fails;
}
{
  const c = await mutantServer({});
  const r = await pyA('preflight.py', ['--url', `http://127.0.0.1:${c.address().port}/`]);
  c.close();
  ok('control: a plain correct stand-in server passes (a server that ignores Range with a full 200 is acceptable HTTP)', r.code === 0 && parseFails(r).length === 0);
}
const f1 = await viaMutant('glb served as application/octet-stream', { glbType: 'application/octet-stream' }, 'is served as model/gltf-binary');
ok('...and every one of the 29 tiles is named', f1.filter((f) => f.includes('is served as model/gltf-binary')).length === 29);
await viaMutant('glb served as model/gltf+json', { glbType: 'model/gltf+json' }, 'is served as model/gltf-binary');
await viaMutant('glb served as text/plain', { glbType: 'text/plain' }, 'is served as model/gltf-binary');
await viaMutant('manifest served as text/plain', { jsonType: 'text/plain' }, 'is served as application/json');
await viaMutant('manifest served as text/html', { jsonType: 'text/html' }, 'is served as application/json');
await viaMutant('no CORS header', { noCors: true }, 'has a CORS allow-origin header');
await viaMutant('a Range request answered with the wrong bytes', { badRange: true }, 'answers a Range request correctly');
{
  const r = py('preflight.py', ['--url', 'http://127.0.0.1:1/']);
  ok('an unreachable server fails (exit 1) and says so, it does not pass by default', r.code === 1 && parseFails(r).length > 0);
}

// =========================================================== template + ingest
const pfPath = join(TMP, 'pf.json');
const tpl = py('template.py', ['--preflight', pfPath, '--out', join(TMP, 'tpl.json'), '--repo-commit', 'abc1234']);
ok('template.py writes a results file from a passing pre-flight', tpl.code === 0 && existsSync(join(TMP, 'tpl.json')));
const T = J(join(TMP, 'tpl.json'));
ok('the template has all 9 manifests, 29 tiles, every observation "untested" (or not_applicable for a single tile), and 8 proposed fields untested',
  T.manifests.length === 9 && T.manifests.reduce((a, m) => a + m.tiles.length, 0) === 29
  && T.manifests.every((m) => m.loaded === 'untested' && m.tiles.every((t) => ['appears', 'orientation', 'scale', 'smooth'].every((k) => t[k] === 'untested')))
  && T.fields.length === 8 && T.fields.every((f) => f.verdict === 'untested') && tiles.field_status.filter((r) => r.status === 'proposed').length === 8);
ok('the template carries the pre-flight hashes and the registry stamp, and a "FILL IN" where a person, date, engine and OS belong',
  T.build.tiles_source_stamp === tiles.source_stamp && T.preflight.passed === true && Object.keys(T.preflight.tile_sha256).length === 29
  && /FILL IN/.test(T.person.name + T.date + T.engine.name + T.os.name + T.os.version));
ok('template.py refuses with no pre-flight (exit 2)', py('template.py', ['--out', join(TMP, 'x.json')]).code === 2);
{
  const bad = clone(pfJson); bad.passed = false; writeFileSync(join(TMP, 'pf_bad.json'), JSON.stringify(bad));
  const r = py('template.py', ['--preflight', join(TMP, 'pf_bad.json'), '--out', join(TMP, 'x2.json')]);
  ok('template.py refuses a pre-flight that did not pass (exit 1, nothing written)', r.code === 1 && !existsSync(join(TMP, 'x2.json')));
  const bad2 = clone(pfJson); bad2.tiles_source_stamp = 'f'.repeat(16); writeFileSync(join(TMP, 'pf_bad2.json'), JSON.stringify(bad2));
  ok('template.py refuses a pre-flight from a different build', py('template.py', ['--preflight', join(TMP, 'pf_bad2.json'), '--out', join(TMP, 'x3.json')]).code === 1);
}
const guide = py('template.py', ['--guide']).out;
ok('--guide prints a row for every one of the 29 tiles with size and direction, computed from the registry', tiles.tiles.every((t) => guide.includes(`${t.id} |`)) && /km (east|west), .* km (north|south)/.test(guide));

const H1 = 'a'.repeat(64), H2 = 'b'.repeat(64), H3 = 'c'.repeat(64);
const TODAY = '2026-10-23';
function goodRun() {
  const r = clone(T);
  r.person = { name: 'Ada Tester' };
  r.date = '2026-10-20';
  r.engine = { name: 'Sneeze', commit: 'abc1234def56', installed_from: 'source' };
  r.os = { name: 'Ubuntu', version: '24.04', arch: 'x86_64' };
  r.build.repo_commit = '86c9906';
  r.screenshots = [{ sha256: H1, caption: 'parishes, all 13 tiles, from above' }, { sha256: H2, caption: 'campus-oakland from the side' }];
  const man = (id) => r.manifests.find((m) => m.id === id);
  const p = man('parishes');
  p.loaded = 'yes'; p.screenshots = [H1];
  p.tiles.forEach((t, i) => { t.appears = 'pass'; t.orientation = 'pass'; t.scale = 'pass'; t.smooth = 'pass'; if (i > 0) t.child_position = 'pass'; });
  const c = man('campus-oakland');
  c.loaded = 'yes'; c.tiles[0].appears = 'pass'; c.tiles[0].orientation = 'pass';
  man('wilds-delta').loaded = 'no';
  man('wilds-delta').tiles[0].appears = 'fail';
  const f = (name) => r.fields.find((x) => x.field.startsWith(name));
  Object.assign(f('manifest.Data.Provenance'), { verdict: 'observed', evidence: 'parishes opened with the Provenance block present and no error in the log', screenshots: [H1] });
  Object.assign(f('world horizontal axes'), { verdict: 'observed', evidence: 'Orleans sat east and south of Ascension; borders touched', screenshots: [H1] });
  return r;
}
let seq = 0;
function ingest(run, { extra = [], runsFile, registry } = {}) {
  const id = ++seq;
  const rf = join(TMP, `run${id}.json`);
  writeFileSync(rf, JSON.stringify(run, null, 1));
  const rp = runsFile ?? join(TMP, `runs${id}.json`);
  const r = py('ingest.py', [rf, '--runs', rp, '--today', TODAY, ...(registry ? ['--registry', registry] : []), ...extra]);
  return { ...r, runs: existsSync(rp) ? J(rp) : null, rp };
}
const stat = (doc, f) => doc.field_status.find((x) => x.field.startsWith(f)).status;

// ---- a good run
const good = ingest(goodRun());
ok('a complete run is recorded (exit 0)', good.code === 0 && good.runs.run_count === 1 && good.runs.runs[0].build_match === true);
{
  const d = good.runs;
  ok('the proven proposed fields flip to exactly "observed in Sneeze <version>"', stat(d, 'manifest.Data.Provenance') === 'observed in Sneeze commit abc1234def56' && stat(d, 'world horizontal axes') === 'observed in Sneeze commit abc1234def56');
  const changed = d.field_status.filter((f) => f.status !== f.registry_status).map((f) => f.field);
  ok('ONLY those two fields changed: the other six proposed fields stay "proposed", the documented ones stay "documented"',
    changed.length === 2 && d.field_status.filter((f) => f.registry_status === 'proposed' && f.status === 'proposed').length === 6 && d.field_status.filter((f) => f.registry_status === 'documented').every((f) => f.status === 'documented'));
  ok('the field not claimed in the run (GeoPose consumed) is untouched even though the manifest loaded', stat(d, 'GeoPose anchor consumed') === 'proposed' && stat(d, 'manifest.Data.Anchors') === 'proposed');
  const allowed = /^(proposed|documented|observed in Sneeze commit abc1234def56)$/;
  ok('every status in the file is proposed, documented or "observed in ..."; the word "claimed" appears nowhere', d.field_status.every((f) => allowed.test(f.status)) && !/claimed/i.test(readFileSync(good.rp, 'utf8')));
  const ms = Object.fromEntries(d.manifest_status.map((m) => [m.id, m.status]));
  ok('manifest statuses: parishes and campus-oakland observed loaded; wilds-delta "tried and did not load"; the other six keep the registry\'s "not loaded" text',
    ms.parishes === 'observed loaded in Sneeze commit abc1234def56' && ms['campus-oakland'] === 'observed loaded in Sneeze commit abc1234def56' && ms['wilds-delta'] === 'tried and did not load in Sneeze commit abc1234def56'
    && ['bayarea', 'wilds-mountain', 'wilds-forest', 'wilds-canyon', 'campus-treasure-island', 'campus-new-orleans'].every((id) => ms[id] === tiles.manifests.find((m) => m.id === id).status && /not loaded/.test(ms[id])));
  const ts = Object.fromEntries(d.tile_status.map((t) => [t.tile, t]));
  ok('tile statuses: the 13 parish tiles and the campus tile "observed appearing"; wild-delta (fail) is not; per-check pass/fail lists kept',
    d.tile_status.filter((t) => /^observed appearing in/.test(t.status)).length === 14 && !/observed/.test(ts['wild-delta'].status) && ts['wild-delta'].checks.appears.fail[0].startsWith('Sneeze') && ts['campus-oakland'].checks.orientation.pass.length === 1);
  ok('each proposed field row says what "observed" means, in words that do not overreach', d.field_status.filter((f) => f.registry_status === 'proposed').every((f) => f.observed_means.length > 20) && /does NOT mean the engine uses/.test(d.field_status.find((f) => f.field.startsWith('manifest.Data.Anchors')).observed_means));
  ok('the run is stored with who, when, version, OS and a content-derived run id', d.runs[0].run.person.name === 'Ada Tester' && d.runs[0].run.date === '2026-10-20' && /^[0-9a-f]{16}$/.test(d.runs[0].run_id) && d.runs[0].run.os.name === 'Ubuntu');
  ok('screenshots are stored by hash only', d.runs[0].run.screenshots.every((s) => /^[0-9a-f]{64}$/.test(s.sha256)) && !/data:image|base64/.test(JSON.stringify(d)));
  const chk = py('ingest.py', ['--check', '--runs', good.rp]);
  ok('--check agrees that the file is exactly what its runs derive', chk.code === 0);
  ok('a dry run records nothing', (() => { const rf = join(TMP, 'dry.json'); writeFileSync(rf, JSON.stringify(goodRun())); const rp = join(TMP, 'dry_runs.json'); const r = py('ingest.py', [rf, '--runs', rp, '--today', TODAY, '--dry-run']); return r.code === 0 && /would be recorded/.test(r.out) && !existsSync(rp); })());
  const again = py('ingest.py', [join(TMP, 'run1.json'), '--runs', good.rp, '--today', TODAY]);
  ok('the same run twice is refused and nothing changes', again.code === 1 && /already recorded/.test(again.err) && J(good.rp).run_count === 1);
}

// ---- refusals: each is a fresh runs file that must stay absent
function refuse(name, mutate, want) {
  const r = goodRun();
  mutate(r);
  const x = ingest(r);
  ok(`refused: ${name}`, x.code === 1 && x.runs === null && /REFUSED/.test(x.err) && (want ? want.test(x.err) : true));
  return x;
}
refuse('no person (empty name)', (r) => { r.person.name = ''; }, /person/);
refuse('no person (key missing)', (r) => { delete r.person; }, /person/);
refuse('person is "anonymous"', (r) => { r.person.name = 'Anonymous'; }, /person\.name/);
refuse('person still the template placeholder', (r) => { r.person.name = 'FILL IN your name or public handle'; }, /person\.name/);
refuse('person is an email address', (r) => { r.person.name = 'someone@example.org'; }, /email/);
refuse('person is one letter', (r) => { r.person.name = 'x'; }, /person/);
refuse('no engine version and no commit', (r) => { delete r.engine.commit; }, /version or a commit/);
refuse('version "unknown" with a commit', (r) => { r.engine.version = 'unknown'; }, /placeholder/);
refuse('version "latest"', (r) => { r.engine.version = 'latest'; }, /placeholder/);
refuse('version "main"', (r) => { r.engine.version = 'main'; }, /placeholder/);
refuse('commit is not a hash', (r) => { r.engine.commit = 'main'; }, /commit/);
refuse('engine name is neither Sneeze nor Artemis', (r) => { r.engine.name = 'Quest Browser'; }, /engine\.name/);
refuse('no date', (r) => { delete r.date; }, /date/);
refuse('date in the future', (r) => { r.date = '2026-10-25'; }, /future/);
refuse('date before Sneeze existed', (r) => { r.date = '2026-01-02'; }, /before Sneeze existed/);
refuse('date not a real day', (r) => { r.date = '2026-02-30'; }, /real calendar date/);
refuse('no OS', (r) => { delete r.os; }, /os/);
refuse('OS name a placeholder', (r) => { r.os.name = 'n/a'; }, /os\.name/);
refuse('OS version a placeholder', (r) => { r.os.version = 'FILL IN'; }, /os\.version/);
refuse('repository commit missing', (r) => { r.build.repo_commit = 'FILL IN git rev-parse HEAD of this repository'; }, /repo_commit|build/);
refuse('pre-flight not passed', (r) => { r.preflight.passed = false; }, /preflight\.passed/);
refuse('pre-flight absent', (r) => { delete r.preflight; }, /preflight/);
refuse('a different build (one tile hash differs)', (r) => { r.preflight.tile_sha256['parish-22005'] = '1'.repeat(64); }, /different build/);
refuse('a different build (one manifest hash differs)', (r) => { r.preflight.manifest_sha256.parishes = '1'.repeat(64); }, /different build/);
refuse('a different build (stamp differs)', (r) => { r.build.tiles_source_stamp = '1'.repeat(16); }, /different build/);
refuse('an unknown manifest', (r) => { r.manifests.push({ ...clone(r.manifests[0]), id: 'atlantis' }); }, /not a manifest in tiles\.json/);
refuse('an unknown tile', (r) => { r.manifests[0].tiles[0].tile = 'parish-99999'; }, /not a tile of this manifest/);
refuse('a tile of a different manifest', (r) => { r.manifests.find((m) => m.id === 'campus-oakland').tiles[0].tile = 'parish-22005'; }, /not a tile of this manifest/);
refuse('a tile reported twice', (r) => { const m = r.manifests.find((x) => x.id === 'parishes'); m.tiles.push(clone(m.tiles[1])); }, /reported twice/);
refuse('a manifest reported twice', (r) => { r.manifests.push(clone(r.manifests.find((x) => x.id === 'campus-oakland'))); }, /reported twice/);
refuse('an unknown field', (r) => { r.fields[0].field = 'manifest.Teleport'; }, /not a field in tiles\.json/);
refuse('a field reported twice', (r) => { r.fields.push(clone(r.fields.find((f) => f.verdict === 'observed'))); }, /reported twice/);
refuse('"observed" with no evidence', (r) => { r.fields.find((f) => f.verdict === 'observed').evidence = ''; }, /written evidence/);
refuse('"observed" with a one-word evidence', (r) => { r.fields.find((f) => f.verdict === 'observed').evidence = 'yes'; }, /written evidence/);
refuse('"observed" with no screenshot', (r) => { r.fields.find((f) => f.verdict === 'observed').screenshots = []; }, /screenshot hash/);
refuse('a field screenshot that was never declared', (r) => { r.fields.find((f) => f.verdict === 'observed').screenshots = [H3]; }, /not declared/);
refuse('a tile screenshot that was never declared', (r) => { r.manifests[0].tiles[0].screenshots = [H3]; }, /not declared/);
refuse('a screenshot hash that is not a sha256', (r) => { r.screenshots[0].sha256 = 'IMG_0042'; }, /sha256/);
refuse('the same screenshot declared twice', (r) => { r.screenshots[1].sha256 = H1; }, /declared twice/);
refuse('a verdict outside the vocabulary: "claimed"', (r) => { r.fields[0].verdict = 'claimed'; }, /not one of/);
refuse('a smuggled status field', (r) => { r.fields[0].status = 'claimed'; }, /not a field of this format/);
refuse('a smuggled top-level status', (r) => { r.status = 'observed in Sneeze 9'; }, /not a field of this format/);
refuse('an observation outside the vocabulary', (r) => { r.manifests[0].tiles[0].appears = 'yes'; }, /not one of/);
refuse('a run that observed nothing', (r) => { r.manifests.forEach((m) => { m.loaded = 'untested'; m.tiles.forEach((t) => { for (const k of ['appears', 'orientation', 'scale', 'smooth']) t[k] = 'untested'; if (t.child_position !== 'not_applicable') t.child_position = 'untested'; }); }); r.fields.forEach((f) => { f.verdict = 'untested'; }); }, /observed nothing/);
refuse('tile passes on a manifest reported not loaded', (r) => { const m = r.manifests.find((x) => x.id === 'wilds-delta'); m.tiles[0].appears = 'pass'; }, /not loaded/);
refuse('orientation passes on a tile that does not appear', (r) => { const m = r.manifests.find((x) => x.id === 'wilds-delta'); m.loaded = 'partial'; m.tiles[0].appears = 'fail'; m.tiles[0].orientation = 'pass'; }, /does not appear/);
refuse('observations given on a manifest reported untested', (r) => { const m = r.manifests.find((x) => x.id === 'wilds-forest'); m.tiles[0].appears = 'pass'; }, /untested/);
refuse('GeoPose "yes" on a manifest that did not load', (r) => { r.manifests.find((x) => x.id === 'wilds-delta').geopose_anchor_read = 'yes'; }, /geopose_anchor_read/);
refuse('an extra unknown key in a tile observation', (r) => { r.manifests[0].tiles[0].verified = true; }, /not a field of this format/);
{
  const rf = join(TMP, 'garbage.json'); writeFileSync(rf, '{ nope');
  const rp = join(TMP, 'garbage_runs.json');
  const r = py('ingest.py', [rf, '--runs', rp, '--today', TODAY]);
  ok('refused: a file that is not JSON', r.code === 1 && !existsSync(rp) && /REFUSED/.test(r.err));
  const t = py('ingest.py', [join(TMP, 'tpl.json'), '--runs', rp, '--today', TODAY]);
  ok('refused: the unfilled template as downloaded (every FILL IN is reported)', t.code === 1 && !existsSync(rp) && /\$\.date/.test(t.err) && /engine\.name/.test(t.err));
}
// each required key of the schema, walked: deleting it must be refused
{
  const paths = [];
  const walk = (sch, path) => {
    if (sch.type === 'object') { for (const k of sch.required || []) paths.push([...path, k]); for (const [k, v] of Object.entries(sch.properties || {})) walk(v, [...path, k]); }
    if (sch.type === 'array' && sch.items) walk(sch.items, [...path, 0]);
  };
  walk(schema, []);
  let refused = 0, tried = 0;
  for (const p of paths) {
    const r = goodRun();
    let o = r, okp = true;
    for (const k of p.slice(0, -1)) { o = o?.[k]; if (o === undefined) { okp = false; break; } }
    if (!okp || !(p[p.length - 1] in o)) continue;
    delete o[p[p.length - 1]];
    tried++;
    const x = ingest(r);
    if (x.code === 1 && x.runs === null) refused++; else console.log('   not refused without', p.join('.'));
  }
  ok(`deleting any one of the schema's ${tried} required keys is refused (all ${refused} of them)`, tried >= 30 && refused === tried);
}

// ---- prerequisites: the run says "observed" but its own tile observations do not support it
function keeps(name, mutate, field, why) {
  const r = goodRun();
  mutate(r);
  const x = ingest(r);
  const rec = x.runs?.runs?.[0];
  ok(`stays proposed: ${name}`, x.code === 0 && rec && stat(x.runs, field) === 'proposed' && new RegExp(why).test(rec.field_outcomes[x.runs.field_status.find((f) => f.field.startsWith(field)).field] || ''));
  return x;
}
const setField = (r, name, verdict) => Object.assign(r.fields.find((f) => f.field.startsWith(name)), { verdict, evidence: 'saw it with my own eyes on screen', screenshots: [H1] });
keeps('axes observed but one child out of place', (r) => { r.manifests.find((m) => m.id === 'parishes').tiles[5].child_position = 'fail'; }, 'world horizontal axes', 'kept: needs a loaded multi-tile');
keeps('axes observed on single-tile manifests only', (r) => { r.manifests.find((m) => m.id === 'parishes').loaded = 'partial'; }, 'world horizontal axes', 'kept: needs a loaded multi-tile');
keeps('axes observed but the first tile did not appear', (r) => { r.manifests.find((m) => m.id === 'parishes').tiles[0].appears = 'fail'; r.manifests.find((m) => m.id === 'parishes').tiles[0].orientation = 'untested'; r.manifests.find((m) => m.id === 'parishes').tiles[0].scale = 'untested'; r.manifests.find((m) => m.id === 'parishes').tiles[0].smooth = 'untested'; }, 'world horizontal axes', 'kept: needs a loaded multi-tile');
keeps('GeoPose consumed, but the run says the anchor was not read', (r) => { setField(r, 'GeoPose anchor consumed', 'observed'); r.manifests.find((m) => m.id === 'parishes').geopose_anchor_read = 'no'; }, 'GeoPose anchor consumed', 'geopose_anchor_read');
keeps('Data.Anchors observed but only a partly loaded manifest', (r) => { setField(r, 'manifest.Data.Anchors', 'observed'); r.manifests.find((m) => m.id === 'parishes').loaded = 'partial'; r.manifests.find((m) => m.id === 'campus-oakland').loaded = 'partial'; }, 'manifest.Data.Anchors', 'fully loaded');
keeps('frame budget observed but the largest tile is not smooth', (r) => { setField(r, 'a tile this size', 'observed'); r.manifests.find((m) => m.id === 'parishes').tiles.find((t) => t.tile === 'parish-22057').smooth = 'fail'; }, 'a tile this size', 'largest tile');
keeps('frame budget observed but the largest tile was never looked at', (r) => { setField(r, 'a tile this size', 'observed'); r.manifests.find((m) => m.id === 'parishes').tiles = r.manifests.find((m) => m.id === 'parishes').tiles.filter((t) => t.tile !== 'parish-22057'); }, 'a tile this size', 'largest tile');
keeps('scale observed but only campus-size tiles (under 10 km) were checked', (r) => { setField(r, 'camera / render scale', 'observed'); const p = r.manifests.find((m) => m.id === 'parishes'); p.tiles.forEach((t) => { t.scale = 'untested'; }); r.manifests.find((m) => m.id === 'campus-oakland').tiles[0].scale = 'pass'; }, 'camera / render scale', 'at least 10 km');
keeps('"attaching one manifest to another" can never be flipped by this kit', (r) => setField(r, 'attaching one manifest', 'observed'), 'attaching one manifest', 'cannot show it');
keeps('"signing" can never be flipped by this kit', (r) => setField(r, 'signing', 'observed'), 'signing', 'cannot show it');
keeps('a field looked for but not seen', (r) => { setField(r, 'GeoPose anchor consumed', 'not_observed'); }, 'GeoPose anchor consumed', 'not seen');
{
  ok('a field the registry marks documented is not in this table of proposed fields, so there is nothing to observe', !tiles.field_status.some((f) => f.field === 'node.Resource.sReference' && f.status === 'proposed'));
  const rr = goodRun(); rr.fields.push({ field: 'node.Resource.sReference', verdict: 'observed', evidence: 'the GLB showed up on screen', screenshots: [H1] });
  const x = ingest(rr);
  ok('a documented field reported "observed" is recorded as a run note but stays "documented" (nothing flipped)', x.code === 0 && stat(x.runs, 'node.Resource.sReference') === 'documented' && /already documented/.test(x.runs.runs[0].field_outcomes['node.Resource.sReference']));
}
{
  // the flips that ARE supported
  const r = goodRun();
  setField(r, 'manifest.Data.Anchors', 'observed'); setField(r, 'GeoPose anchor consumed', 'observed'); setField(r, 'camera / render scale', 'observed'); setField(r, 'a tile this size', 'observed');
  r.manifests.find((m) => m.id === 'parishes').geopose_anchor_read = 'yes';
  const x = ingest(r);
  const flipped = x.runs.field_status.filter((f) => f.status !== f.registry_status).map((f) => f.field);
  ok('with supporting observations, six fields flip; the two the kit can never show (child fabrics, signing) still do not', x.code === 0 && flipped.length === 6 && stat(x.runs, 'attaching one manifest') === 'proposed' && stat(x.runs, 'signing') === 'proposed');
}
{
  // a proposed field the kit has no rule for is never flipped
  const reg = clone(tiles); reg.field_status.push({ field: 'a future proposed thing', status: 'proposed', verified_ids: [] });
  const rp = join(TMP, 'reg_future.json'); writeFileSync(rp, JSON.stringify(reg));
  const r = goodRun(); r.fields.push({ field: 'a future proposed thing', verdict: 'observed', evidence: 'looked fine to me on screen', screenshots: [H1] });
  const x = ingest(r, { registry: rp });
  ok('a proposed field with no rule in the kit is kept proposed ("review by hand"), never flipped by default', x.code === 0 && stat(x.runs, 'a future proposed thing') === 'proposed' && /no automatic rule/.test(x.runs.runs[0].field_outcomes['a future proposed thing']));
}

// ---- contradicted, disputed, other build
{
  const r = goodRun(); r.fields.find((f) => f.field.startsWith('world horizontal')).verdict = 'contradicted'; r.fields.find((f) => f.field.startsWith('world horizontal')).evidence = 'north is clearly along minus Y, Orleans sat west';
  const x = ingest(r);
  ok('"contradicted" (with evidence) is recorded as such, not as proposed and never as observed', x.code === 0 && stat(x.runs, 'world horizontal axes') === 'contradicted in Sneeze commit abc1234def56');
  const rp = x.rp;
  const r2 = goodRun(); r2.person.name = 'Bo Second'; r2.engine = { name: 'Artemis', version: '1.2.3', installed_from: 'installer' };
  const y = ingest(r2, { runsFile: rp });
  ok('a second run that observes what the first contradicted makes the field "disputed", naming both', y.code === 0 && y.runs.run_count === 2 && /^disputed: observed in Artemis 1\.2\.3; contradicted in Sneeze commit abc1234def56$/.test(stat(y.runs, 'world horizontal axes')));
  ok('runs are ordered by date then id and --check still agrees', py('ingest.py', ['--check', '--runs', rp]).code === 0);
}
{
  const r = goodRun(); r.preflight.tile_sha256['parish-22005'] = '1'.repeat(64);
  const x = ingest(r, { extra: ['--allow-other-build'] });
  ok('--allow-other-build records a run of a different build but flips NOTHING and changes no manifest or tile status',
    x.code === 0 && x.runs.runs[0].build_match === false && x.runs.field_status.every((f) => f.status === f.registry_status) && Object.values(x.runs.runs[0].field_outcomes).length >= 2 && Object.values(x.runs.runs[0].field_outcomes).every((o) => /^kept: the run tested a different build/.test(o)) && x.runs.manifest_status.every((m) => m.status === tiles.manifests.find((q) => q.id === m.id).status) && x.runs.tile_status.every((t) => !/observed/.test(t.status)));
}
{
  const sd = join(TMP, 'shots'); mkdirSync(sd);
  writeFileSync(join(sd, 'a.png'), 'picture one'); writeFileSync(join(sd, 'b.png'), 'picture two');
  const r = goodRun(); r.screenshots = [{ sha256: sha('picture one'), caption: 'the first picture' }, { sha256: sha('picture two'), caption: 'the second picture' }];
  r.manifests.find((m) => m.id === 'parishes').screenshots = [sha('picture one')];
  r.fields.filter((f) => f.verdict === 'observed').forEach((f) => { f.screenshots = [sha('picture one')]; });
  r.manifests.forEach((m) => { m.tiles.forEach((t) => { t.screenshots = []; }); });
  ok('--screens: every declared hash matches a file in the folder -> recorded', ingest(r, { extra: ['--screens', sd] }).code === 0);
  r.screenshots[1].sha256 = sha('picture three');
  const x = ingest(r, { extra: ['--screens', sd] });
  ok('--screens: a declared hash with no file in the folder -> refused', x.code === 1 && /no file with sha256/.test(x.err) && x.runs === null);
}

// ---- the stored file cannot be edited into a claim
{
  const rp = good.rp;
  const doc = J(rp);
  const tamper = (fn, name, wantMsg) => { const d = clone(doc); fn(d); const p = join(TMP, `tamper_${++seq}.json`); writeFileSync(p, JSON.stringify(d)); const r = py('ingest.py', ['--check', '--runs', p]); ok(`--check fails if the stored file is hand-edited: ${name}`, r.code === 1 && new RegExp(wantMsg).test(r.out)); };
  tamper((d) => { d.field_status.find((f) => f.field.startsWith('GeoPose anchor consumed')).status = 'claimed'; }, 'a status set to "claimed"', 'differs');
  tamper((d) => { d.field_status.find((f) => f.field.startsWith('signing')).status = 'observed in Sneeze 1'; }, 'a status flipped by hand', 'differs');
  tamper((d) => { d.runs[0].field_outcomes['GeoPose anchor consumed by any Sneeze component'] = 'flipped'; d.runs[0].run.fields.find((f) => f.field.startsWith('GeoPose')).verdict = 'observed'; }, 'an outcome flipped by hand without the evidence', 'field outcomes differ|differs');
  tamper((d) => { d.runs[0].run.person.name = 'Someone Else'; }, 'the person changed after the fact', 'does not hash to its id');
  tamper((d) => { d.run_count = 0; }, 'the run count lowered', 'differs');
  tamper((d) => { d.runs = []; }, 'the runs removed but the statuses kept', 'differs');
  const rc = join(TMP, 'rc.json'); writeFileSync(rc, JSON.stringify(doc)); 
  const bad = clone(doc); bad.field_status.find((f) => f.field.startsWith('signing')).status = 'claimed'; writeFileSync(rc, JSON.stringify(bad));
  ok('--recompute rebuilds the tables from the runs and removes a hand edit', py('ingest.py', ['--recompute', '--runs', rc]).code === 0 && J(rc).field_status.find((f) => f.field.startsWith('signing')).status === 'proposed' && py('ingest.py', ['--check', '--runs', rc]).code === 0);
}

// =========================================================== the committed registry and the pages
const reg = J(RUNS);
ok('spatial/registry/sneeze_runs.json is exactly what its runs derive (--check)', py('ingest.py', ['--check']).code === 0);
ok('regenerating it from nothing is byte-identical (deterministic: rebuild_all can run --recompute)', (() => { const p = join(TMP, 'regen.json'); const r = py('ingest.py', ['--recompute', '--runs', p]); return reg.run_count > 0 || (r.code === 0 && readFileSync(p, 'utf8') === readFileSync(RUNS, 'utf8')); })());
ok('it lists every field, manifest and tile of tiles.json', reg.field_status.length === tiles.field_status.length && reg.manifest_status.length === 9 && reg.tile_status.length === 29);
ok('every status in the committed file is proposed, documented, "not loaded", or "observed ..." / "contradicted ..." / "disputed ..." with a run behind it; never "claimed"',
  !/claimed/i.test(readFileSync(RUNS, 'utf8')) && reg.field_status.every((f) => f.status === f.registry_status || (f.run_ids.length > 0 && /^(observed in|contradicted in|disputed:)/.test(f.status))));
if (reg.run_count === 0) {
  ok('ZERO runs are recorded: every proposed field is still "proposed", every manifest still says not loaded, every tile still says not loaded',
    reg.field_status.every((f) => f.status === f.registry_status) && reg.manifest_status.every((m) => /not loaded in Sneeze, Artemis/.test(m.status)) && reg.tile_status.every((t) => /not loaded in Sneeze, Artemis/.test(t.status)));
  ok('while the count is zero the checklist says nobody has done this, and the wiki page still says nothing was opened in Sneeze or Artemis',
    /Status today: nobody has done this/.test(text('CHECKLIST.md')) && /not loaded/.test(readFileSync(join(ROOT, 'wiki', 'Spatial-Fabric.md'), 'utf8')));
} else {
  ok('a run is recorded, so the checklist no longer says nobody has done this', !/Status today: nobody has done this/.test(text('CHECKLIST.md')));
  ok('a run is recorded, so the wiki page may not keep the sentence "No tile and no manifest here has been opened in Sneeze"', !/No tile and no manifest here has been opened in Sneeze/.test(readFileSync(join(ROOT, 'wiki', 'Spatial-Fabric.md'), 'utf8')));
}
ok('tiles.json itself is untouched by the kit: its manifests still say "proposed - not loaded", no run is smuggled into it', tiles.manifests.every((m) => /^proposed - not loaded in Sneeze/.test(m.status)) && !('sneeze_runs' in tiles));

// ---- the checklist's own claims, read against the registry
const ck = text('CHECKLIST.md');
ok('the checklist names all nine manifests', tiles.manifests.every((m) => ck.includes('`' + m.id + '`')));
ok('the checklist\'s numbers are the registry\'s: 29 tiles, 9 manifests, the largest tile and its size, the smallest manifest\'s size, the parishes total',
  /29 `\.glb` tiles and 9 manifests/.test(ck) && ck.includes(tiles.tiles.find((t) => t.bytes === tiles.budget.largest_tile_bytes).name) && ck.includes(`${Math.round(tiles.budget.largest_tile_bytes / 1000)} KB`)
  && ck.includes(`${Math.round(tiles.tiles.find((t) => t.id === 'campus-oakland').bytes / 1000)} KB`)
  && ck.includes(`about ${Math.round(tiles.tiles.filter((t) => t.world === 'parishes').reduce((a, t) => a + t.bytes, 0) / 1e6)} MB`));
{
  const w = (id) => { const b = tiles.tiles.find((t) => t.id === id).bbox_gltf_m; return b.max[0] - b.min[0]; };
  ok('the scale ratios the checklist offers hold: Plaquemines ~3x St. James, St. Bernard ~3x St. Charles (2.5 to 3.6)', w('parish-22075') / w('parish-22093') > 2.5 && w('parish-22075') / w('parish-22093') < 3.6 && w('parish-22087') / w('parish-22089') > 2.5 && w('parish-22087') / w('parish-22089') < 3.6);
}
ok('the checklist says region tiles are thin sheets, and the registry heights agree (every parish/county tile is under 10 m tall)',
  /thin sheets/.test(ck) && tiles.tiles.filter((t) => ['parishes', 'bayarea'].includes(t.world)).every((t) => t.bbox_gltf_m.max[1] - t.bbox_gltf_m.min[1] < 10));
ok('the checklist names the documented Y-up to Z-up conversion and the registry\'s verified fact for it', /Y-up to Z-up/.test(ck) && tiles.verified.some((v) => v.id === 'glb-axes' && /Z-up/.test(v.fact)));
ok('the checklist says the GeoPose anchor is not documented as read ("no" is the expected answer) and that unsigned manifests may stop working',
  /docs say nothing about it/.test(ck) && tiles.verified.some((v) => v.id === 'no-geopose-doc') && /may stop working/.test(ck) && tiles.verified.some((v) => v.id === 'unsigned-caveat'));
ok('the checklist cites the Sneeze docs\' own install step and the CDN module the manifests name', ck.includes('01-stool.md') && ck.includes(tiles.map_module_url));
{
  const PHRASE = { 'manifest.Data.Anchors': 'Data.Anchors sidecar', 'manifest.Data.Provenance': 'Data.Provenance sidecar', 'world horizontal axes': 'Horizontal axes are east/north', 'GeoPose anchor consumed': 'GeoPose anchor consumed',
    'attaching one manifest': 'Attaching one manifest to another', 'camera / render scale': 'Camera and render scale at 10-100 km', 'a tile this size': 'Largest tile inside the frame budget', 'signing': 'Signing' };
  const proposed = tiles.field_status.filter((f) => f.status === 'proposed').map((f) => f.field);
  ok('the checklist has a row for every proposed field in the registry (a new proposed field fails here until the checklist gets its row)', proposed.length === 8 && proposed.every((f) => { const k = Object.keys(PHRASE).find((p) => f.startsWith(p)); return k && ck.includes(PHRASE[k]); }));
}
ok('the checklist ends by saying what a pass does not establish', /does not establish/.test(ck) && /not that anything here is an OMBI or MSF standard/.test(ck));
ok('every command the checklist shows names a script that exists in the kit', [...ck.matchAll(/python3 spatial\/(sneeze_kit\/[a-z_]+\.py|build\.py)/g)].every((m) => existsSync(join(ROOT, 'spatial', m[1]))));
ok('the flags the checklist uses all exist in the scripts', ['--out', '--guide', '--preflight', '--log', '--map-wasm', '--dry-run', '--screens'].every((f) => ck.includes(f) && FILES.filter((x) => x.endsWith('.py')).some((x) => text(x).includes(`'${f}'`))));

// ---- optional: ONE headless Chromium run, proving the server to a page on another origin
if (process.argv.includes('--browser')) {
  const pw = process.env.PLAYWRIGHT_MODULE ? await import(process.env.PLAYWRIGHT_MODULE) : await import((await import('node:child_process')).execSync('npm root -g', { encoding: 'utf8' }).trim() + '/playwright/index.mjs');
  const chromium = (pw.default || pw).chromium;
  const s = await startServer([]);
  const other = http.createServer((q, r) => { r.writeHead(200, { 'Content-Type': 'text/html' }); r.end('<!doctype html><title>other origin</title>'); });
  await new Promise((r) => other.listen(0, '127.0.0.1', r));
  const b = await chromium.launch({ executablePath: process.env.CHROMIUM_PATH || undefined });
  try {
    const pg = await b.newPage();
    await pg.goto(`http://127.0.0.1:${other.address().port}/`);
    const base = `http://127.0.0.1:${s.port}/`;
    const got = await pg.evaluate(async ({ base, ref }) => {
      const m = await fetch(base + 'campus-oakland.json'); const doc = await m.json();
      const full = await fetch(base + ref); const buf = new Uint8Array(await full.arrayBuffer());
      const part = await fetch(base + ref, { headers: { Range: 'bytes=0-3' } }); const pb = new Uint8Array(await part.arrayBuffer());
      return { ct: m.headers.get('content-type'), name: doc.Container, gct: full.headers.get('content-type'), len: buf.length, magic: String.fromCharCode(...buf.slice(0, 4)), pstatus: part.status, pmagic: String.fromCharCode(...pb), cr: part.headers.get('content-range'), origin: location.origin };
    }, { base, ref: 'tiles/campus-oakland.glb' });
    const t = tiles.tiles.find((x) => x.id === 'campus-oakland');
    ok('Chromium, from a page on ANOTHER origin: manifest JSON and tile fetched through CORS with the right types and exact byte count', got.origin !== base.slice(0, -1) && got.ct === 'application/json' && got.name === 'smartcitix-world-campus-oakland' && got.gct === 'model/gltf-binary' && got.len === t.bytes && got.magic === 'glTF');
    ok('Chromium: a Range request across origins returns 206 with the glTF magic and Content-Range readable by the page', got.pstatus === 206 && got.pmagic === 'glTF' && got.cr === `bytes 0-3/${t.bytes}`);
  } finally { await b.close(); other.close(); await s.stop(); }
}

console.log(`\n${n} checks passed. This suite shows the kit works and refuses what it should; it does not show that Sneeze or Artemis loads any tile (nothing here runs either).`);
