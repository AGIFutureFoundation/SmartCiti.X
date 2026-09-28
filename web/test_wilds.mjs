/**
 * The wilds page, read as a file: structure, nav, controls, instancing,
 * honesty, the terrain core carried byte-for-byte, and the quest hooks.
 * The browser half (draw calls, frame time, page errors) is
 * web/eval_wilds.mjs; this half runs anywhere node does.
 *
 *   node web/test_wilds.mjs
 *   node web/test_wilds.mjs --root=/tmp/copy      (mutation runs)
 */
import { readFileSync, existsSync } from 'node:fs';
import { join, resolve, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';
import { spawnSync } from 'node:child_process';

const HERE = dirname(fileURLToPath(import.meta.url));
const hit = process.argv.slice(2).find((a) => a.startsWith('--root='));
const ROOT = resolve(hit ? hit.slice(7) : join(HERE, '..'));
let n = 0, bad = 0;
const ok = (m, c, evidence = []) => {
  if (c) { n++; console.log('  ok  ' + m); return; }
  bad++; console.log('FAIL  ' + m);
  for (const e of evidence.slice(0, 6)) console.log('      ' + e);
};
const canon = (v) => (v && typeof v === 'object' && !Array.isArray(v))
  ? Object.fromEntries(Object.keys(v).sort().map((k) => [k, canon(v[k])]))
  : (Array.isArray(v) ? v.map(canon) : v);
const same = (a, b) => JSON.stringify(canon(a)) === JSON.stringify(canon(b));
const read = (rel) => readFileSync(join(ROOT, rel), 'utf8');
const html = read('web/trade_craft_wilds.html');
const reg = JSON.parse(read('wilds/registry/wilds.json'));
const coreSrc = read('wilds/core.mjs');
const builder = read('web/build_wilds.py');
const halls = new Set(JSON.parse(read('pack/registry/halls.json')).halls.map((h) => h.slug));
const lessons = JSON.parse(read('lessons/registry/lessons.json')).lessons;
const main = (html.match(/<script type="module" id="wilds-main">([\s\S]*?)<\/script>/) || [, ''])[1];

/* ------------------------------------------------------------- build -- */
const chk = spawnSync('python3', [join(ROOT, 'web/build_wilds.py'), '--check'], { cwd: ROOT, encoding: 'utf8' });
ok('[build] the page is what web/build_wilds.py writes (not stale, not hand-edited)', chk.status === 0, [chk.stdout, chk.stderr]);

/* --------------------------------------------------------- structure -- */
ok('[page] exactly one <h1>', (html.match(/<h1[\s>]/g) || []).length === 1);
ok('[page] lang, viewport and title', /<html lang="en">/.test(html) && /name="viewport"/.test(html) && /<title>[^<]+<\/title>/.test(html));
const sitenav = read('web/sitenav.py');
const wired = sitenav.includes("'web/trade_craft_wilds.html'");
ok('[nav] the site nav is carried and marks this page current',
  /<nav class="sitenav" data-sitenav/.test(html) && /href="trade_craft_wilds\.html" aria-current="page"/.test(html));
ok('[nav] web/sitenav.py lists this page (so every other page links here)', wired);
ok('[page] the registry is embedded verbatim',
  (() => { const m = html.match(/<script type="application\/json" id="wilds-registry">([\s\S]*?)<\/script>/); return m && same(JSON.parse(m[1].replace(/<\\\//g, '</')), reg); })());
const B = '/* WILDS_CORE:BEGIN */', E = '/* WILDS_CORE:END */';
const core = coreSrc.slice(coreSrc.indexOf(B), coreSrc.indexOf(E) + E.length);
ok('[page] the terrain core is carried byte-for-byte from wilds/core.mjs', main.includes(core) && main.split(B).length === 2);
const switchIds = [...html.matchAll(/<div id="switch"[^>]*>([\s\S]*?)<\/div>/g)].flatMap((m) => [...m[1].matchAll(/data-world="([^"]+)"/g)].map((x) => x[1]));
ok('[page] the world switcher offers every registry world, in order', JSON.stringify(switchIds) === JSON.stringify(reg.worlds.map((w) => w.id)), switchIds);
ok('[page] intro figures are the registry counts',
  [['worlds', reg.counts.worlds], ['area', reg.counts.area_km2], ['sites', reg.counts.sites], ['halls', reg.counts.halls_linked], ['lessons', reg.counts.lessons_linked]]
    .every(([k, v]) => { const m = html.match(new RegExp(`<b data-fig="${k}">([0-9.]+)</b>`)); return m !== null && Number(m[1]) === v; }));

/* ---------------------------------------------------------- three.js -- */
const im = html.match(/<script type="importmap">([\s\S]*?)<\/script>/);
const imports = im ? JSON.parse(im[1]).imports : {};
ok('[three] the importmap points at the vendored three and addons, which exist',
  imports.three === './vendor/three.module.min.js' && existsSync(join(ROOT, 'web/vendor/three.module.min.js'))
  && existsSync(join(ROOT, 'web/vendor/addons/controls/OrbitControls.js')) && existsSync(join(ROOT, 'web/vendor/addons/utils/BufferGeometryUtils.js')));
ok('[three] no script or stylesheet is fetched from another origin', !/<(script|link)[^>]+(src|href)="https?:/.test(html));
ok('[draw calls] vegetation is instanced: one InstancedMesh per species, refilled in place',
  /new THREE\.InstancedMesh\(/.test(main) && /setMatrixAt\(/.test(main) && /for \(const \[k, g\] of Object\.entries\(SPECIES\)\)/.test(main));
ok('[draw calls] props, caches and species geometry are merged (mergeGeometries)', (main.match(/mergeGeometries\(/g) || []).length >= 3);
ok('[draw calls] terrain streams in chunks with LOD rings and skirts', /const RING_SEGS = \[/.test(main) && /SKIRT/.test(main) && /function updateChunks/.test(main));
ok('[view] distance fog and an overview camera', /new THREE\.Fog\(/.test(main) && /new OrbitControls\(/.test(main) && /function buildOverview/.test(main));
ok('[view] water where the world has it, and a minimap', /function buildWater/.test(main) && /id="minimap"/.test(html) && /function drawMinimap/.test(main));

/* ---------------------------------------------------------- controls -- */
const keysNeeded = ['KeyW', 'KeyA', 'KeyS', 'KeyD', 'ArrowUp', 'ArrowDown', 'ArrowLeft', 'ArrowRight', 'ShiftLeft', 'KeyO'];
ok('[controls] keyboard: WASD, arrows, Shift run, O overview', keysNeeded.every((k) => main.includes(k)), keysNeeded.filter((k) => !main.includes(k)));
ok('[controls] touch: an on-screen stick and pointer-drag look', /id="stick"/.test(html) && /stick\.addEventListener\('pointerdown'/.test(main) && /canvas\.addEventListener\('pointermove'/.test(main) && /touch-action:none/.test(html));
ok('[controls] the canvas is focusable and labelled', /<canvas id="view" tabindex="0" aria-label="[^"]+"/.test(html));

/* ------------------------------------------------------------- sites -- */
const siteMiss = [];
for (const w of reg.worlds) for (const s of w.sites) {
  const card = (html.match(new RegExp(`<article class="site" id="site-${s.id}"[\\s\\S]*?</article>`)) || [''])[0];
  if (!card) { siteMiss.push(`${s.id}: no card`); continue; }
  for (const h of s.halls) if (!card.includes(`href="trade_craft_3d.html?hall=${h.id}"`) || !halls.has(h.id)) siteMiss.push(`${s.id}: hall ${h.id}`);
  for (const l of s.lessons) if (!card.includes(`href="trade_craft_lessons.html#lesson-${l.id}"`) || !lessons[l.id]) siteMiss.push(`${s.id}: lesson ${l.id}`);
  if (!card.includes('SCHEMATIC')) siteMiss.push(`${s.id}: no SCHEMATIC label`);
}
ok('[sites] every site has a card linking each of its halls (3D hall) and lessons, labelled SCHEMATIC', siteMiss.length === 0, siteMiss);

/* ----------------------------------------------------------- honesty -- */
ok('[honesty] the footer says authored landscape, not a survey', /<footer data-honesty>Authored landscape, not a survey/.test(html));
ok('[honesty] play is said plainly once: never enters a completion record, never certifies',
  /never enter a completion record and never certify anything/.test(html));
ok('[honesty] every world card says inspiration only, not real elevation',
  reg.worlds.every((w) => new RegExp(`data-world-card="${w.id}"[\\s\\S]*?inspiration only; the terrain is AUTHORED, not real elevation`).test(html)));
ok('[honesty] the altitude readout is labelled authored', /\(authored height\)/.test(main));
ok('[rules] no model identifiers in the page or builder', !/\b(gpt-|claude-|opus|sonnet|haiku)\b/i.test(html + builder));
ok('[rules] fail closed: no ?? defaults in the page script, no .get(k, default) in the builders',
  !/\?\?/.test(main) && !/\.get\([^)]*,[^)]*\)/.test(builder + read('wilds/build.py')));

/* ------------------------------------------------------------ quests -- */
const qpath = join(ROOT, 'quests/registry/quests.json');
const wq = existsSync(qpath) ? JSON.parse(readFileSync(qpath, 'utf8')).quests.filter((q) => q.world.startsWith('wilds:')) : [];
if (wq.length === 0) {
  ok('[quests] no wilds quests are registered yet, and the page says the quest log is not wired (integration point)',
    /data-quests-pending/.test(html) && !/data-tc-(egg|quest)=/.test(html));
} else {
  const places = new Map(reg.worlds.map((w) => [w.id, new Set(['trailhead', ...w.sites.map((s) => s.id), ...w.caches.map((c) => c.id)])]));
  const miss = [];
  for (const q of wq) {
    const wid = q.world.split(':')[1];
    const attr = q.kind === 'treasure' || q.kind === 'egg' ? 'data-tc-egg' : 'data-tc-quest';
    if (!html.includes(`${attr}="${q.id}"`)) miss.push(`${q.id}: no ${attr} hook`);
    if (!places.has(wid) || !places.get(wid).has(q.place)) miss.push(`${q.id}: place ${q.place} not in ${wid}`);
  }
  ok('[quests] every wilds quest has its hook and its place resolves to a site, cache or trailhead of its world', miss.length === 0, miss);
  const qi = html.indexOf('<script', html.indexOf('id="wilds-main"') + 1);
  ok('[quests] the quest script comes after the page\'s own main script', html.indexOf('id="wilds-main"') > 0 && qi > html.indexOf('id="wilds-main"'));
  ok('[quests] a quest log is on the page', /<div data-tc-questlog><\/div>/.test(html));
}

/* -------------------------------------------------------------- eval -- */
const ev = read('web/eval_wilds.mjs');
const baseBlock = ev.slice(ev.indexOf('const BASE = {'), ev.indexOf('const CALL_HEADROOM'));
ok('[eval] web/eval_wilds.mjs declares a target for every world and all four views',
  reg.worlds.every((w) => new RegExp(`\\b${w.id}: \\{[\\s\\S]*?overview:[\\s\\S]*?trail:[\\s\\S]*?dense:[\\s\\S]*?summit:`).test(baseBlock)),
  reg.worlds.map((w) => w.id));

console.log(bad ? `wilds page: ${bad} FAILED, ${n} ok` : `wilds page: all ${n} checks ok`);
process.exit(bad ? 1 : 0);
