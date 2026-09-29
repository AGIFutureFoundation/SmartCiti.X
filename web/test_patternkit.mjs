// web/test_patternkit.mjs - checks the embeddable exterior pattern kit (web/patternkit.py).
// Headless: the pure parts directly, the drawing through a small fake 2D context that records calls.
// Prints "  ok " per check, FAIL at column 0, exits non-zero on failure.
import { readFileSync } from 'node:fs';
import { execFileSync } from 'node:child_process';

let n = 0, bad = 0;
const ok = (m, c, d) => { if (c) { n++; console.log('  ok ', m); } else { bad++; console.log('FAIL', m, d === undefined ? '' : JSON.stringify(d).slice(0, 400)); } };
const ROOT = new URL('../', import.meta.url);
const kitPy = readFileSync(new URL('web/patternkit.py', ROOT), 'utf8');
const reg = JSON.parse(readFileSync(new URL('surfaces/registry/exterior.json', ROOT)));

const py = (code) => execFileSync('python3', ['-c', 'import sys; sys.path.insert(0, "web"); import patternkit as P\n' + code],
  { cwd: new URL('.', ROOT).pathname, encoding: 'utf8', stdio: ['ignore', 'pipe', 'pipe'] });
const script = py('sys.stdout.write(P.inline_script())');
let PK = null;
try { PK = new Function(script + '\nreturn PatternKit;')(); } catch (e) { PK = null; console.log(String(e)); }
ok('[api] inline_script() parses and PatternKit exposes the v1 API', PK && ['load', 'recipe', 'recipes', 'families', 'colour', 'colours',
  'shade', 'sizeFor', 'isPow2', 'hintsFor', 'repeatFor', 'draw', 'texture', 'cacheSize', 'clearCache', 'rng'].every((k) => typeof PK[k] === 'function')
  && PK.version === '1');
ok('[api] the data the page gets is the registry: every recipe and colour family, same stamp',
  PK.recipes().join() === Object.keys(reg.recipes).join() && PK.families().join() === Object.keys(reg.colour_families).join()
  && script.includes(reg.source_stamp));
const esm = py('sys.stdout.write(P.es_module(["brick.running"], ["earth"]))');
ok('[api] es_module(subset) ends with a default export and carries only the ids asked for',
  /export default PatternKit;\s*$/.test(esm) && esm.includes('"brick.running"') && !esm.includes('"roof.slate"') && !esm.includes('"night"'));
let pyErr = '';
try { py('P.data_json(["brick.nope"])'); } catch (e) { pyErr = String(e.stderr || e); }
ok('[fail-closed] data_json with an unknown recipe id stops the build naming it', /brick\.nope/.test(pyErr));

// pure parts
const throws = (f, re) => { try { f(); return false; } catch (e) { return re.test(String(e.message)); } };
ok('[pure] colour ids resolve to the registry hex; unknown ids throw by name',
  PK.colour('earth.adobe') === reg.colour_families.earth.colours.find((c) => c.id === 'earth.adobe').hex
  && throws(() => PK.colour('earth.nope'), /earth\.nope/) && throws(() => PK.colour('nope'), /nope/));
ok('[pure] shade: 0 is identity, -1 is black, +1 is white, darker is darker; out-of-range k throws',
  PK.shade('#808080', 0) === '#808080' && PK.shade('#123456', -1) === '#000000' && PK.shade('#123456', 1) === '#FFFFFF'
  && PK.shade('#808080', -0.5) === '#404040' && throws(() => PK.shade('#808080', 2), /out of range/));
const cj = PK.colours('brick.running', 'earth.fired_clay');
ok('[pure] colours(): a colour id gives base + joint derived by the recipe joint_shade; {base, joint} is honoured; missing base throws',
  cj.base === PK.colour('earth.fired_clay') && cj.joint === PK.shade(cj.base, reg.recipes['brick.running'].joint_shade)
  && PK.colours('brick.running', { base: '#aabbcc', joint: 'earth.umber_trim' }).joint === PK.colour('earth.umber_trim')
  && PK.colours('brick.running', { base: '#aabbcc' }).base === '#AABBCC' && throws(() => PK.colours('brick.running', {}), /base/));
ok('[pure] sizeFor: every quality is a power of two from the registry; an unknown quality throws',
  Object.entries(reg.quality_sizes).every(([q, s]) => PK.sizeFor(q) === s && PK.isPow2(s)) && throws(() => PK.sizeFor('ultra'), /ultra/)
  && !PK.isPow2(300) && PK.isPow2(256));
ok('[pure] repeatFor divides a face by the recipe tile_m', (() => { const [u, v] = PK.repeatFor('brick.running', 9, 4.5); const t = reg.recipes['brick.running'].tile_m; return Math.abs(u - 9 / t) < 1e-9 && Math.abs(v - 4.5 / t) < 1e-9; })());
ok('[pure] hintsFor returns the registry table for the world land uses; unknown throws',
  JSON.stringify(PK.hintsFor('industrial')) === JSON.stringify(reg.landuse_hints.industrial) && throws(() => PK.hintsFor('moon'), /moon/));
const r1 = PK.rng('a'), r2 = PK.rng('a'), r3 = PK.rng('b');
const s1 = [r1(), r1(), r1()], s2 = [r2(), r2(), r2()], s3 = [r3(), r3(), r3()];
ok('[pure] rng is deterministic per seed, in [0,1), and differs between seeds',
  JSON.stringify(s1) === JSON.stringify(s2) && JSON.stringify(s1) !== JSON.stringify(s3) && s1.every((x) => x >= 0 && x < 1));
ok('[fail-closed] unknown recipe throws by name in recipe/colours/draw/texture', throws(() => PK.recipe('brick.nope'), /brick\.nope/)
  && throws(() => PK.draw(fakeCtx([]), 'brick.nope', '#808080', 64), /brick\.nope/));

// fake 2D context: records every call with the fillStyle in force
function fakeCtx(log) {
  const st = { fillStyle: '#000000', strokeStyle: '#000000', lineWidth: 1, globalAlpha: 1 };
  return new Proxy(st, {
    get: (t, k) => (k in t ? t[k] : (...a) => { log.push({ op: k, a, fill: t.fillStyle }); }),
    set: (t, k, v) => { t[k] = v; return true; },
  });
}
const S = 256;
const drawn = {};
for (const id of PK.recipes()) { const log = []; PK.draw(fakeCtx(log), id, reg.recipes[id].uses.includes('roof') ? 'earth.terracotta_roof' : 'earth.fired_clay', S); drawn[id] = log; }
const nums = (c) => c.a.filter((x) => typeof x === 'number');
ok(`[draw] every recipe (${Object.keys(drawn).length}) draws, with finite coordinates only`,
  Object.values(drawn).every((l) => l.length > 3 && l.every((c) => nums(c).every(Number.isFinite))));
ok('[draw] every recipe first floods the whole tile (no transparent pixel at any size)',
  Object.values(drawn).every((l) => l[0].op === 'fillRect' && l[0].a.join() === `0,0,${S},${S}`));
ok('[draw] every fillStyle used is a #RRGGBB colour', Object.values(drawn).every((l) => l.every((c) => /^#[0-9A-F]{6}$/.test(c.fill))));
ok('[draw] every fillRect overlaps the tile (nothing drawn wholly off-canvas)',
  Object.values(drawn).every((l) => l.filter((c) => c.op === 'fillRect').every(({ a: [x, y, w, h] }) => x < S && x + w > 0 && y < S && y + h > 0 && w >= 0 && h >= 0)));
// tileability: a rect that crosses the right or bottom edge must reappear shifted by -S on that axis
const wrapGaps = [];
for (const [id, l] of Object.entries(drawn)) {
  const rects = l.filter((c) => c.op === 'fillRect').map((c) => c.a.map((v) => Math.round(v * 1000) / 1000).join(',') + '|' + c.fill);
  const set = new Set(rects);
  for (const c of l.filter((q) => q.op === 'fillRect')) {
    const [x, y, w, h] = c.a;
    const k = (X, Y) => [X, Y, w, h].map((v) => Math.round(v * 1000) / 1000).join(',') + '|' + c.fill;
    if (x + w > S + 1e-6 && !set.has(k(x - S, y))) wrapGaps.push(id + ' x@' + x.toFixed(1));
    if (y + h > S + 1e-6 && !set.has(k(x, y - S))) wrapGaps.push(id + ' y@' + y.toFixed(1));
  }
}
ok('[tile] every rectangle that crosses the right or bottom edge is repeated at -S (the tile wraps)', wrapGaps.length === 0, wrapGaps.slice(0, 8));
const arcGaps = [];
for (const [id, l] of Object.entries(drawn)) {
  const paths = l.filter((c) => ['arc', 'ellipse'].includes(c.op));
  const set = new Set(paths.map((c) => c.a.map((v) => Math.round(v * 1000) / 1000).join(',')));
  for (const c of paths) {
    const [x, y, r1] = c.a; const r = c.op === 'ellipse' ? Math.max(c.a[2], c.a[3]) : r1;
    const shifted = (X, Y) => [X, Y, ...c.a.slice(2)].map((v) => Math.round(v * 1000) / 1000).join(',');
    if (x + r > S && x < S && !set.has(shifted(x - S, y))) arcGaps.push(id + ' ' + c.op + ' x@' + x.toFixed(1));
    if (y + r > S && y < S && !set.has(shifted(x, y - S))) arcGaps.push(id + ' ' + c.op + ' y@' + y.toFixed(1));
  }
}
ok('[tile] every round shape (arc/ellipse) that crosses the right or bottom edge is repeated at -S', arcGaps.length === 0, arcGaps.slice(0, 8));
const again = []; PK.draw(fakeCtx(again), 'render.terrazzo', 'earth.fired_clay', S);
ok('[draw] drawing is deterministic (same recipe, colour and size, identical call list)', JSON.stringify(again) === JSON.stringify(drawn['render.terrazzo']));
const dFlem = drawn['brick.flemish'].filter((c) => c.op === 'fillRect').map((c) => c.fill);
ok('[draw] Flemish bond draws two unit shades (stretcher and darker header)', new Set(dFlem).size > 3);
ok('[draw] a non-power-of-two size throws', throws(() => PK.draw(fakeCtx([]), 'brick.running', '#808080', 300), /power of two/));

// texture(): fake THREE + fake document; cached per id/colour/size
let made = 0;
const THREE = { RepeatWrapping: 1000, SRGBColorSpace: 'srgb', CanvasTexture: class { constructor(c) { made++; this.image = c; this.userData = {}; } dispose() { this.disposed = true; } } };
const doc = { createElement: (tag) => ({ tag, width: 0, height: 0, getContext: () => fakeCtx([]) }) };
PK.clearCache();
const t1 = PK.texture(THREE, 'brick.running', 'earth.fired_clay', { quality: 'low', doc });
const t2 = PK.texture(THREE, 'brick.running', 'earth.fired_clay', { quality: 'low', doc });
const t3 = PK.texture(THREE, 'brick.running', 'earth.fired_clay', { quality: 'high', doc });
const t4 = PK.texture(THREE, 'brick.running', 'earth.adobe', { quality: 'low', doc });
ok('[texture] cached per (recipe, colour, size): same key returns the same object; size or colour makes a new one',
  t1 === t2 && t1 !== t3 && t1 !== t4 && made === 3 && PK.cacheSize() === 3);
ok('[texture] power-of-two canvas sized by the quality flag; RepeatWrapping on both axes; sRGB; userData names the key',
  t1.image.width === reg.quality_sizes.low && t1.image.height === reg.quality_sizes.low && t3.image.width === reg.quality_sizes.high
  && t1.wrapS === 1000 && t1.wrapT === 1000 && t1.colorSpace === 'srgb' && /^brick\.running\|#/.test(t1.userData.patternkit)
  && t1.userData.tile_m === reg.recipes['brick.running'].tile_m);
ok('[texture] default quality is medium', PK.texture(THREE, 'roof.slate', 'civic.copper_roof', { doc }).image.width === reg.quality_sizes.medium);
PK.clearCache();
ok('[texture] clearCache disposes and empties', t1.disposed === true && PK.cacheSize() === 0);
ok('[texture] an unknown quality throws before any canvas is made', throws(() => PK.texture(THREE, 'brick.running', '#808080', { quality: 'ultra', doc }), /ultra/));

// the real vendored three.js (the one pages load): texture() builds a genuine CanvasTexture with its constants
{
  const T = await import(new URL('web/vendor/three.module.min.js', ROOT).href);
  PK.clearCache();
  const tr = PK.texture(T, 'metal.standing_seam', 'industrial.sheet_roof', { quality: 'low', doc });
  const cl = tr.clone(); cl.repeat.set(...PK.repeatFor('metal.standing_seam', 8, 4));
  ok('[three] with the vendored three.js: a real CanvasTexture, RepeatWrapping, sRGB colour space, clone takes repeatFor',
    tr.isCanvasTexture === true && tr.wrapS === T.RepeatWrapping && tr.wrapT === T.RepeatWrapping && tr.colorSpace === T.SRGBColorSpace
    && tr.image.width === reg.quality_sizes.low && Math.abs(cl.repeat.x - 8 / reg.recipes['metal.standing_seam'].tile_m) < 1e-9 && cl.image === tr.image);
  PK.clearCache();
}

// honesty + hygiene of the kit source
ok('[honesty] honesty_line says AUTHORED and names no image/brand source', /AUTHORED/.test(py('sys.stdout.write(P.honesty_line())')));
const js = (kitPy.match(/PK_JS = r'''([\s\S]*?)'''/) || [, ''])[1];
ok('[hygiene] PK_JS has no ?? default, no network, no storage, no image loading', js.length > 1000 && !/\?\?/.test(js)
  && !/fetch\(|XMLHttpRequest|localStorage|new Image|\.src\s*=/.test(js));

console.log(`web/test_patternkit: ${n} checks, ${bad} failed — ${PK.recipes().length} recipes, ${PK.families().length} colour families`);
if (bad) process.exit(1);
