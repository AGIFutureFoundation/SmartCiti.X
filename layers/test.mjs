#!/usr/bin/env node
/* layers/test.mjs - the parish layers registry and web/pathkit.py, held to LAYERS_CONTRACT.
   Prints "  ok " per check, FAIL at column 0, exits non-zero on failure. */
import { readFileSync, existsSync } from 'node:fs';
import { createHash } from 'node:crypto';
import { execFileSync } from 'node:child_process';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const HERE = dirname(fileURLToPath(import.meta.url));
const ROOT = join(HERE, '..');
let fails = 0;
function ok(name, cond, detail) {
  if (cond) { console.log('  ok ' + name); return; }
  fails++; console.log('FAIL ' + name);
  for (const d of [].concat(detail || []).slice(0, 8)) console.log('     ' + d);
}
const read = (p) => readFileSync(join(ROOT, p), 'utf8');
const json = (p) => JSON.parse(read(p));
const reg = json('layers/registry/layers.json');
const sims = json('sims/registry/sims.json').sims;
const tasks = json('tasks/registry/tasks.json').tasks;
const taskById = new Map(tasks.map((t) => [t.id, t]));
const lreg = json('lessons/registry/lessons.json');
const L = lreg.lessons;
const layerOf = {}; for (const [d, ids] of Object.entries(lreg.ladder.layers)) for (const i of ids) layerOf[i] = +d;
const keyOrder = Object.keys(L);
const courseKey = (i) => [layerOf[i], keyOrder.indexOf(i)];
const schools = json('schools/registry/schools.json');
const hallName = Object.fromEntries(json('pack/registry/halls.json').halls.map((h) => [h.slug, h.name]));
const quests = json('quests/registry/quests.json');
const qById = new Map(quests.quests.map((q) => [q.id, q]));
const psrcPath = 'parishes/registry/parishes.json';
const preg = json(psrcPath);
const psrc = preg.selection.selected.map((f) => preg.parishes[f]);
const P = reg.parishes;
const ALL = P.flatMap((p) => p.stations.map((s) => ({ ...s, fips: p.fips })));
const LAYERS = ['trade-sim', 'task', 'lesson', 'k12-unit'];

// ---- counts
const byLayer = Object.fromEntries(LAYERS.map((k) => [k, ALL.filter((s) => s.layer === k).length]));
ok(`counts are computed: ${reg.counts.parishes} parishes, ${reg.counts.stations} stations, ${reg.counts.launchable} launchable`,
  reg.counts.parishes === P.length && P.length === psrc.length && reg.counts.stations === ALL.length
  && LAYERS.every((k) => reg.counts.by_layer[k] === byLayer[k])
  && reg.counts.launchable === ALL.filter((s) => s.launch.href).length,
  [JSON.stringify(reg.counts), JSON.stringify(byLayer), `parish source ${psrcPath}: ${psrc.length}`]);
ok('every parish of the parish source is here, by fips and name, with stations on all four layers',
  psrc.every((q) => P.some((p) => p.fips === q.fips && p.name === q.full_name))
  && P.every((p) => LAYERS.every((k) => p.stations.some((s) => s.layer === k))),
  P.map((p) => `${p.fips}: ${LAYERS.filter((k) => !p.stations.some((s) => s.layer === k))}`));
ok(`station ids are unique, kebab, st-<fips>-...; treasure is treasure-station-<id> (${ALL.length})`,
  new Set(ALL.map((s) => s.id)).size === ALL.length
  && ALL.every((s) => /^st-\d{5}-[a-z0-9]+(-[a-z0-9]+)*$/.test(s.id) && s.id.startsWith(`st-${s.fips}-`) && s.treasure === `treasure-station-${s.id}`));

// ---- every station points to a real entry, title read from it
const unitAt = (src) => { const m = /^schools\/registry\/schools\.json#units\[(\d+)\]$/.exec(src); return m ? schools.units[+m[1]] : null; };
const badRef = [];
for (const s of ALL) {
  const { registry: r, id, source } = s.ref;
  let title = null;
  if (s.layer === 'trade-sim' && r === 'sims/registry/sims.json' && id in sims && source === `${r}#sims.${id}`) title = sims[id].name;
  else if (s.layer === 'task' && r === 'tasks/registry/tasks.json' && taskById.has(id) && source === `${r}#tasks[${tasks.indexOf(taskById.get(id))}]`) title = taskById.get(id).title;
  else if (s.layer === 'lesson' && r === 'lessons/registry/lessons.json' && id in L && source === `${r}#lessons.${id}`) title = L[id].title;
  else if (s.layer === 'k12-unit' && r === 'schools/registry/schools.json' && unitAt(source) && unitAt(source).hall === id) title = `${hallName[id]}: flipped unit`;
  if (title === null || title !== s.title) badRef.push(`${s.id}: ${s.layer} ${r}#${id} (${source}) title ${JSON.stringify(s.title)} vs ${JSON.stringify(title)}`);
  for (const l of s.suggests) if (!(l in L)) badRef.push(`${s.id}: suggests unknown lesson ${l}`);
}
ok('every station points to a real entry (sims, tasks, lessons, schools units) and its title is read from it', badRef.length === 0, badRef);
ok('the K-12 layer is named "Cognition.X K-12", says its content is the schools/ pack, and districts stay PROPOSED',
  reg.layers['k12-unit'].label === 'Cognition.X K-12' && reg.layers['k12-unit'].content_from.includes('schools/')
  && reg.honesty.k12.includes('schools/') && /PROPOSED/.test(reg.honesty.k12) && reg.k12_districts === schools.honesty.districts
  && /proposed partner/i.test(reg.k12_districts));
ok('lessons stay "unverified general practice"; stations, paths and rings are play and never a completion record',
  reg.honesty.lessons.includes('unverified general practice') && lreg.honesty.content.startsWith('unverified general practice')
  && /never enter a completion record/.test(reg.honesty.play) && /AUTHORED/.test(reg.honesty.placement));

// ---- hrefs resolve, and only where the target page reads the param
const html = (p) => (existsSync(join(ROOT, p)) ? read(p) : null);
const pageLessons = html('web/trade_craft_lessons.html'); const pageSchools = html('web/trade_craft_schools.html');
const badHref = [];
for (const s of ALL) {
  const l = s.launch;
  if (!l.href) { if (!l.why) badHref.push(`${s.id}: no href and no why`); continue; }
  const [path, rest] = l.href.split(/(?=[?#])/);
  if (!existsSync(join(ROOT, path))) { badHref.push(`${s.id}: ${path} does not exist`); continue; }
  if (path === 'web/trade_craft_3d.html') {
    const q = new URLSearchParams(rest.slice(1));
    const keys = [...q.keys()];
    const sim = sims[q.get('sim')];
    if (JSON.stringify(keys) !== JSON.stringify(l.param)) badHref.push(`${s.id}: params ${keys} vs declared ${l.param}`);
    if (!sim || !sim.halls.includes(q.get('hall')) && !(taskById.has(s.ref.id) && taskById.get(s.ref.id).launch.href === l.href)) badHref.push(`${s.id}: hall/sim do not resolve (${rest})`);
    if (q.has('scenario') && !(sim && sim.scenarios.some((x) => x.id === q.get('scenario')))) badHref.push(`${s.id}: scenario ${q.get('scenario')} is not the seat's`);
    if (!read('web/build_3d.py').includes("params.get('sim')")) badHref.push('web/build_3d.py no longer reads ?sim');
  } else if (path === 'web/trade_craft_lessons.html') {
    const id = rest.slice(1);
    if (!(id.startsWith('lesson-') && pageLessons.includes(`id="${id}"`) && id.slice(7) === s.ref.id) || l.param[0] !== '#lesson-') badHref.push(`${s.id}: ${rest} is not an anchor on the lessons page`);
    if (!read('web/build_lessons.py').includes("id.indexOf('lesson-') === 0 ? document.getElementById(id)")) badHref.push('build_lessons no longer reads #lesson-');
  } else if (path === 'web/trade_craft_schools.html') {
    const m = /^#band-(.+)$/.exec(rest);
    const sec = m && new RegExp(`id="band-${m[1]}"([\\s\\S]*?)(?:id="band-|$)`).exec(pageSchools);
    if (!sec || !sec[1].includes(`#course-${s.ref.id}"`)) badHref.push(`${s.id}: ${rest} section does not list unit ${s.ref.id}`);
  } else if (!(taskById.has(s.ref.id) && taskById.get(s.ref.id).launch.href === l.href)) {
    badHref.push(`${s.id}: ${l.href} is neither a 3D/lessons/schools link nor the task's own verified link`);
  }
  if (s.layer === 'task' && taskById.get(s.ref.id).launch.href !== l.href) badHref.push(`${s.id}: task href differs from tasks.json`);
}
ok(`every launch href resolves to a page that reads its param (${ALL.filter((s) => s.launch.href).length} links)`, badHref.length === 0, badHref);

// ---- paths ordered and ungated
const badPath = [];
for (const p of P) {
  const ids = p.paths.map((x) => x.id);
  if (JSON.stringify(ids) !== '["trade","k12","explorer"]') badPath.push(`${p.fips}: paths ${ids}`);
  if (!p.paths.every((x) => x.gated === false)) badPath.push(`${p.fips}: a path is gated`);
  const st = new Map(p.stations.map((s) => [s.id, s]));
  const [trade, k12, exp] = p.paths;
  const onPath = [...trade.steps, ...k12.steps];
  if (onPath.length !== p.stations.length || new Set(onPath).size !== onPath.length || !onPath.every((i) => st.has(i))) badPath.push(`${p.fips}: stations and path steps do not match one-to-one`);
  if (!trade.steps.every((i) => st.has(i) && ['trade-sim', 'task'].includes(st.get(i).layer))) badPath.push(`${p.fips}: trade path holds a non-trade station`);
  if (!k12.steps.every((i) => st.has(i) && ['k12-unit', 'lesson'].includes(st.get(i).layer))) badPath.push(`${p.fips}: K-12 path holds a non-K-12 station`);
  let lastSim = null;
  for (const i of trade.steps) {
    const s = st.get(i); if (!s) continue;
    if (s.layer === 'trade-sim') { if (lastSim !== null && s.ref.id < lastSim) badPath.push(`${p.fips}: seats out of order at ${i}`); lastSim = s.ref.id; }
    else if (taskById.get(s.ref.id).seat !== lastSim) badPath.push(`${p.fips}: task ${i} does not follow its seat`);
  }
  const ks = k12.steps.map((i) => st.get(i)).filter(Boolean);
  const firstLesson = ks.findIndex((s) => s.layer === 'lesson');
  if (firstLesson >= 0 && ks.slice(firstLesson).some((s) => s.layer !== 'lesson')) badPath.push(`${p.fips}: K-12 path mixes units after lessons`);
  const ux = ks.filter((s) => s.layer === 'k12-unit').map((s) => +/\[(\d+)\]$/.exec(s.ref.source)[1]);
  if (ux.some((v, j) => j && v < ux[j - 1])) badPath.push(`${p.fips}: units out of schools order`);
  const lx = ks.filter((s) => s.layer === 'lesson').map((s) => courseKey(s.ref.id));
  if (lx.some((v, j) => j && (v[0] < lx[j - 1][0] || (v[0] === lx[j - 1][0] && v[1] < lx[j - 1][1])))) badPath.push(`${p.fips}: lessons out of ladder order`);
  if (!exp.steps.every((q) => qById.has(q) && qById.get(q).world === `parish:${p.fips}`)) badPath.push(`${p.fips}: explorer step not a quest of this parish`);
  for (const s of p.stations) if ('requires' in s || 'locked' in s || 'gate' in s) badPath.push(`${s.id}: carries a gate field`);
}
ok('three paths per parish (Trade, K-12, Explorer) in order, never gated; seats then their tasks; units then lessons in ladder order', badPath.length === 0, badPath);

// ---- stations inside land
function inRing(x, y, r) { let c = false; for (let i = 0, j = r.length - 1; i < r.length; j = i++) { const [xi, yi] = r[i], [xj, yj] = r[j]; if ((yi > y) !== (yj > y) && x < (xj - xi) * (y - yi) / (yj - yi) + xi) c = !c; } return c; }
const polysOf = (g) => g.polygons;
const outside = [];
for (const s of ALL) {
  const src = psrc.find((q) => q.fips === s.fips);
  const inLand = polysOf(src.outline).some((poly) => inRing(s.at.lon, s.at.lat, poly[0]) && !poly.slice(1).some((h) => inRing(s.at.lon, s.at.lat, h)));
  if (!inLand || s.provenance !== 'AUTHORED') outside.push(`${s.id} at ${s.at.lon},${s.at.lat}`);
}
ok(`every station stands inside its parish's land outline, AUTHORED (${ALL.length})`, outside.length === 0, outside);
const R = preg.frames.R_m; const W0 = preg.frames.world.origin;
const ltp = (lng, lat, o) => [R * Math.cos(o.lat * Math.PI / 180) * (lng - o.lng) * Math.PI / 180, R * (lat - o.lat) * Math.PI / 180];
const badFrame = [];
for (const s of ALL) {
  const src = psrc.find((q) => q.fips === s.fips);
  for (const [k, o] of [['world_m', W0], ['local_m', src.frame.origin]]) {
    const [e, n] = ltp(s.at.lon, s.at.lat, o);
    if (!Array.isArray(s[k]) || Math.abs(s[k][0] - e) > 0.02 || Math.abs(s[k][1] - n) > 0.02) badFrame.push(`${s.id} ${k} ${s[k]} vs ${e.toFixed(2)},${n.toFixed(2)}`);
  }
  if (s.near !== null && !P.find((p) => p.fips === s.fips).landmarks.some((l) => l.id === s.near)) badFrame.push(`${s.id}: near ${s.near} is not a landmark of ${s.fips}`);
}
ok('world_m and local_m follow the parishes/ ltp formula (<= 2 cm); "near" names a landmark of the parish', badFrame.length === 0, badFrame);
const lmMiss = P.filter((p) => { const src = psrc.find((q) => q.fips === p.fips); return p.landmarks.length !== src.landmarks.length || src.landmarks.length && !p.stations.some((s) => s.near); }).map((p) => p.fips);
ok('every parish landmark is carried, and a parish with landmarks has stations standing near them', lmMiss.length === 0, lmMiss);
const pos = new Set(ALL.map((s) => `${s.fips}:${s.at.lon},${s.at.lat}`));
ok('no two stations share a spot', pos.size === ALL.length);

// ---- quests keep the evidence rule
const pq = quests.quests.filter((q) => q.world === 'parishes' || q.world.startsWith('parish:'));
const badQ = [];
for (const s of ALL) { const q = qById.get(s.treasure); if (!q || q.kind !== 'treasure' || q.world !== `parish:${s.fips}` || q.place !== s.id || q.requires.lessons.length || q.requires.halls.length || q.requires.quests.length) badQ.push(`${s.treasure}`); }
for (const q of pq) if (q.provenance !== 'AUTHORED' || q.requires.lessons.length || q.requires.halls.length) badQ.push(`${q.id}: gated on lessons/halls or not AUTHORED`);
ok(`every station has an ungated play treasure; parish quests (${pq.length}) gate on nothing but other play`, badQ.length === 0, badQ);
ok('the quest registry keeps its evidence rule', /never enter a completion record/.test(quests.honesty) && /play/.test(quests.honesty));

// ---- stamps current
const badStamp = Object.entries(reg.sources).filter(([p, h]) => createHash('sha256').update(readFileSync(join(ROOT, p))).digest('hex').slice(0, 16) !== h).map(([p]) => p);
const stampOf = createHash('sha256').update(Object.entries(reg.sources).map(([k, v]) => `${k}:${v}\n`).join('')).digest('hex').slice(0, 16);
ok(`source stamp ${reg.source_stamp} is current over ${Object.keys(reg.sources).length} sources`, badStamp.length === 0 && stampOf === reg.source_stamp, badStamp);
let checkOut = '';
try { checkOut = execFileSync('python3', ['layers/build.py', '--check'], { cwd: ROOT, encoding: 'utf8', stdio: ['ignore', 'pipe', 'pipe'] }); } catch (e) { checkOut = String(e.stdout) + String(e.stderr); }
ok('python3 layers/build.py --check: registry is current', /is current/.test(checkOut), checkOut.trim());
const src = read('layers/build.py');
ok('the builder fails closed (no .get defaults, no ?? on registry data) and reuses tasks/build.py PARAM_READS',
  !/\.get\(/.test(src.replace(/q\.get|params\.get/g, '')) && !src.includes('??') && src.includes('mod.PARAM_READS'));

// ---- web/pathkit.py
let kit = null;
try {
  kit = JSON.parse(execFileSync('python3', ['-c', 'import json,sys;sys.path.insert(0,"web");import pathkit as k;d=k.path_data(sys.argv[1]);print(json.dumps({"css":k.PATH_CSS,"js":k.PATH_JS,"n":len(d["stations"]),"paths":[p["id"] for p in d["paths"]],"steps":len(d["steps"])}))', P[0].fips], { cwd: ROOT, encoding: 'utf8' }));
} catch (e) { kit = null; }
ok('pathkit.path_data(fips) loads a parish with its stations and three paths', kit && kit.n === P[0].stations.length && kit.paths.join() === 'trade,k12,explorer' && kit.steps === P[0].paths[2].steps.length);
let unknownFails = false;
try { execFileSync('python3', ['-c', 'import sys;sys.path.insert(0,"web");import pathkit;pathkit.path_data("00000")'], { cwd: ROOT, stdio: 'pipe' }); } catch (e) { unknownFails = /holds no parish/.test(String(e.stderr)); }
ok('pathkit.path_data fails by name on an unknown parish', unknownFails);
ok('PATH_CSS colours only through theme tokens (no hex, rgb or named colours)',
  kit && !/#[0-9a-f]{3,8}\b|rgba?\(|hsla?\(|:\s*(white|black|red|blue|green)\b/i.test(kit.css) && /var\(--mark\)/.test(kit.css) && /var\(--panel\)/.test(kit.css));
ok('PATH_JS: accessible chooser (radiogroup, aria-checked, arrow keys, Escape closes, focus returns)',
  kit && ['role="radiogroup"', 'role="radio"', 'aria-checked', 'ArrowRight', "e.key === 'Escape'", "'[data-pk-open=\"' + S.opener", 'aria-live'].every((t) => kit.js.includes(t)));
ok('PATH_JS: rings come from local play state only ("tc-quests", read-only; never written here), path choice under "tc-path"',
  kit && kit.js.includes("QSTORE = 'tc-quests'") && kit.js.includes('getItem(QSTORE)') && !/setItem\(QSTORE/.test(kit.js)
  && kit.js.includes('setItem(PSTORE') && !/fetch\(|XMLHttpRequest|sendBeacon/.test(kit.js));
ok('PATH_JS never gates: no lock/disabled on stations, suggestions labelled "never a lock"',
  kit && !/disabled|locked/.test(kit.js) && kit.js.includes('never a lock'));

// ---- region card (local play only, no leaderboard) and path.* labels in 8 locales
let reg2 = null;
try {
  reg2 = JSON.parse(execFileSync('python3', ['-c', 'import json,sys;sys.path.insert(0,"web");import pathkit as k;print(json.dumps({f:k.path_data(f)["region"] for f in sys.argv[1:]}|{"_keys":list(k.PATH_LABEL_KEYS)}))', ...P.map((p) => p.fips)], { cwd: ROOT, encoding: 'utf8' }));
} catch (e) { reg2 = null; }
const badRegion = [];
for (const p of reg2 ? P : []) {
  const r = reg2[p.fips];
  const wantB = p.adjacent.map((o) => `treasure-border-${[p.fips, o].sort().join('-')}`).sort();
  if (JSON.stringify(r.borders.map((b) => b.id).sort()) !== JSON.stringify(wantB) || !r.borders.every((b) => qById.has(b.id))) badRegion.push(`${p.fips}: borders`);
  const wantBadges = quests.quests.filter((q) => q.world === `parish:${p.fips}`).map((q) => q.id).sort();
  if (JSON.stringify(r.badges) !== JSON.stringify(wantBadges)) badRegion.push(`${p.fips}: badges ${r.badges.length} vs ${wantBadges.length}`);
  if (JSON.stringify(r.rides) !== '["treasure-ride-land","treasure-ride-water"]' || r.guide !== `treasure-guide-${p.fips}` || r.arrive !== `treasure-parish-${p.fips}-arrive`) badRegion.push(`${p.fips}: rides/guide/arrive`);
}
ok(`region card data per parish: badges = the parish's quests, borders = its adjacency, both rides, its guide (${P.length})`, reg2 && badRegion.length === 0, badRegion);
ok('region card counts local play only and says there is no leaderboard (no server, no accounts)',
  kit && kit.js.includes('No region leaderboard') && kit.js.includes('function region()') && kit.js.includes('card()')
  && /no leaderboard: no server, no accounts/i.test(kit.js) && !/fetch\(|XMLHttpRequest|WebSocket|sendBeacon/.test(kit.js));
const LOCS = ['en', 'ar', 'de', 'es', 'fr', 'hi', 'pt', 'zh'];
const cat = Object.fromEntries(LOCS.map((l) => [l, json(`i18n/locales/${l}.json`).strings]));
const keys = reg2 ? reg2._keys : [];
const badL = [];
for (const k of keys) {
  for (const l of LOCS) if (typeof cat[l]['path.' + k] !== 'string' || !cat[l]['path.' + k].trim()) badL.push(`${l}: path.${k} missing`);
  const en = cat.en['path.' + k];
  const copies = LOCS.filter((l) => l !== 'en' && cat[l]['path.' + k] === en);
  if (copies.length) badL.push(`path.${k} is an English copy in ${copies}`);
  const m = new RegExp("(?:^|[\\s{,])'?" + k.replace('.', '\\.') + "'?: '([^']*)'").exec(kit ? kit.js : '');
  if (!m || m[1] !== en) badL.push(`PATH_JS English default for ${k} differs from en.json`);
}
for (const p of P) for (const path of p.paths) if (cat.en['path.' + path.id] !== path.label) badL.push(`en path.${path.id} differs from the registry label ${path.label}`);
ok(`path.* labels: ${keys.length} keys in 8 locales, real translations, English defaults = en.json = registry path labels`, keys.length >= 18 && badL.length === 0, badL);
let labFail = false;
try { execFileSync('python3', ['-c', 'import sys;sys.path.insert(0,"web");import pathkit;pathkit.path_labels({})'], { cwd: ROOT, stdio: 'pipe' }); } catch (e) { labFail = /no path\.choose/.test(String(e.stderr)); }
ok('pathkit.path_labels fails by name on a catalog without path.* keys', labFail);

// ---- re-mount is idempotent (REVIEW finding 7): mount the same element 6 times (6 parish changes), one handler fires
let remount = null;
try {
  const two = JSON.parse(execFileSync('python3', ['-c', 'import json,sys;sys.path.insert(0,"web");import pathkit as k;print(json.dumps([k.path_data(f) for f in sys.argv[1:]]))', P[0].fips, P[1].fips], { cwd: ROOT, encoding: 'utf8' }));
  const live = { click: new Set(), keydown: new Set() }; const found = []; const finds = [];
  const node = () => ({ hidden: true, innerHTML: '', setAttribute() {}, focus() {}, querySelector: () => node(), classList: { add() {} } });
  const root = Object.assign(node(), {
    addEventListener(t, f, o) { live[t].add(f); if (o && o.signal) o.signal.addEventListener('abort', () => live[t].delete(f)); },
    querySelector: () => node(), querySelectorAll: () => [] });
  const win = { localStorage: { getItem: () => null, setItem() {} },
    TCQuests: { state: () => ({ found: {}, done: {} }), find: (id) => finds.push(id), on: (ev, f) => found.push(f) } };
  new Function('window', 'document', kit.js)(win, { dir: 'ltr', activeElement: null });
  for (let i = 0; i < 6; i++) win.TCPaths.mount(root, two[i % 2], { hrefPrefix: '' });
  const st = two[1].stations[0].id;
  const btn = { closest: (sel) => (sel.includes('data-pk-open') ? { hasAttribute: (x) => x === 'data-pk-open', getAttribute: () => st } : null) };
  for (const f of live.click) f({ target: btn });
  remount = { click: live.click.size, keydown: live.keydown.size, found: found.length, finds: finds.length, unmount: typeof win.TCPaths.unmount };
} catch (e) { remount = { error: String(e) }; }
ok('mounting the same element 6 times leaves one click, one keydown and one found listener; one click = one find',
  remount && remount.click === 1 && remount.keydown === 1 && remount.found === 1 && remount.finds === 1 && remount.unmount === 'function', JSON.stringify(remount));

// ---- wave 7: seven adventure paths + side stories (layers/registry/paths.json, PATHS_CONTRACT v1)
const P7 = json('layers/registry/paths.json');
const PIDS = ['trades', 'k12', 'responders', 'un', 'relief', 'teachers', 'roam'];
const q7reg = json('quests/registry/quests.json');
const q7ById = new Map(q7reg.quests.map((q) => [q.id, q]));
{
  const bad = [];
  if (JSON.stringify(P7.path_ids) !== JSON.stringify(PIDS)) bad.push('path_ids ' + P7.path_ids);
  if (JSON.stringify(P7.parishes.map((p) => p.fips)) !== JSON.stringify(P.map((p) => p.fips))) bad.push('parishes differ from layers');
  const by = Object.fromEntries(PIDS.map((k) => [k, 0]));
  let stories = 0;
  for (const p of P7.parishes) {
    if (JSON.stringify(p.paths.map((x) => x.id)) !== JSON.stringify(PIDS)) bad.push(`${p.fips}: paths ${p.paths.map((x) => x.id)}`);
    for (const x of p.paths) { by[x.id] += x.steps.length; if (x.gated !== false) bad.push(`${p.fips}.${x.id} gated`); }
    if (JSON.stringify(p.stories.map((x) => x.path)) !== JSON.stringify(PIDS)) bad.push(`${p.fips}: one story per path`);
    stories += p.stories.length;
  }
  if (JSON.stringify(by) !== JSON.stringify(P7.counts.steps_by_path) || stories !== P7.counts.stories) bad.push('counts ' + JSON.stringify(by));
  ok(`paths7: ${P7.parishes.length} parishes x 7 paths (${PIDS.join(', ')}), one side story each (${stories}); counts recomputed`, bad.length === 0 && stories === 7 * P.length, bad);
}
{
  const bad = [];
  for (const p of P7.parishes) {
    const lp = P.find((q) => q.fips === p.fips), st = new Map(lp.stations.map((s) => [s.id, s]));
    for (const x of p.paths) for (const s of x.steps) {
      if (s.kind === 'station') {
        if (!st.has(s.id)) bad.push(`${s.id}: no such station`);
        else if (x.id === 'trades' && !['trade-sim', 'task'].includes(st.get(s.id).layer)) bad.push(`${s.id}: trades step on layer ${st.get(s.id).layer}`);
        else if (x.id === 'k12' && !['k12-unit', 'lesson'].includes(st.get(s.id).layer)) bad.push(`${s.id}: k12 step on layer ${st.get(s.id).layer}`);
        else if (st.get(s.id).title !== s.title) bad.push(`${s.id}: title differs from layers`);
      } else if (s.kind === 'quest') { if (!q7ById.has(s.id)) bad.push(`${s.id}: no such quest`); }
      else if (s.kind === 'quote') { if (!st.has(s.station)) bad.push(`${s.id}: anchor ${s.station} is no station`); }
      else bad.push(`${s.id}: kind ${s.kind}`);
    }
    for (const story of p.stories) {
      const side = q7ById.get(story.quest), want = story.steps.map((x) => x.quest);
      if (!side || side.kind !== 'side' || JSON.stringify(side.requires.quests) !== JSON.stringify(want)) bad.push(`${story.quest}: side quest must require exactly its steps`);
      if (story.steps.length < 3 || story.steps.length > 5) bad.push(`${story.id}: ${story.steps.length} steps (3..5)`);
      if (story.steps[0].do !== 'talk' || story.steps[story.steps.length - 1].do !== 'talk') bad.push(`${story.id}: must start and end with the NPC`);
      story.steps.forEach((x, i) => {
        const q = q7ById.get(x.quest);
        if (!q || q.kind !== 'treasure' || q.world !== `parish:${p.fips}`) bad.push(`${x.quest}: not a parish treasure`);
        else if (JSON.stringify(q.requires.quests) !== JSON.stringify(i ? [story.steps[i - 1].quest] : [])) bad.push(`${x.quest}: must require only the previous step`);
        if (x.station && !st.has(x.station)) bad.push(`${x.quest}: station ${x.station} missing`);
      });
    }
  }
  ok('paths7: every station / quest / story step id resolves (layers stations, quests.json); stories talk -> ... -> talk, in order', bad.length === 0, bad);
}
{
  const walk = (src) => {
    const [rel, path] = src.split('#');
    let cur = json(rel);
    for (const part of path.match(/[^.[\]]+|\[\d+\]/g)) {
      const k = part.startsWith('[') ? +part.slice(1, -1) : part;
      if (cur == null || !(k in Object(cur))) return undefined;
      cur = cur[k];
    }
    return cur;
  };
  const bad = []; let n = 0;
  const allowed = { responders: /^respond\/registry\/respond\.json#scenario_frames\[\d+\]\.situation$/,
    un: /^respond\/registry\/respond\.json#(competencies|scenario_frames)\[\d+\]\.(what_it_is|situation)$/,
    relief: /^(respond\/registry\/respond\.json#(competencies|scenario_frames)\[\d+\]\.(what_it_is|situation)|restoration\/registry\/restoration\.json#tracks\[\d+\]\.what)$/,
    teachers: /^schools\/registry\/schools\.json#model\.(loop|stages\[\d+\]\.what)$/ };
  for (const p of P7.parishes) for (const x of p.paths) for (const s of x.steps) {
    if (s.kind !== 'quote') continue;
    n++;
    if (walk(s.source) !== s.quote) bad.push(`${s.id}: quote is not verbatim ${s.source}`);
    if (walk(s.title_source) !== s.title) bad.push(`${s.id}: title is not verbatim ${s.title_source}`);
    if (!allowed[x.id] || !allowed[x.id].test(s.source)) bad.push(`${s.id}: source ${s.source} not allowed on ${x.id}`);
    if (!s.source.startsWith(s.registry + '#')) bad.push(`${s.id}: registry/source mismatch`);
  }
  ok(`paths7: all ${n} quotes are verbatim at their source json path (and titles), from the registries each path may quote`, bad.length === 0 && n > 0, bad);
}
{
  const bad = [];
  const DIS = 'not affiliated with or endorsed by the United Nations';
  if (P7.un_disclaimer !== DIS || !P7.honesty.un.includes(DIS)) bad.push('registry disclaimer');
  const en = json('i18n/locales/en.json').strings;
  if (!en['path.p7.unNote'].includes(DIS)) bad.push('en path.p7.unNote lacks the disclaimer');
  if (!new RegExp("'p7\\.unNote': '[^']*" + DIS).test(kit.js)) bad.push('PATH_JS default unNote lacks the disclaimer');
  const UNOK = ['em.mass-care-coordination', 'em.access-functional-needs', 'em.volunteer-donations', 'resp.s.shelter-operations'];
  for (const p of P7.parishes) {
    const un = p.paths.find((x) => x.id === 'un');
    if (un.status !== 'PROPOSED' || !/PROPOSED/.test(un.label)) bad.push(`${p.fips}: un not PROPOSED`);
    for (const s of un.steps) {
      if (!UNOK.includes(s.ref_id)) bad.push(`${s.id}: ${s.ref_id} is not a humanitarian-theme item`);
      if (/united nations|\bUN\b|UNHCR|UNICEF|OCHA|WFP/i.test(s.quote + s.title)) bad.push(`${s.id}: quotes a UN name`);
    }
    for (const x of p.paths) if (x.id !== 'un' && x.status !== 'AVAILABLE') bad.push(`${p.fips}.${x.id}: status ${x.status}`);
  }
  ok('paths7 UN: PROPOSED module, disclaimer "' + DIS + '" in registry + en.json + PATH_JS, only humanitarian respond/ items, no UN names', bad.length === 0, bad);
}
{
  const bad = [];
  if (!/PROPOSED partners/.test(P7.honesty.k12)) bad.push('honesty.k12');
  if (!/PROPOSED/.test(json('i18n/locales/en.json').strings['path.p7.k12Note'])) bad.push('en path.p7.k12Note');
  if (!/unverified general practice/.test(P7.honesty.lessons)) bad.push('honesty.lessons');
  for (const p of P7.parishes) if (!/PROPOSED partner/.test(p.paths.find((x) => x.id === 'k12').what)) bad.push(`${p.fips}: k12 what`);
  ok('paths7 K-12: districts stay PROPOSED partners (registry, en.json, every parish), lessons unverified general practice', bad.length === 0, bad);
}
{
  const bad = [];
  const CR = /crash|collid|wreck/i;
  for (const p of P7.parishes) for (const story of p.stories) for (const x of story.steps) {
    if (CR.test(JSON.stringify(x))) bad.push(`${x.quest}: mentions a crash`);
    if (x.hook && /hit|crash|collid|wreck/i.test(x.hook)) bad.push(`${x.quest}: hook ${x.hook}`);
    const q = q7ById.get(x.quest);
    if (q && CR.test(q.title + ' ' + q.hint + ' ' + q.reward.label)) bad.push(`${x.quest}: quest text rewards a crash`);
  }
  for (const h of P7.ambient_hooks) if (!/^ambient\.(pet-found|litter-picked)$/.test(h)) bad.push('hook ' + h);
  ok('paths7: no side-story step, hook or quest rewards crashing; ambient hooks are pet-found / litter-picked only', bad.length === 0, bad);
}
{
  let r = null;
  try {
    const f = P[4].fips;
    const d = JSON.parse(execFileSync('python3', ['-c', 'import json,sys;sys.path.insert(0,"web");import pathkit as k;print(json.dumps(k.path_data(sys.argv[1])))', f], { cwd: ROOT, encoding: 'utf8' }));
    const got = {};
    const node = () => ({ hidden: true, innerHTML: '', setAttribute() {}, focus() {}, querySelector: () => node(), classList: { add() {} } });
    const root = Object.assign(node(), { addEventListener() {}, querySelector: () => node(), querySelectorAll: () => [] });
    const win = { localStorage: { getItem: () => null, setItem() {} },
      TCQuests: { state: () => ({ found: { ...got }, done: {} }), find: (id) => { got[id] = 't'; }, on() {} } };
    new Function('window', 'document', kit.js)(win, { dir: 'ltr', activeElement: null });
    win.TCPaths.mount(root, d, { hrefPrefix: '' });
    const html = {};
    for (const pid of PIDS) { win.TCPaths.adventure(pid); html[pid] = root.innerHTML; }
    const radios = (html.un.match(/role="radio" data-pk-adv="/g) || []).length;
    const prop = (html.un.match(/class="pk-prop"/g) || []).length;
    const roam = d.adventure.stories.find((s) => s.path === 'roam');
    const lot = roam.steps.find((x) => x.hook === 'econ.lot-rented').lots[0];
    const seq = [win.TCPaths.hook('ambient.pet-found').length, win.TCPaths.talk('host').length,
      win.TCPaths.hook('ambient.litter-picked').length, win.TCPaths.hook('ambient.pet-found').length,
      win.TCPaths.hook('ambient.litter-picked').length, win.TCPaths.hook('econ.lot-rented', { lotId: 'lot-00000-r01' }).length,
      win.TCPaths.hook('econ.lot-rented').length, win.TCPaths.hook('econ.lot-rented', { lotId: lot }).length, win.TCPaths.talk('host').length];
    let crashThrew = false; try { win.TCPaths.hook('vehicle.crash'); } catch (e) { crashThrew = /crash/.test(e.message); }
    r = { radios, prop, unNote: html.un.includes('data-pk-un') && html.un.includes('not affiliated with or endorsed by the United Nations'),
      k12Note: /PROPOSED partners/.test(html.k12), quote: html.responders.includes('<blockquote>') && html.responders.includes('respond/registry/respond.json#'),
      story: /data-pk-story="story-/.test(html.relief), seq: seq.join(''), roamDone: win.TCPaths.story('roam').steps.every((x) => x.found), crashThrew };
  } catch (e) { r = { error: String(e) }; }
  ok('pathkit adventure: 7 radios, 1 PROPOSED badge (un), UN disclaimer + K-12 note shown, quotes with source, story advances only in order (talk, pet, litter, rent one of its lots, talk; wrong/missing lot refused), hook("...crash") throws',
    r && r.radios === 7 && r.prop === 1 && r.unNote && r.k12Note && r.quote && r.story && r.seq === '010110011' && r.roamDone && r.crashThrew, JSON.stringify(r));
}

{
  const bad = [];
  const eco = json('economy/registry/economy.json');
  const WANT = { trades: ['econ.shop-opened', 'shop'], roam: ['econ.lot-rented', 'home'] };
  const EVENTS = /^econ\.(shop-opened|lot-rented|first-shop-opened|first-rent-paid|rent-paid|lot-bought|staff-hired|skill-unlocked)$/;
  for (const p of P7.parishes) {
    const lots = new Map(eco.parishes[p.fips].lots.map((l) => [l.id, l]));
    for (const story of p.stories) {
      const ec = story.steps.filter((x) => x.do === 'econ' || /^econ\./.test(x.hook || ''));
      if (!WANT[story.path]) { if (ec.length) bad.push(`${story.id}: unexpected city-life step`); continue; }
      if (ec.length !== 1) { bad.push(`${story.id}: ${ec.length} city-life steps`); continue; }
      const x = ec[0];
      if (x.hook !== WANT[story.path][0] || !EVENTS.test(x.hook)) bad.push(`${x.quest}: hook ${x.hook}`);
      if (!x.lots.length || x.lots.some((l) => !lots.has(l) || !lots.get(l).allowed.includes(WANT[story.path][1]))) bad.push(`${x.quest}: lot ids not ${WANT[story.path][1]} lots of ${p.fips} in economy.json`);
      if (!/play coins, not money/.test(x.text)) bad.push(`${x.quest}: text must say play coins, not money`);
    }
  }
  if (!/PLAY COINS only, never money/.test(P7.honesty.econ)) bad.push('honesty.econ');
  ok('paths7 econ: trades (shop opened) and roam (lot rented) stories carry one city-life step per parish, hooks are ECON_CONTRACT events, lots are that parish\'s economy.json shop/home lots, play coins not money', bad.length === 0, bad);
}

console.log(fails ? `layers/test: ${fails} FAILED` : 'layers/test: all passed');
process.exit(fails ? 1 : 0);
