#!/usr/bin/env node
/* quests/test.mjs - the quest registry and engine, held to the contract.
   Prints "  ok " per check, FAIL at column 0, exits non-zero on failure. */
import { readFileSync, existsSync, readdirSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { execFileSync } from 'node:child_process';
import * as Q from './engine.mjs';

const HERE = dirname(fileURLToPath(import.meta.url));
const ROOT = join(HERE, '..');
let fails = 0;
function ok(name, cond, detail) {
  if (cond) { console.log('  ok ' + name); return; }
  fails++; console.log('FAIL ' + name);
  for (const d of [].concat(detail || []).slice(0, 8)) console.log('     ' + d);
}
const read = (p) => readFileSync(join(ROOT, p), 'utf8');
const reg = JSON.parse(read('quests/registry/quests.json'));
const lessons = JSON.parse(read('lessons/registry/lessons.json'));
const halls = new Set(JSON.parse(read('pack/registry/halls.json')).halls.map((h) => h.slug));
const L = lessons.lessons;
const ids = new Set(reg.quests.map((q) => q.id));

ok(`ids are unique and kebab-case (${reg.quests.length})`, ids.size === reg.quests.length && reg.quests.every((q) => /^[a-z0-9]+(-[a-z0-9]+)*$/.test(q.id)));
ok('every kind is main | side | game | treasure | egg', reg.quests.every((q) => ['main', 'side', 'game', 'treasure', 'egg'].includes(q.kind)));
const bad = [];
for (const q of reg.quests) {
  for (const l of q.requires.lessons) if (!(l in L)) bad.push(`${q.id}: lesson ${l}`);
  for (const h of q.requires.halls) if (!halls.has(h)) bad.push(`${q.id}: hall ${h}`);
  for (const r of q.requires.quests) if (!ids.has(r)) bad.push(`${q.id}: quest ${r}`);
}
ok('every requires id resolves (lessons, halls, quests)', bad.length === 0, bad);
const expect = (r) => {
  if (!r.lessons.every((i) => i in L) || !r.quests.every((i) => ids.has(i))) return null; // named by the resolve check above
  const parts = [];
  if (r.lessons.length) parts.push('walk ' + r.lessons.map((i) => `"${L[i].title}"`).join(', '));
  if (r.halls.length) parts.push('finish a lesson in ' + r.halls.map((h) => JSON.parse(read('pack/registry/halls.json')).halls.find((x) => x.slug === h).name).join(', '));
  if (r.quests.length) parts.push('finish ' + r.quests.map((i) => `"${reg.quests.find((x) => x.id === i).title}"`).join(', '));
  return parts.length ? 'To unlock: ' + parts.join('; ') + '.' : 'Open to everyone.';
};
const ut = reg.quests.filter((q) => q.unlock_text !== expect(q.requires)).map((q) => q.id);
ok('unlock_text is generated from requires for every entry', ut.length === 0, ut);
ok('every entry is AUTHORED provenance with a badge reward', reg.quests.every((q) => q.provenance === 'AUTHORED' && q.reward && q.reward.badge && q.reward.label));
ok('K-5 entries are explore-only (no lessons, no halls)', reg.quests.filter((q) => q.band === 'K-5').every((q) => !q.requires.lessons.length && !q.requires.halls.length));
ok('honesty says play, never evidence, never a completion record',
  /play/.test(reg.honesty) && /never evidence/.test(reg.honesty) && /never enter a completion record/.test(reg.honesty));
const hallsWithLessons = new Set(Object.values(L).map((l) => l.hall));
const sideHalls = new Set(reg.quests.filter((q) => q.id.startsWith('side-hall-')).map((q) => q.world.slice(5)));
ok(`a side quest for every hall that has lessons (${hallsWithLessons.size})`, [...hallsWithLessons].every((h) => sideHalls.has(h)));
ok('at least three arcade games, each gated by at least one lesson',
  reg.quests.filter((q) => q.kind === 'game').length >= 3 && reg.quests.filter((q) => q.kind === 'game').every((q) => q.requires.lessons.length > 0));

// every egg/treasure hook exists in the built page its world names, where that page carries the engine
const WORLD_PAGE = (w) => (w.startsWith('page:') ? w.slice(5) : null);
const missing = []; const pagesSeen = new Set();
for (const q of reg.quests.filter((x) => x.kind === 'egg' || x.kind === 'treasure')) {
  const p = WORLD_PAGE(q.world);
  if (!p) continue;
  pagesSeen.add(p);
  if (!existsSync(join(ROOT, p))) { missing.push(`${q.id}: ${p} does not exist`); continue; }
  const html = read(p);
  if (!html.includes('QUEST_CORE:BEGIN')) continue;
  if (!html.includes(`data-tc-egg="${q.id}"`)) missing.push(`${q.id}: no hook in ${p}`);
  if (q.target && !new RegExp('<' + q.target + '[\\s>]').test(html)) missing.push(`${q.id}: target ${q.target} not in ${p}`);
}
const carrying = [...pagesSeen].filter((p) => existsSync(join(ROOT, p)) && read(p).includes('QUEST_CORE:BEGIN'));
ok(`every egg/treasure hook is in the page its world names (${carrying.length} pages carry the engine)`, missing.length === 0 && carrying.length >= 3, missing);
const threeEach = carrying.filter((p) => reg.quests.filter((q) => q.world === 'page:' + p && (q.kind === 'egg' || q.kind === 'treasure')).length < 3);
ok('every page that carries the engine has at least three eggs or treasures', threeEach.length === 0, threeEach);

// engine core byte-identical in every page that carries it
const eng = read('quests/engine.mjs');
const core = eng.slice(eng.indexOf('/* QUEST_CORE:BEGIN'), eng.indexOf('/* QUEST_CORE:END */') + '/* QUEST_CORE:END */'.length);
const all = ['index.html', ...readdirSync(join(ROOT, 'web')).filter((f) => f.endsWith('.html')).map((f) => 'web/' + f)];
const carriers = all.filter((p) => read(p).includes('QUEST_CORE:BEGIN'));
const drift = carriers.filter((p) => !read(p).includes(core));
ok(`the engine core is byte-identical in every page that carries it (${carriers.length})`, carriers.length > 0 && drift.length === 0, drift);

// the evidence functions are the progress page's own, verbatim
const prog = read('web/build_progress.py');
const segA = prog.slice(prog.indexOf('const EVIDENCED_KINDS'), prog.indexOf('/* the digest input'));
const segB = prog.slice(prog.indexOf('function stepEvidence('), prog.indexOf('async function buildCompletionRecord'));
ok('the core carries the progress page\'s evidence functions verbatim', segA.length > 100 && segB.length > 100 && core.includes(segA) && core.includes(segB));
ok('the core names the storage key tc-quests and reads the progress keys from data, not typed', Q.QUEST_STORE === 'tc-quests' && !core.includes("'tc-progress'"));

// lessonsDone over a synthetic record the way the progress page's own suite seeds one
const training = JSON.parse(read('training/registry/training.json')).episode_kinds;
const D = { lessons: {}, meta: { step_kinds: lessons.step_kinds, episode_kinds: training, human_actor: 'human' } };
D.lessons['crane-ops-read-the-chart'] = { hall: L['crane-ops-read-the-chart'].hall, steps: L['crane-ops-read-the-chart'].steps };
ok('an empty device counts no lesson done', Q.questLessonsDone(null, null, D).size === 0);
const lesson = L['crane-ops-read-the-chart'];
const progSeed = { sims: {}, tools: {}, stations: [] };
const trainSeed = [];
const t = new Date(0).toISOString();
for (const s of lesson.steps) {
  if (s.kind === 'sim') progSeed.sims[s.sim] = { passed: true, runs: 1 };
  if (s.kind === 'station') progSeed.stations.push(s.station);
  if (s.kind === 'crib') progSeed.tools[s.crib] = { passed: true };
  if (s.kind in Q.REF_FIELDS) { const ep = { kind: s.kind, hall: lesson.hall, t, actor: 'human' }; for (const f of Q.REF_FIELDS[s.kind]) ep[f] = s[f]; trainSeed.push(ep); }
}
ok('a device holding every recordable step of a lesson counts it done', Q.questLessonsDone(progSeed, trainSeed, D).has('crane-ops-read-the-chart'));
const half = { ...progSeed, sims: {} };
ok('a device missing the seat pass does not', !Q.questLessonsDone(half, trainSeed, D).has('crane-ops-read-the-chart'));

// check / record
const game = reg.quests.find((q) => q.id === 'game-load-chart');
const T = { lessons: { 'crane-ops-read-the-chart': 'x' }, lesson_hall: { 'crane-ops-read-the-chart': 'crane-ops' }, halls: {}, quests: {} };
const st0 = Q.questEmptyState();
const c0 = Q.questCheck(game, st0, new Set(), T);
ok('check() names the missing lessons of a locked game', !c0.ok && c0.missing.some((m) => m.kind === 'lesson' && m.id === 'crane-ops-read-the-chart'));
ok('record() refuses a locked entry', Q.questRecord(st0, game, t, c0).changed === false);
const c1 = Q.questCheck(game, st0, new Set(['crane-ops-read-the-chart']), T);
const r1 = Q.questRecord(st0, game, t, c1);
ok('record() records an open entry once and gives its badge', c1.ok && r1.changed && r1.state.done[game.id] === t && r1.state.badges.includes(game.reward.badge) && !Q.questRecord(r1.state, game, t, c1).changed);
ok('a garbled store parses to an empty state', JSON.stringify(Q.questParseState('{nope')) === JSON.stringify(st0));
let buf = []; let hits = [];
for (const k of Q.QUEST_KONAMI) { const r = Q.questKeys(buf, k, ['hardhat']); buf = r.buf; hits = hits.concat(r.hits); }
ok('the konami sequence triggers konami', hits.includes('konami'));
buf = []; hits = [];
for (const k of 'xhardhat') { const r = Q.questKeys(buf, k, ['hardhat']); buf = r.buf; hits = hits.concat(r.hits); }
ok('a typed word triggers typed:<word>', hits.includes('typed:hardhat'));

// CAMPUS's published entries (quests/source/campus.json) all land, unchanged, with no trigger fields
const campus = JSON.parse(read('quests/source/campus.json')).entries;
const byId = new Map(reg.quests.map((q) => [q.id, q]));
const cmiss = campus.filter((e) => { const q = byId.get(e.id);
  return !q || q.kind !== e.kind || q.world !== e.world || q.place !== e.place || q.title !== e.title || 'trigger' in q
    || JSON.stringify(q.requires) !== JSON.stringify(e.requires) || q.reward.badge !== e.reward.badge; }).map((e) => e.id);
ok(`every CAMPUS entry is registered as published, campus | hall:<id>, no trigger (${campus.length})`, campus.length > 0 && cmiss.length === 0, cmiss);
// every WILDS hidden cache has an explore-only treasure placed on it; every site with a gate has a side quest
const wreg = JSON.parse(read('wilds/registry/wilds.json'));
const wmiss = [];
for (const w of wreg.worlds) {
  for (const c of w.caches) { const q = byId.get(`treasure-wilds-${c.id}`);
    if (!q || q.kind !== 'treasure' || q.world !== `wilds:${w.id}` || q.place !== c.id || q.band !== 'K-5') wmiss.push(`${w.id}/${c.id}`); }
  for (const s of w.sites) {
    const gated = s.lessons.length || (s.halls.length && s.halls.every((h) => hallsWithLessons.has(h.id)));
    if (gated && !byId.has(`side-wilds-${s.id}`)) wmiss.push(`${w.id}/${s.id} (side)`);
  }
}
ok('every wilds cache has a K-5 treasure on it, and every gateable wilds site a side quest', wmiss.length === 0, wmiss);

// ---- the parish world (layers/registry/layers.json + parishes/ + fleet/): all play, never gated on lessons
const layers = JSON.parse(read('layers/registry/layers.json'));
const preg = JSON.parse(read('parishes/registry/parishes.json'));
const fips = layers.parishes.map((p) => p.fips);
const pq = reg.quests.filter((q) => q.world === 'parishes' || q.world.startsWith('parish:'));
const pbad = [];
const words = new Set();
for (const p of layers.parishes) {
  const w = `parish:${p.fips}`;
  const a = byId.get(`treasure-parish-${p.fips}-arrive`);
  if (!a || a.kind !== 'treasure' || a.world !== w || a.band !== 'K-5' || !a.reward.label.includes(p.name)) pbad.push(`${p.fips}: region badge`);
  const e = byId.get(`egg-parish-${p.fips}-word`);
  if (!e || e.kind !== 'egg' || e.world !== w || !/^typed:[a-z]+$/.test(e.trigger || '')) pbad.push(`${p.fips}: egg`); else words.add(e.trigger);
  const g = byId.get(`treasure-guide-${p.fips}`);
  if (!g || g.kind !== 'treasure' || g.world !== w) pbad.push(`${p.fips}: guide treasure`);
  for (const l of p.landmarks) if (!byId.has(`treasure-parish-${p.fips}-lm-${l.id}`)) pbad.push(`${p.fips}: landmark ${l.id}`);
  for (const path of p.paths) {
    const sq = byId.get(`side-parish-${p.fips}-${path.id}`);
    const want = path.steps.map((s) => (path.id === 'explorer' ? s : `treasure-station-${s}`));
    if (!sq || sq.kind !== 'side' || JSON.stringify(sq.requires.quests) !== JSON.stringify(want)) pbad.push(`${p.fips}: ${path.id} path side quest`);
  }
}
ok(`every parish has a region badge, a typed egg (distinct words), a guide treasure, landmark treasures and one side quest per path (${fips.length} parishes)`,
  pbad.length === 0 && words.size === fips.length, pbad);
const edges = new Set();
for (const [f, p] of Object.entries(preg.parishes)) for (const o of p.adjacent) if (fips.includes(o)) edges.add([f, o].sort().join('-'));
const borderIds = [...edges].sort().map((e) => `treasure-border-${e}`);
const haveBorders = pq.filter((q) => q.id.startsWith('treasure-border-')).map((q) => q.id).sort();
const mb = byId.get('main-parishes-borders');
ok(`"Cross every connected border": one treasure per shared border (${edges.size}) and the main quest requires exactly them`,
  edges.size > 0 && JSON.stringify(haveBorders) === JSON.stringify(borderIds) && mb && mb.kind === 'main'
  && JSON.stringify([...mb.requires.quests].sort()) === JSON.stringify(borderIds), [`have ${haveBorders.length}`, `want ${borderIds.length}`]);
const media = [...new Set(JSON.parse(read('fleet/registry/fleet.json')).fleet.map((v) => v.medium))].sort();
const mm = byId.get('main-parishes-media');
ok(`"Ride one of each medium": ${media.join(' + ')} (from fleet/), one ride treasure each, required by the main quest`,
  media.length === 2 && mm && JSON.stringify([...mm.requires.quests].sort()) === JSON.stringify(media.map((m) => `treasure-ride-${m}`))
  && media.every((m) => byId.has(`treasure-ride-${m}`)));
const mg = byId.get('main-parishes-guides'); const mr = byId.get('main-parishes-regions');
ok(`"Talk to N guides" and "every parish": N = ${fips.length}, computed, requiring one guide / one arrival per parish`,
  mg && mg.title === `Talk to ${fips.length} guides` && JSON.stringify(mg.requires.quests) === JSON.stringify(fips.map((f) => `treasure-guide-${f}`))
  && mr && JSON.stringify(mr.requires.quests) === JSON.stringify(fips.map((f) => `treasure-parish-${f}-arrive`)));
ok(`parish-world entries (${pq.length}) are AUTHORED play: never gated on lessons or halls, every parish world is a layers parish`,
  pq.length > 0 && pq.every((q) => q.provenance === 'AUTHORED' && !q.requires.lessons.length && !q.requires.halls.length
    && (q.world === 'parishes' || fips.includes(q.world.slice(7)))));
let qcheck = '';
try { qcheck = execFileSync('python3', ['quests/build.py', '--check'], { cwd: ROOT, encoding: 'utf8', stdio: ['ignore', 'pipe', 'pipe'] }); } catch (e) { qcheck = String(e.stdout) + String(e.stderr); }
ok('python3 quests/build.py --check: the registry is current (stamp over lessons, sims, campus, wilds, layers, fleet)', /is current/.test(qcheck), qcheck.trim());

let scope = null;
try {
  scope = JSON.parse(execFileSync('python3', ['-c', 'import json,sys;sys.path.insert(0,"web");import questkit as k;print(json.dumps({"ids":sorted(q["id"] for q in k.QUESTS if k.in_scope(q,"parishes")),"page":k.SCOPE_PAGE["parishes"],"js":"parish:" in k.quest_js("parishes")}))'], { cwd: ROOT, encoding: 'utf8' }));
} catch (e) { scope = null; }
ok(`questkit scope 'parishes' holds exactly the parish-world entries (${pq.length}) and binds to web/trade_craft_parishes.html`,
  scope && JSON.stringify(scope.ids) === JSON.stringify(pq.map((q) => q.id).sort()) && scope.page === 'web/trade_craft_parishes.html' && scope.js);

// wave 7: side-story entries ride as compact rows + one text table; the page's own script must rebuild them exactly
{
  let r = null;
  try {
    const py = 'import json,sys;sys.path.insert(0,"web");import questkit as k\n'
      + 'js=k.quest_js("parishes");head=js.index("const QD = ");g=js.index(k.GLUE_JS)\n'
      + 'print(json.dumps({"prefix":js[js.index(chr(34)+"use strict"+chr(34)+";")+13:g],"full":k._data("parishes","web/trade_craft_parishes.html"),"size":len(js.encode()),'
      + '"campus":"QD.story" in k.quest_js("campus")}))';
    const o = JSON.parse(execFileSync('python3', ['-c', py], { cwd: ROOT, encoding: 'utf8', maxBuffer: 64 << 20 }));
    const QD = new Function(o.prefix + '\nreturn QD;')();
    const sortT = (m) => JSON.stringify(Object.keys(m).sort().map((k) => [k, m[k]]));
    const nStory = o.full.quests.filter((q) => /^(treasure|side)-story-/.test(q.id)).length;
    r = { same: JSON.stringify(QD.quests) === JSON.stringify(o.full.quests), titles: sortT(QD.titles.quests) === sortT(o.full.titles.quests),
      compacted: o.prefix.includes('"story":{"t":['), nStory, size: o.size, campus: o.campus };
  } catch (e) { r = { error: String(e).slice(0, 300) }; }
  ok(`questkit: the parish page's ${r.nStory} side-story entries ride compact (${r.size} bytes) and its script rebuilds every entry and title exactly; other scopes unchanged`,
    r.same === true && r.titles === true && r.compacted && r.nStory > 0 && r.campus === false, JSON.stringify(r));
}

// wave 12 (BAYOU, GAMES_CONTRACT): every quests/source/*.json is loaded, owner-prefixed, informative, in a known world
{
  const srcDir = join(ROOT, 'quests/source');
  const files = readdirSync(srcDir).filter((f) => f.endsWith('.json')).sort();
  const want = Object.fromEntries(files.map((f) => ['quests/source/' + f, JSON.parse(read('quests/source/' + f)).entries.length]));
  ok(`quests/build.py loads every quests/source/*.json, sorted (${files.length}: ${files.join(', ')})`,
    reg.sources && JSON.stringify(reg.sources) === JSON.stringify(want) && files.every((f) => reg.reads.includes('quests/source/' + f)),
    JSON.stringify({ reg: reg.sources, want }));
  const byId = Object.fromEntries(reg.quests.map((q) => [q.id, q]));
  const badSrc = [];
  const seen = {};
  for (const f of files) {
    const stem = f.slice(0, -5);
    for (const e of JSON.parse(read('quests/source/' + f)).entries) {
      if (seen[e.id]) badSrc.push(`${e.id}: in ${seen[e.id]} and ${f}`);
      seen[e.id] = f;
      const q = byId[e.id];
      if (!q) { badSrc.push(`${e.id}: in ${f} but not in the registry`); continue; }
      if (q.world !== e.world || q.kind !== e.kind || q.reward.badge !== 'badge-' + e.id) badSrc.push(`${e.id}: world/kind/badge differ from ${f}`);
      if (f === 'campus.json') continue;
      if (!e.id.startsWith(`${e.kind}-${stem}-`)) badSrc.push(`${e.id}: not ${e.kind}-${stem}-*`);
      if (typeof q.reveal !== 'string' || q.reveal.trim().length < 20) badSrc.push(`${e.id}: no informative reveal`);
      if (q.trigger && !/^(konami|typed:[a-z]{3,24}|clicks:[2-9])$/.test(q.trigger)) badSrc.push(`${e.id}: trigger ${q.trigger}`);
    }
  }
  ok('source entries: one owner file each, owner-prefixed ids, badge-<id>, a one-line informative reveal, contract triggers', badSrc.length === 0, badSrc);
  const bay = new Set(Object.keys(JSON.parse(read('bayarea/registry/bayarea.json')).counties));
  const wildsIds = existsSync(join(ROOT, 'wilds/registry/wilds.json')) ? new Set(JSON.parse(read('wilds/registry/wilds.json')).worlds.map((w) => w.id)) : null;
  const smilesZ = existsSync(join(ROOT, 'smiles/registry/smiles.json')) ? new Set(JSON.parse(read('smiles/registry/smiles.json')).zones.map((z) => z.id)) : null;
  const badW = reg.quests.filter((q) => (q.world.startsWith('bay:') && !bay.has(q.world.slice(4)))
    || (q.world.startsWith('wilds:') && wildsIds && !wildsIds.has(q.world.slice(6)))
    || ((q.world === 'smiles' || q.world.startsWith('smiles:')) && (!smilesZ || (q.world.startsWith('smiles:') && !smilesZ.has(q.world.slice(7))))))
    .map((q) => `${q.id}: ${q.world}`);
  ok('wave-12 world kinds resolve: bay:<fips> in bayarea counties, wilds:<id> in wilds worlds, smiles:<zone> in smiles zones', badW.length === 0, badW);
  const noFact = reg.quests.filter((q) => q.reveal !== undefined && /\b\d+(\.\d+)?\s*(ft|feet|lb|lbs|pounds|kg|inches|cm|mph|years? old)\b/i.test(q.reveal)).map((q) => q.id);
  ok('no reveal quotes an invented measurement (sizes, weights, speeds)', noFact.length === 0, noFact);
  let sc = null;
  try {
    sc = JSON.parse(execFileSync('python3', ['-c', 'import json,sys;sys.path.insert(0,"web");import questkit as k;print(json.dumps({s:{"n":sum(1 for q in k.QUESTS if k.in_scope(q,s)),"page":k.SCOPE_PAGE[s],"reveal":"reveal" in json.dumps(k._data(s,k.SCOPE_PAGE[s])) if any(k.in_scope(q,s) for q in k.QUESTS) else None} for s in ("bay","smiles")}))'], { cwd: ROOT, encoding: 'utf8', maxBuffer: 64 << 20 }));
  } catch (e) { sc = { error: String(e).slice(0, 200) }; }
  const nBay = reg.quests.filter((q) => q.world === 'bay' || q.world.startsWith('bay:')).length;
  const nSm = reg.quests.filter((q) => q.world === 'smiles' || q.world.startsWith('smiles:')).length;
  ok(`questkit scopes 'bay' (${nBay}) and 'smiles' (${nSm}) hold exactly their world entries, bind to their pages and carry reveal lines`,
    sc && sc.bay && sc.bay.n === nBay && sc.bay.page === 'web/trade_craft_bay.html' && sc.smiles.n === nSm && sc.smiles.page === 'web/trade_craft_smiles.html'
    && (nBay === 0 || sc.bay.reveal === true), JSON.stringify(sc));
}

console.log(fails ? `quests/test: ${fails} FAILED` : 'quests/test: all passed');
process.exit(fails ? 1 : 0);
