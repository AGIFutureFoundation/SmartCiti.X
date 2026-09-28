/**
 * NPC guides verification: registry + kit.
 *
 * Every NPC line in npcs/registry/npcs.json is re-read from the registry field
 * its source path names and compared byte for byte; counts, places, names,
 * looks and pointers are recomputed; the web/npckit.py kit's behaviour state
 * machine, steering, frame budget and dialogue accessibility are exercised in
 * node (real vendored three.js, a small fake DOM).
 *
 *   node npcs/test.mjs
 *   node npcs/test.mjs --root=/tmp/copy      (mutation runs: a broken copy)
 */
import { createHash } from 'node:crypto';
import { readFileSync, readdirSync, existsSync, writeFileSync, mkdtempSync } from 'node:fs';
import { join, resolve, dirname } from 'node:path';
import { tmpdir } from 'node:os';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { execFileSync } from 'node:child_process';

const HERE = dirname(fileURLToPath(import.meta.url));
const args = process.argv.slice(2);
const hit = args.find((a) => a.startsWith('--root='));
const ROOT = resolve(hit ? hit.slice(7) : join(HERE, '..'));

let n = 0, bad = 0;
const ok = (m, c, evidence = []) => {
  if (c) { n++; console.log('  ok  ' + m); return; }
  bad++;
  console.log('FAIL  ' + m);
  for (const e of evidence.slice(0, 8)) console.log('      ' + e);
};
const readJSON = (rel) => JSON.parse(readFileSync(join(ROOT, rel), 'utf8'));
const cache = new Map();
const src = (rel) => { if (!cache.has(rel)) cache.set(rel, readJSON(rel)); return cache.get(rel); };

// "<file>#a.b[2].c" -> value | undefined
function resolvePath(ref) {
  const [rel, path] = ref.split('#');
  if (!rel || !path || !existsSync(join(ROOT, rel))) return undefined;
  let node = src(rel);
  const re = /\.?([A-Za-z0-9_\-]+)|\[(\d+)\]/y;
  let m;
  re.lastIndex = 0;
  while (re.lastIndex < path.length && (m = re.exec(path))) {
    if (m[2] !== undefined) { if (!Array.isArray(node)) return undefined; node = node[Number(m[2])]; }
    else { if (node === null || typeof node !== 'object' || Array.isArray(node) || !(m[1] in node)) return undefined; node = node[m[1]]; }
    if (node === undefined) return undefined;
  }
  return re.lastIndex === path.length ? node : undefined;
}

const REG = 'npcs/registry/npcs.json';
const reg = readJSON(REG);
const npcs = reg.npcs;

// ---------------------------------------------------------------- stamp --
{
  const h = createHash('sha256');
  h.update(readFileSync(join(ROOT, 'npcs/build.py')));
  for (const k of Object.keys(reg.sources).sort()) h.update(readFileSync(join(ROOT, reg.sources[k])));
  const want = h.digest('hex').slice(0, 16);
  ok(`stamp: source_stamp ${reg.source_stamp} = sha256(build.py + sources)[:16]`, reg.source_stamp === want,
     [`recomputed ${want}`]);
}

// --------------------------------------------------------------- counts --
{
  const byRole = {};
  for (const x of npcs) byRole[x.role] = (byRole[x.role] || 0) + 1;
  ok(`counts: ${npcs.length} NPCs = counts.npcs`, npcs.length === reg.counts.npcs);
  ok('counts: by_role recomputed', JSON.stringify(Object.fromEntries(Object.entries(byRole).sort()))
     === JSON.stringify(reg.counts.by_role), [JSON.stringify(byRole)]);
  ok('counts: lines recomputed', npcs.reduce((s, x) => s + x.knowledge.length, 0) === reg.counts.lines);
  ok('counts: parishes recomputed', reg.parishes.length === reg.counts.parishes);
  const fams = Object.keys(readJSON('unions/registry/districts.json').districts);
  const dupIds = npcs.map((x) => x.id).filter((id, i, a) => a.indexOf(id) !== i);
  ok('counts: NPC ids unique', dupIds.length === 0, dupIds);
  // trade families present, recomputed from LAYERS stations and each station's owning registry
  const famOf = {};
  for (const [f, d] of Object.entries(readJSON('unions/registry/districts.json').districts)) for (const h of d.halls) famOf[h] = f;
  const presentFams = (fips) => {
    if (reg.places_status === 'STUB') return fams;
    const lay = readJSON('layers/registry/layers.json').parishes.find((q) => q.fips === fips);
    const sims = readJSON('sims/registry/sims.json').sims, les = readJSON('lessons/registry/lessons.json').lessons;
    const tasks = Object.fromEntries(readJSON('tasks/registry/tasks.json').tasks.map((t) => [t.id, t]));
    const out = new Set();
    for (const st of lay.stations) {
      const r = st.ref.id;
      const halls = st.layer === 'trade-sim' ? sims[r].halls : st.layer === 'task'
        ? (tasks[r].place.kind === 'hall' ? [tasks[r].place.id] : []) : st.layer === 'k12-unit' ? [r] : [les[r].hall];
      for (const h of halls) out.add(famOf[h]);
    }
    return [...out];
  };
  for (const p of reg.parishes) {
    const here = npcs.filter((x) => x.parish === p.fips);
    const mf = here.filter((x) => x.role === 'mentor').map((x) => x.family);
    const want = presentFams(p.fips);
    ok(`counts: parish ${p.fips} has one mentor per trade family present (${want.length})`,
       mf.length === want.length && want.every((f) => mf.includes(f)), [`mentors ${mf.join(',')}`, `present ${want.join(',')}`]);
    ok(`counts: parish ${p.fips} has 2 K-12 guides, 1..4 hosts`,
       here.filter((x) => x.role === 'k12-guide').length === 2 && here.some((x) => x.role === 'host')
       && here.filter((x) => x.role === 'host').length <= 4);
    if (reg.places_status === 'STUB') {
      ok(`counts: STUB parish ${p.fips} also has a ranger and a pilot`,
         here.some((x) => x.role === 'ranger') && here.some((x) => x.role === 'pilot'));
    } else {
      const lms = readJSON('layers/registry/layers.json').parishes.find((q) => q.fips === p.fips).landmarks;
      const wantR = lms.some((l) => /park|refuge|preserve|spillway/.test(l.kind));
      const wantP = lms.some((l) => /port|ferry|bridge|lake|river|levee|refuge|spillway/.test(l.kind));
      ok(`counts: parish ${p.fips} ranger ${wantR ? 1 : 0} / pilot ${wantP ? 1 : 0} per the landmark-kind rule (never faked)`,
         here.filter((x) => x.role === 'ranger').length === (wantR ? 1 : 0)
         && here.filter((x) => x.role === 'pilot').length === (wantP ? 1 : 0));
    }
  }
  const badLen = npcs.filter((x) => x.knowledge.length < 3 || x.knowledge.length > 8).map((x) => x.id);
  ok('counts: every NPC carries 3..8 knowledge lines', badLen.length === 0, badLen);
}

// ------------------------------------------------------ verbatim quotes --
{
  const allowed = new Set(['unions/registry/unions.json', 'unions/registry/districts.json',
    'schools/registry/schools.json', 'lessons/registry/lessons.json', 'tasks/registry/tasks.json',
    'restoration/registry/restoration.json']);
  const miss = [], foreign = [];
  let checked = 0;
  for (const x of npcs) {
    for (const q of [...x.knowledge, x.not_certification]) {
      checked++;
      if (!allowed.has(q.source.split('#')[0])) foreign.push(`${x.id}: ${q.source}`);
      const v = resolvePath(q.source);
      if (typeof v !== 'string' || v !== q.text) miss.push(`${x.id}: ${q.source}`);
    }
  }
  ok(`quote: all ${checked} lines match their source field verbatim`, miss.length === 0, miss);
  ok('quote: every line comes from unions/schools/lessons/tasks/restoration', foreign.length === 0, foreign);
  const k12bad = npcs.filter((x) => x.role === 'k12-guide').filter((x) => x.layer !== 'Cognition.X K-12'
    || x.knowledge.some((q) => !/^(schools|lessons)\/registry\//.test(q.source))).map((x) => x.id);
  ok('quote: Cognition.X K-12 guides quote only schools/ and lessons/', k12bad.length === 0, k12bad);
  const noCert = npcs.filter((x) => !x.not_certification || !x.not_certification.text).map((x) => x.id);
  ok('quote: every NPC carries a verbatim not-a-certification line', noCert.length === 0, noCert);
  const dupLine = npcs.filter((x) => new Set(x.knowledge.map((q) => q.source)).size !== x.knowledge.length).map((x) => x.id);
  ok('quote: no NPC repeats a source', dupLine.length === 0, dupLine);
}

// ----------------------------------------------------------- real names --
{
  const DENY = ['Louis Armstrong', 'Andrew Jackson', 'Marie Laveau', 'Fats Domino', 'Mahalia Jackson',
    'Huey Long', 'Edwin Edwards', 'Ruby Bridges', 'Harry Connick', 'Drew Brees', 'Lil Wayne',
    'Tennessee Williams', 'Anne Rice', 'Truman Capote', 'Jean Lafitte', 'Marie Harrison',
    'Martin Luther King', 'George Washington', 'Abraham Lincoln', 'Barack Obama', 'Donald Trump',
    'Joe Biden', 'Kamala Harris', 'Elon Musk', 'Taylor Swift', 'Beyonce Knowles', 'Oprah Winfrey',
    'Allen Toussaint', 'Dr. John', 'Irma Thomas', 'Wynton Marsalis', 'Mitch Landrieu', 'LaToya Cantrell',
    'John Bel Edwards', 'Jeff Landry', 'Bobby Jindal', 'Kathleen Blanco', 'Ray Nagin', 'Tom Benson',
    'Peyton Manning', 'Archie Manning', 'Eli Manning', 'Shaquille O\'Neal', 'Zion Williamson'];
  const denyTok = new Set(DENY.flatMap((d) => d.split(/\s+/)).map((t) => t.toLowerCase()));
  // capitalised pairs used anywhere in the bundle's registries (people named in them included)
  const pairs = new Set();
  const dirs = readdirSync(ROOT, { withFileTypes: true }).filter((d) => d.isDirectory() && d.name !== '.git');
  const files = [];
  for (const d of dirs) {
    const r = join(ROOT, d.name, 'registry');
    if (existsSync(r)) for (const f of readdirSync(r)) if (f.endsWith('.json') && d.name !== 'npcs') files.push(join(r, f));
  }
  if (existsSync(join(ROOT, 'parishes/authored/landmarks.json'))) files.push(join(ROOT, 'parishes/authored/landmarks.json'));
  for (const f of files) {
    const t = readFileSync(f, 'utf8');
    for (const m of t.matchAll(/\b([A-Z][a-z]+)\s+([A-Z][a-z]+)\b/g)) pairs.add(m[1] + ' ' + m[2]);
  }
  const TITLES = { mentor: 'Mentor', 'k12-guide': 'Guide', ranger: 'Ranger', pilot: 'Pilot', host: 'Host' };
  const words = new Set(reg.name_words);
  const shape = [], deny = [], inReg = [];
  for (const x of npcs) {
    const m = /^([A-Z][a-z]+) ([A-Z][a-z]+)$/.exec(x.name);
    if (!m || m[1] !== TITLES[x.role] || !words.has(m[2]) || x.name_provenance !== 'AUTHORED') shape.push(`${x.id}: ${x.name}`);
    if (DENY.some((d) => x.name.includes(d)) || (m && denyTok.has(m[2].toLowerCase()))) deny.push(`${x.id}: ${x.name}`);
    if (pairs.has(x.name)) inReg.push(`${x.id}: ${x.name}`);
  }
  ok('names: every name is "<role title> <AUTHORED word>" from name_words', shape.length === 0, shape);
  ok(`names: no name or name word on the ${DENY.length}-name prominent-person denylist`, deny.length === 0, deny);
  ok(`names: no NPC name equals any of ${pairs.size} capitalised pairs in ${files.length} registries`, inReg.length === 0, inReg);
  const wordPeople = reg.name_words.filter((w) => [...pairs].some((p) => p.split(' ')[0] === w && DENY.some((d) => d.startsWith(w + ' '))));
  ok('names: no name word is the given name of a denylisted person', wordPeople.length === 0, wordPeople);
}

// --------------------------------------------------------------- places --
{
  const ids = new Map(reg.places.map((p) => [p.id, p]));
  const missing = [], wrongParish = [];
  let realSet = null;
  if (reg.places_status !== 'STUB') {
    realSet = new Map();
    const lay = readJSON('layers/registry/layers.json');
    const par = readJSON('parishes/registry/parishes.json');
    for (const q of lay.parishes) {
      for (const st of q.stations) realSet.set(st.id, st.world_m);
      for (const l of q.landmarks) {
        const pl = par.parishes[q.fips].landmarks.find((m) => m.name === l.name);
        realSet.set(`${q.fips}-lm-${l.id}`, pl ? pl.world_m : null);
      }
    }
    ok('places: parish list = parishes.json selection.selected',
       JSON.stringify(reg.parishes.map((p) => p.fips)) === JSON.stringify(par.selection.selected));
    const badXY = reg.places.filter((p) => !realSet.has(p.id) || JSON.stringify(realSet.get(p.id)) !== JSON.stringify(p.world_m)).map((p) => p.id);
    ok(`places: all ${reg.places.length} places exist in LAYERS/PARISH with identical world_m`, badXY.length === 0, badXY);
    const tsk = (x) => reg.places.find((p) => p.id === x.home.place);
    const badHost = npcs.filter((x) => x.role === 'host').filter((x) => { const h = tsk(x); return !h || h.layer !== 'task' || h.ref_id !== x.points_to.id; }).map((x) => x.id);
    ok('places: every host stands at the task station it points to', badHost.length === 0, badHost);
    const badK = npcs.filter((x) => x.role === 'k12-guide').filter((x) => { const h = tsk(x), g = reg.places.find((p) => p.id === x.guide_to);
      return !h || h.layer !== 'k12-unit' || !g || (g.layer === 'lesson' && g.ref_id !== x.points_to.id); }).map((x) => x.id);
    ok('places: K-12 guides stand at k12-unit stations and lead to their lesson station', badK.length === 0, badK);
  }
  for (const x of npcs) {
    for (const pid of [x.home.place, x.guide_to]) {
      const p = ids.get(pid);
      if (!p || (realSet && !realSet.has(pid)) || (!realSet && p.status !== 'STUB')) missing.push(`${x.id}: ${pid}`);
      else if (p.parish !== x.parish) wrongParish.push(`${x.id}: ${pid}`);
    }
  }
  ok(`places: every home and guide_to place exists (${reg.places_status})`, missing.length === 0, missing);
  ok('places: every place is in the NPC\'s own parish', wrongParish.length === 0, wrongParish);
  const parishFips = new Set(reg.parishes.map((p) => p.fips));
  ok('places: every NPC parish is a listed parish', npcs.every((x) => parishFips.has(x.parish)));
  if (reg.places_status === 'STUB') {
    ok('places: STUB mode is Orleans 22071 and says STUB on its face',
       reg.parishes.length === 1 && reg.parishes[0].fips === '22071' && reg.parishes[0].status === 'STUB'
       && /STUB/.test(reg.places_note));
  }
}

// ------------------------------------------------- pointers + looks ------
{
  const les = readJSON('lessons/registry/lessons.json').lessons;
  const tids = new Set(readJSON('tasks/registry/tasks.json').tasks.map((t) => t.id));
  const badPt = npcs.filter((x) => !((x.points_to.kind === 'lesson' && x.points_to.id in les)
    || (x.points_to.kind === 'task' && tids.has(x.points_to.id)))).map((x) => x.id);
  ok('points_to: every NPC points to a real lesson or task', badPt.length === 0, badPt);
  const av = readJSON('avatars/registry/avatars.json');
  const opts = Object.fromEntries(av.sections.map((s) => [s.id, new Set(s.options.map((o) => o.id))]));
  const badCfg = [];
  for (const x of npcs) {
    const cfg = x.appearance.cfg;
    for (const s of Object.keys(opts)) if (!(s in cfg) || !opts[s].has(cfg[s])) badCfg.push(`${x.id}: ${s}=${cfg[s]}`);
    for (const k of Object.keys(cfg)) if (!(k in opts)) badCfg.push(`${x.id}: unknown section ${k}`);
  }
  ok(`looks: every appearance cfg is ${Object.keys(opts).length} valid avatars/ locker options`, badCfg.length === 0, badCfg);
  const badProxy = [];
  for (const x of npcs) for (const p of ['torso', 'legs', 'head', 'hat']) {
    const pr = x.appearance.proxy[p];
    if (!pr || resolvePath(pr.source) !== pr.hex) badProxy.push(`${x.id}: ${p}`);
  }
  ok('looks: every proxy colour is read verbatim from avatars/ options', badProxy.length === 0, badProxy);
}

// ------------------------------------------------------------ npc_data ---
{
  const f = reg.parishes[0].fips;
  const py = `import sys, json; sys.path.insert(0, ${JSON.stringify(join(ROOT, 'web'))}); from npckit import npc_data, NPCKitError
d = npc_data(${JSON.stringify(f)})
try:
    npc_data('00000'); bad = 'no error'
except NPCKitError as e:
    bad = str(e)
print(json.dumps({'n': len(d['npcs']), 'p': sorted(d['places']), 'bad': bad}))`;
  const out = JSON.parse(execFileSync('python3', ['-c', py], { encoding: 'utf8' }));
  const want = npcs.filter((x) => x.parish === f);
  const needP = [...new Set(want.flatMap((x) => [x.home.place, x.guide_to]))];
  ok(`npc_data(${f}): ${out.n} NPCs = registry rows for that parish, every home place included`,
     out.n === want.length && needP.every((p) => out.p.includes(p)));
  ok('npc_data: unknown parish fails by name', /parish 00000 is not in npcs\/registry/.test(out.bad), [out.bad]);
}

// ----------------------------------------------------------------- kit ---
const kitSrc = execFileSync('python3', [join(ROOT, 'web/npckit.py'), '--emit'], { encoding: 'utf8' });
const kitCss = execFileSync('python3', [join(ROOT, 'web/npckit.py'), '--emit-css'], { encoding: 'utf8' });
const tmp = mkdtempSync(join(tmpdir(), 'npckit-'));
writeFileSync(join(tmp, 'kit.mjs'), kitSrc);
const K = await import(pathToFileURL(join(tmp, 'kit.mjs')).href);

// state machine
{
  const base = { dist: 10, talking: false, following: false, arrived: false, scheduled: 'wander', greetRadius: 4 };
  const T = [
    ['idle', {}, 'wander', 'schedule wander -> wander'],
    ['wander', { scheduled: 'idle' }, 'idle', 'schedule idle -> idle'],
    ['wander', { dist: 3 }, 'greet', 'player near -> greet'],
    ['greet', { dist: 9 }, 'wander', 'player leaves -> schedule'],
    ['greet', { talking: true }, 'talk', 'dialogue open -> talk'],
    ['talk', { talking: true, dist: 50 }, 'talk', 'talk holds while open'],
    ['talk', { following: true }, 'follow', 'take me there -> follow'],
    ['follow', { following: true, dist: 1 }, 'follow', 'follow ignores greet until arrival'],
    ['follow', { following: true, arrived: true }, 'greet', 'arrival -> greet'],
    ['talk', { dist: 2 }, 'greet', 'closed near -> greet'],
  ];
  const wrong = T.filter(([s, d, want]) => K.nextState(s, { ...base, ...d }) !== want).map((t) => t[3]);
  ok(`state: ${T.length} transitions of idle/wander/greet/talk/follow`, wrong.length === 0, wrong);
  let threw = false; try { K.nextState('dance', base); } catch (e) { threw = /unknown state/.test(e.message); }
  ok('state: unknown state throws by name', threw);
  const S = K.STATES.join(',');
  ok('state: STATES = idle,wander,greet,talk,follow', S === 'idle,wander,greet,talk,follow');
  const sched = npcs[0].schedule;
  let cover = true; try { for (let h = 0; h < 24; h++) K.scheduledAt(sched, h); } catch { cover = false; }
  ok('state: every NPC schedule covers all 24 game hours', cover && npcs.every((x) => {
    try { for (let h = 0; h < 24; h++) K.scheduledAt(x.schedule, h); return true; } catch { return false; } }));
}

// steering
{
  const o = { maxSpeed: 1.2, slowRadius: 1.5, sepRadius: 1.2, avoidMargin: 0.8 };
  const a = { x: 0, z: 0, vx: 0, vz: 0 };
  const v1 = K.steer(a, { x: 10, z: 0 }, [], [], o);
  ok('steer: seeks toward target, speed clamped', v1.vx > 0 && Math.abs(v1.vz) < 1e-9 && Math.hypot(v1.vx, v1.vz) <= o.maxSpeed + 1e-9);
  const v2 = K.steer({ x: 0, z: 0, vx: 0, vz: 0 }, { x: 0.3, z: 0 }, [], [], o);
  ok('steer: arrives (slows inside slowRadius)', v2.vx > 0 && v2.vx < o.maxSpeed * 0.5);
  const v3 = K.steer(a, null, [{ x: 0.5, z: 0 }], [], o);
  ok('steer: separation pushes away from a neighbour', v3.vx < 0);
  const v4 = K.steer(a, { x: 0, z: 10 }, [], [{ x: 0.6, z: 0.2, r: 0.5 }], o);
  ok('steer: obstacle avoidance pushes off a circle', v4.vx < 0 && v4.vz > 0);
  const v5 = K.steer({ x: 0, z: 0, vx: 1, vz: 0 }, null, [], [], o);
  ok('steer: no target -> brakes to rest', Math.abs(v5.vx) < 1e-9);
}

// budget
{
  let t = 0; const now = () => t;
  const run = K.makeBudget(1.0, now);
  const items = [...Array(10).keys()], seen = [];
  const r1 = run(items, (i) => { seen.push(i); t += 0.4; });
  ok('budget: stops when the per-frame budget is spent', r1.updated === 3 && r1.skipped === 7, [JSON.stringify(r1)]);
  const r2 = run(items, (i) => { seen.push(i); t += 0.4; });
  ok('budget: resumes round-robin where it stopped', seen.slice(3).join(',') === '3,4,5' && r2.updated === 3, [seen.join(',')]);
  const run0 = K.makeBudget(0, now);
  ok('budget: always updates at least one agent', run0(items, () => { t += 5; }).updated === 1);
}

// dialogue (pure) + kit integration with real three and a fake DOM
const LBL = { talk: 'Talk', next: 'Next', prev: 'Back', close: 'Close', takeMeThere: 'Take me there',
  source: 'Source:', notCert: 'Not a certification:', pointsTo: 'Try next:', of: 'of', honesty: 'Note:',
  roles: { mentor: 'Trade mentor', 'k12-guide': 'Cognition.X K-12 guide', ranger: 'Restoration ranger', pilot: 'Boat pilot', host: 'Station host' } };
{
  const x = npcs[0];
  const m = K.dialogueModel(x, 0);
  const h = K.dialogueHTML(m, LBL, reg.honesty.scripted);
  ok('dialogue: line shown in an aria-live="polite" region', /class="npc-line" aria-live="polite"/.test(h));
  ok('dialogue: heading id matches aria-labelledby target', h.includes('<h2 id="npc-dlg-title">'));
  ok('dialogue: role shown by the caller\'s label, not the raw id', h.includes('<p class="npc-role">Trade mentor</p>'));
  let rthrew = ''; try { K.dialogueHTML(m, { ...LBL, roles: {} }, 'h'); } catch (e) { rthrew = e.message; }
  ok('dialogue: a missing role label fails by name', /labels\.roles\.mentor/.test(rthrew), [rthrew]);
  ok('dialogue: every line is shown with its source path', h.includes(x.knowledge[0].source));
  ok('dialogue: not-a-certification line and its source shown', h.includes(x.not_certification.source));
  ok('dialogue: Back disabled on first line, Next enabled',
     /data-npc="prev" disabled/.test(h) && !/data-npc="next" disabled/.test(h));
  const last = K.dialogueHTML(K.dialogueModel(x, 99), LBL, 'h');
  ok('dialogue: Next disabled on last line (index clamped)', /data-npc="next" disabled/.test(last));
  const evil = K.dialogueHTML(K.dialogueModel({ ...x, knowledge: [{ text: '<img onerror=1>', source: 's' }] }, 0), LBL, 'h');
  ok('dialogue: quote text is HTML-escaped', !evil.includes('<img') && evil.includes('&lt;img'));
  let threw = ''; try { K.dialogueHTML(m, { ...LBL, takeMeThere: undefined }, 'h'); } catch (e) { threw = e.message; }
  ok('dialogue: a missing label fails by name', /labels\.takeMeThere/.test(threw), [threw]);
  ok('dialogue: Escape closes, arrows step and clamp',
     K.dialogueKey(0, 3, 'Escape').action === 'close' && K.dialogueKey(2, 3, 'ArrowRight').idx === 2
     && K.dialogueKey(0, 3, 'ArrowLeft').idx === 0 && K.dialogueKey(0, 3, 'ArrowRight').idx === 1);
  ok('css: panel colours only via theme tokens (no hex, no rgb)', !/#[0-9a-fA-F]{3,8}\b|rgba?\(/.test(kitCss) && /var\(--panel\)/.test(kitCss) && /var\(--ink\)/.test(kitCss));
  ok('css: buttons >= 44px and a visible focus ring', /min-height:44px/.test(kitCss) && /:focus-visible\{outline:3px/.test(kitCss));
  ok('kit: no ?? defaults in the kit source', !kitSrc.includes('??'));
}
{
  // fake DOM: enough for the panel, its buttons, focus and events
  class El {
    constructor(tag) { this.tag = tag; this.attrs = {}; this.hidden = false; this._html = ''; this.children = [];
      this.handlers = {}; this.isConnected = true; this.dataset = {}; this.className = ''; this.parent = null; }
    setAttribute(k, v) { this.attrs[k] = String(v); }
    getAttribute(k) { return k in this.attrs ? this.attrs[k] : null; }
    appendChild(c) { this.children.push(c); c.parent = this; return c; }
    remove() { this.isConnected = false; }
    addEventListener(t, f) { (this.handlers[t] = this.handlers[t] || []).push(f); }
    focus() { doc.activeElement = this; }
    closest(sel) { return sel === '[data-npc]' && this.dataset.npc ? this : null; }
    set innerHTML(v) { this._html = v; this._btn = {};
      for (const m of v.matchAll(/<button type="button"(?: class="[^"]*")? data-npc="(\w+)"( disabled)?>/g)) {
        const b = new El('button'); b.dataset.npc = m[1]; b.disabled = !!m[2]; this._btn[m[1]] = b; } }
    get innerHTML() { return this._html; }
    querySelector(sel) {
      const m = /^\[data-npc="(\w+)"\](:not\(\[disabled\]\))?$/.exec(sel);
      if (!m || !this._btn) return null;
      const b = this._btn[m[1]];
      return b && !(m[2] && b.disabled) ? b : null;
    }
    fire(t, e) { for (const f of this.handlers[t] || []) f(e); }
  }
  const doc = { activeElement: null, createElement: (t) => new El(t) };
  globalThis.document = doc;
  const THREE = await import(pathToFileURL(join(ROOT, 'web/vendor/three.module.min.js')).href);
  const scene = new THREE.Scene();
  const root = new El('body');
  const opener = new El('canvas'); opener.focus();
  const here0 = npcs.filter((x) => x.parish === reg.parishes[0].fips);
  // lead NPC 0 somewhere other than its home, so "take me there" must walk
  const here = [{ ...here0[0], guide_to: here0[here0.length - 1].home.place }, ...here0.slice(1)];
  const places = {}; let k = 0;
  for (const x of here) for (const p of [x.home.place, x.guide_to]) if (!(p in places)) places[p] = { x: (k++) * 20, z: 0 };
  let went = null, talked = null, clock = 0, bodies = 0;
  const kit = K.createNPCKit({ THREE, scene, npcs: here, placeOf: (id) => places[id], labels: LBL,
    honesty: reg.honesty, panelRoot: root, onTakeMeThere: (p) => { went = p; }, onTalk: (x) => { talked = x.id; },
    makeBody: () => { bodies++; return new THREE.Group(); }, now: () => (clock += 0.3), budgetMs: 1.0 });
  const inst = scene.children.filter((c) => c.isInstancedMesh);
  ok(`spawn: ${here.length} NPCs on 4 InstancedMesh parts (one draw per part)`,
     inst.length === 4 && inst.every((m) => m.count === here.length) && kit.agents.length === here.length);
  ok('spawn: per-instance colours set from the registry proxy', inst.every((m) => m.instanceColor));
  const panel = root.children[0];
  ok('a11y: panel is role=dialog, aria-labelledby, hidden until talk',
     panel.getAttribute('role') === 'dialog' && panel.getAttribute('aria-labelledby') === 'npc-dlg-title' && panel.hidden);
  const first = kit.agents[0];
  kit.talkTo(first.id);
  ok('a11y: talk opens panel and focuses Next', !panel.hidden && doc.activeElement && doc.activeElement.dataset.npc === 'next');
  ok('quests: onTalk hook fires with the NPC', talked === first.id);
  panel.fire('keydown', { key: 'ArrowRight', preventDefault() {} });
  ok('a11y: ArrowRight steps to line 2', panel.innerHTML.includes(first.npc.knowledge[1].source));
  panel.fire('keydown', { key: 'Escape', preventDefault() {} });
  ok('a11y: Escape closes and focus returns to the opener', panel.hidden && doc.activeElement === opener);
  kit.talkTo(first.id);
  panel.fire('click', { target: panel.querySelector('[data-npc="go"]') });
  ok('take me there: closes panel, calls host with guide_to, NPC starts follow',
     panel.hidden && went === first.npc.guide_to && first.follow && doc.activeElement === opener);
  // every clock read costs 0.3 ms on the fake clock -> a 1 ms budget runs a few agents per frame
  const st = kit.update(0.016, { x: first.x + 30, z: 0 }, 12);
  ok('budget: kit update is budget-bound (updated + skipped = agents, skipped > 0)',
     st.updated + st.skipped === kit.agents.length && st.updated >= 1 && st.skipped > 0, [JSON.stringify(st)]);
  ok('detail: at most detailMax rigged bodies near the player', kit.stats().detail <= 2 && bodies <= 2);
  for (let i = 0; i < 400; i++) kit.update(0.05, { x: 1e4, z: 1e4 }, 12);
  const f = kit.agents[0];
  const gp = places[first.npc.guide_to];
  const homeP = places[first.npc.home.place];
  ok('follow: NPC walks to its guide_to place (not its home) and arrives',
     f.follow === null && Math.hypot(homeP.x - gp.x, homeP.z - gp.z) > 15
     && Math.hypot(f.x - gp.x, f.z - gp.z) < 11, [`at ${f.x.toFixed(1)},${f.z.toFixed(1)} state ${f.state} target ${gp.x},${gp.z}`]);
  kit.update(0.05, { x: kit.agents[1].x + 1, z: kit.agents[1].z }, 12);
  for (let i = 0; i < 30; i++) kit.update(0.05, { x: kit.agents[1].x + 1, z: kit.agents[1].z }, 12);
  ok('greet: NPC near the player greets', kit.agents[1].state === 'greet', [kit.agents[1].state]);
  const far = kit.agents.filter((a) => a.state === 'wander');
  const outside = far.filter((a) => Math.hypot(a.x - a.home.x, a.z - a.home.z) > 8 + 1.5);
  ok('wander: wanderers stay inside their schedule radius', outside.length === 0, outside.map((a) => a.id));
  kit.dispose();
  ok('dispose: removes instanced parts and panel', !scene.children.some((c) => c.isInstancedMesh) && !panel.isConnected);
  let threw = ''; try { K.createNPCKit({ THREE, scene, npcs: here, placeOf: () => null, labels: { talk: 'x' }, honesty: reg.honesty, panelRoot: root }); } catch (e) { threw = e.message; }
  ok('kit: missing labels fail by name', /labels\.next/.test(threw), [threw]);
}

if (bad) {
  console.log(`npcs/test: ${bad} FAILED, ${n} passed`);
  process.exit(1);
}
console.log(`npcs/test: all ${n} checks passed`);
