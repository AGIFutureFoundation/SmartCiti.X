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
const PATHROLE = { responders: 'responder', relief: 'relief-coordinator', teachers: 'teacher', un: 'humanitarian-trainer' };

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
      if (typeof q.source !== 'string' || typeof q.text !== 'string') { miss.push(`${x.id}: source/text missing`); continue; }
      const isPathRole = ['responder', 'relief-coordinator', 'humanitarian-trainer'].includes(x.role);
      if (!allowed.has(q.source.split('#')[0]) && !(isPathRole && q.source.startsWith('respond/registry/respond.json#'))) foreign.push(`${x.id}: ${q.source}`);
      const v = resolvePath(q.source);
      if (typeof v !== 'string' || v !== q.text) miss.push(`${x.id}: ${q.source}`);
    }
  }
  ok(`quote: all ${checked} lines match their source field verbatim`, miss.length === 0, miss);
  ok('quote: every line comes from unions/schools/lessons/tasks/restoration (+ respond/ for responder, relief, UN-trainer roles)', foreign.length === 0, foreign);
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
  const TITLES = { mentor: 'Mentor', 'k12-guide': 'Guide', ranger: 'Ranger', pilot: 'Pilot', host: 'Host',
    responder: 'Responder', 'relief-coordinator': 'Coordinator', teacher: 'Teacher', 'humanitarian-trainer': 'Trainer' };
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
  const badAt = [], badDay = [];
  for (const x of npcs) {
    for (const sl of x.schedule) { const p = ids.get(sl.at); if (!p || p.parish !== x.parish) badAt.push(`${x.id}: ${sl.at}`); }
    const lmHere = reg.places.some((p) => p.parish === x.parish && p.kind === 'landmark');
    const wh = x.schedule.map((sl) => sl.where).join(',');
    const right = x.schedule.every((sl) => (sl.where === 'home' ? sl.at === x.home.place
      : sl.where === 'station' ? sl.at === x.guide_to
      : sl.where === 'landmark' ? (lmHere ? ids.get(sl.at) && ids.get(sl.at).kind === 'landmark' : sl.at === x.guide_to) : false));
    if (wh !== 'home,station,landmark,home,home' || !right) badDay.push(x.id);
  }
  ok('routine: every schedule place exists in the NPC\'s own parish', badAt.length === 0, badAt);
  ok('routine: every day walks home -> station (guide_to) -> landmark (when the parish has one)', badDay.length === 0, badDay);
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
    || (x.points_to.kind === 'task' && tids.has(x.points_to.id))
    || (x.points_to.kind === 'path' && PATHROLE[x.points_to.id] === x.role))).map((x) => x.id);
  ok('points_to: every NPC points to a real lesson, task or (path roles) its own path', badPt.length === 0, badPt);
  // wave 7 path roles (PATHS_CONTRACT v1): one per parish per quote path; lines == that path's quotes, in order
  const P7 = readJSON('layers/registry/paths.json');
  const badRole = [];
  for (const pp of P7.parishes) {
    for (const [pid, role] of Object.entries(PATHROLE)) {
      const here = npcs.filter((x) => x.parish === pp.fips && x.role === role);
      const path = pp.paths.find((q) => q.id === pid);
      if (here.length !== 1 || !path) { badRole.push(`${pp.fips}: ${here.length} ${role}`); continue; }
      const want = path.steps.map((st) => `${st.source}|${st.quote}`);
      const got = here[0].knowledge.slice(0, want.length).map((q) => `${q.source}|${q.text}`);
      if (JSON.stringify(got) !== JSON.stringify(want)) badRole.push(`${here[0].id}: lines are not its path's quotes`);
      if (here[0].knowledge.length < 3) badRole.push(`${here[0].id}: fewer than 3 lines`);
    }
  }
  ok(`path roles: responder, relief coordinator, teacher, humanitarian trainer - one each in all ${P7.parishes.length} parishes, lines = the path's verbatim quotes`, badRole.length === 0 && P7.parishes.length > 0, badRole);
  const unBad = npcs.filter((x) => x.role === 'humanitarian-trainer').flatMap((x) => x.knowledge)
    .filter((q) => !/^respond\/registry\/respond\.json#(competencies|scenario_frames)\[\d+\]\.(what_it_is|situation)$/.test(q.source)
      || /united nations|\bUN\b/i.test(q.text)).map((q) => q.source);
  ok('path roles: the humanitarian trainer quotes only respond/ competencies and frames, and never a UN name or course', unBad.length === 0, unBad);
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
  for (const x of npcs) for (const p of ['torso', 'legs', 'head', 'hat', 'vest']) {
    if (!(p in x.appearance.proxy)) { badProxy.push(`${x.id}: ${p} key missing`); continue; }
    const pr = x.appearance.proxy[p];
    if (pr === null && (p === 'hat' || p === 'vest')) continue;
    if (!pr || resolvePath(pr.source) !== pr.hex) badProxy.push(`${x.id}: ${p}`);
  }
  ok('looks: every proxy colour is read verbatim from avatars/ options', badProxy.length === 0, badProxy);
  // wave 6: wardrobe variety, deterministic per NPC id, registry items only
  const W = reg.wardrobe, badW = [], badPick = [], badHat = [], badScale = [];
  const pickOf = (id, sec, pool) => pool[parseInt(createHash('sha256').update(`${id}:${sec}`).digest('hex').slice(0, 8), 16) % pool.length];
  for (const [nm, gear] of [...Object.entries(W.family_gear), ...Object.entries(W.roles), ['mentor_colours', W.mentor_colours]])
    for (const [sec, pool] of Object.entries(gear)) for (const v of pool) if (!opts[sec] || !opts[sec].has(v)) badW.push(`${nm}.${sec}=${v}`);
  for (const v of [...W.hard_hats]) if (!opts.headwear.has(v)) badW.push('hard_hats ' + v);
  for (const v of [...W.facialhair]) if (!opts.facialhair.has(v)) badW.push('facialhair ' + v);
  for (const [v, t] of Object.entries(W.vest_tint)) if (!opts.vest.has(v) || !opts.topcolor.has(t)) badW.push(`vest_tint ${v}->${t}`);
  ok('looks: every wardrobe item is an existing avatars/ locker option (no invented gear)', badW.length === 0, badW);
  const secOpts = Object.fromEntries(av.sections.map((s) => [s.id, s.options.map((o) => o.id)]));
  for (const x of npcs) {
    const cfg = x.appearance.cfg;
    const gear = x.role === 'mentor' ? { ...W.family_gear[x.family], ...W.mentor_colours } : W.roles[x.role];
    if (!gear) { badPick.push(`${x.id}: no wardrobe for ${x.role}/${x.family}`); continue; }
    for (const [sec, pool] of Object.entries(gear)) if (cfg[sec] !== pickOf(x.id, sec, pool)) badPick.push(`${x.id}: ${sec}=${cfg[sec]}`);
    for (const sec of W.vary) {
      const pool = sec === 'facialhair' ? W.facialhair : secOpts[sec];
      if (cfg[sec] !== pickOf(x.id, sec, pool)) badPick.push(`${x.id}: ${sec}=${cfg[sec]}`);
    }
    if ((x.role === 'mentor' || x.role === 'host') && (!W.hard_hats.includes(cfg.headwear) || cfg.vest === 'none'))
      badHat.push(`${x.id}: ${cfg.headwear}/${cfg.vest}`);
    if (x.role === 'mentor' && !secOpts.crew.includes(cfg.crew)) badHat.push(`${x.id}: crew ${cfg.crew}`);
    if ((cfg.headwear === 'none') !== (x.appearance.proxy.hat === null)) badHat.push(`${x.id}: hat proxy vs ${cfg.headwear}`);
    if ((cfg.vest in W.vest_tint) === (x.appearance.proxy.vest === null)) badHat.push(`${x.id}: vest proxy vs ${cfg.vest}`);
    const sc = x.appearance.scale;
    if (!sc || JSON.stringify(resolvePath(sc.source)) !== JSON.stringify(sc.xyz) || !sc.source.includes(`options[${secOpts.build.indexOf(cfg.build)}]`)) badScale.push(x.id);
  }
  ok('looks: every outfit + body pick = sha256("<id>:<section>") into its AUTHORED pool (deterministic per NPC id)', badPick.length === 0, badPick);
  ok('looks: mentors + hosts wear a registry hard hat and a vest/harness; mentors wear their hall crew; hat/vest proxies match', badHat.length === 0, badHat);
  ok('looks: body scale is the build option\'s registry scale (rig range)', badScale.length === 0, badScale);
  const distinct = (f) => new Set(npcs.map(f)).size;
  const nb = distinct((x) => x.appearance.cfg.build), ns = distinct((x) => x.appearance.cfg.skin);
  const nh = distinct((x) => x.appearance.scale.xyz[1]);
  const whole = distinct((x) => JSON.stringify(x.appearance.cfg));
  ok(`looks: variety - ${nb} builds, ${nh} heights, ${ns} skin tones, ${whole}/${npcs.length} distinct outfits`,
    nb >= 12 && nh === 4 && ns >= 12 && whole === npcs.length, [nb, nh, ns, whole]);
  const fams = new Set(npcs.filter((x) => x.role === 'mentor').map((x) => x.family));
  const famTools = [...fams].filter((f) => new Set(npcs.filter((x) => x.family === f).map((x) => x.appearance.cfg.tools)).size >= 1
    && npcs.filter((x) => x.family === f).every((x) => W.family_gear[f].tools.includes(x.appearance.cfg.tools)));
  ok('looks: each mentor carries a tool belt from its own trade family gear', famTools.length === fams.size, [[...fams].join(',')]);
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
    ['wander', { away: true }, 'walk', 'routine place changed -> walk'],
    ['walk', { away: false }, 'wander', 'arrived at routine place -> schedule'],
    ['walk', { away: true, dist: 2 }, 'greet', 'greet interrupts a walk'],
    ['walk', { away: true, following: true }, 'follow', 'take me there beats the routine'],
  ];
  const wrong = T.filter(([s, d, want]) => K.nextState(s, { ...base, ...d }) !== want).map((t) => t[3]);
  ok(`state: ${T.length} transitions of idle/wander/walk/greet/talk/follow`, wrong.length === 0, wrong);
  let threw = false; try { K.nextState('dance', base); } catch (e) { threw = /unknown state/.test(e.message); }
  ok('state: unknown state throws by name', threw);
  const S = K.STATES.join(',');
  ok('state: STATES = idle,wander,walk,greet,talk,follow', S === 'idle,wander,walk,greet,talk,follow');
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
// labels come from the site catalogue (npc.* keys), exactly as a page passes them
const LOC = ['en', 'ar', 'de', 'es', 'fr', 'hi', 'pt', 'zh'];

const cat = Object.fromEntries(LOC.map((l) => [l, readJSON(`i18n/locales/${l}.json`).strings]));
const trOf = (l) => (k) => { if (!(k in cat[l])) throw new Error('i18n missing ' + l + ':' + k); return cat[l][k]; };
const LBL = K.labelsFrom(trOf('en'));
{
  const bad = [];
  for (const l of LOC) { try { K.labelsFrom(trOf(l)); } catch (e) { bad.push(e.message); } }
  ok('i18n: labelsFrom(tr) builds every dialogue label + 9 role titles in all 8 locales', bad.length === 0, bad);
  const keys = execFileSync('python3', ['-c', `import sys; sys.path.insert(0, ${JSON.stringify(join(ROOT, 'web'))}); from npckit import NPC_I18N_KEYS; print('\\n'.join(NPC_I18N_KEYS))`], { encoding: 'utf8' }).trim().split('\n');
  const same = [];
  for (const l of LOC.slice(1)) for (const k of keys) if (cat[l][k] === cat.en[k] && !/^(\/|Source :)$/.test(cat[l][k])) same.push(`${l}:${k}`);
  ok(`i18n: the ${keys.length} npc.* keys are real translations (no English copies)`, keys.length === 20 && same.length === 0, same);
  const lang = LOC.filter((l) => !/[(（]/.test(cat[l]['npc.quotelang']));
  ok('i18n: every locale says quoted lines stay verbatim in their source language', lang.length === 0 && /verbatim/.test(cat.en['npc.quotelang']), lang);
  let t = ''; try { K.labelsFrom((k) => (k === 'npc.role.pilot' ? '' : cat.en[k])); } catch (e) { t = e.message; }
  ok('i18n: an empty catalogue string fails by key name', /npc\.role\.pilot/.test(t), [t]);
}
{
  const x = npcs[0];
  const m = K.dialogueModel(x, 0);
  const h = K.dialogueHTML(m, LBL, reg.honesty.scripted);
  ok('dialogue: line shown in an aria-live="polite" region', /class="npc-line" aria-live="polite"/.test(h));
  ok('dialogue: heading id matches aria-labelledby target', h.includes('<h2 id="npc-dlg-title">'));
  ok('dialogue: role shown by the catalogue label, not the raw id', h.includes('<p class="npc-role">Trade mentor</p>'));
  ok('dialogue: panel says quotes stay verbatim in their source language', h.includes('<p class="npc-lang">' + cat.en['npc.quotelang']));
  let ms = ''; try { K.dialogueModel({ ...x, knowledge: [{ text: 'a line' }] }, 0); } catch (e) { ms = e.message; }
  ok('dialogue: a line with no source fails by name (never "undefined")', /line\.source/.test(ms), [ms]);
  let es = ''; try { K.dialogueModel({ ...x, knowledge: [{ text: 'a line', source: '' }] }, 0); } catch (e) { es = e.message; }
  ok('dialogue: an empty source fails by name', /line\.source/.test(es), [es]);
  let hs = ''; try { K.dialogueHTML(m, LBL, undefined); } catch (e) { hs = e.message; }
  ok('dialogue: footer honesty text missing fails by name', /honesty\.scripted/.test(hs), [hs]);
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
  for (const x of here) for (const p of [x.home.place, x.guide_to, ...x.schedule.map((sl) => sl.at)]) if (!(p in places)) places[p] = { x: (k++) * 20, z: 0 };
  let went = null, talked = null, clock = 0, bodies = 0;
  const kit = K.createNPCKit({ THREE, scene, npcs: here, placeOf: (id) => places[id], labels: LBL,
    honesty: reg.honesty, panelRoot: root, onTakeMeThere: (p) => { went = p; }, onTalk: (x) => { talked = x.id; },
    makeBody: () => { bodies++; return new THREE.Group(); }, now: () => (clock += 0.3), budgetMs: 1.0 });
  const inst = scene.children.filter((c) => c.isInstancedMesh);
  ok(`spawn: ${here.length} NPCs on 5 InstancedMesh parts (torso, legs, head, hat, vest) (one draw per part)`,
     inst.length === 5 && inst.every((m) => m.count === here.length) && kit.agents.length === here.length);
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
  const outside = far.filter((a) => Math.hypot(a.x - a.anchor.x, a.z - a.anchor.z) > K.scheduledAt(a.npc.schedule, 12).radius_m + 2);
  ok('wander: wanderers stay inside this hour\'s routine radius', far.length > 0 && outside.length === 0, outside.map((a) => a.id));
  kit.dispose();
  ok('dispose: removes instanced parts and panel', !scene.children.some((c) => c.isInstancedMesh) && !panel.isConnected);
  let threw = ''; try { K.createNPCKit({ THREE, scene, npcs: here, placeOf: () => null, labels: { talk: 'x' }, honesty: reg.honesty, panelRoot: root }); } catch (e) { threw = e.message; }
  ok('kit: missing labels fail by name', /labels\.next/.test(threw), [threw]);
}

// ---------------------------------------- WILDS data shape (5a bug) -----
{
  // exactly what web/build_parishes.py embeds: places {id: [x, z]} (x = e, z = -n), honesty = the object
  const all = { npcs: [], places: {}, honesty: null };
  for (const p of reg.parishes) {
    const py = `import sys, json; sys.path.insert(0, ${JSON.stringify(join(ROOT, 'web'))}); from npckit import npc_data; print(json.dumps(npc_data(${JSON.stringify(p.fips)})))`;
    const d = JSON.parse(execFileSync('python3', ['-c', py], { encoding: 'utf8' }));
    all.honesty = d.honesty;
    for (const [id, pl] of Object.entries(d.places)) all.places[id] = pl.world_m ? [pl.world_m[0], -pl.world_m[1]] : [0, 0];
    all.npcs.push(...d.npcs);
  }
  const THREE = await import(pathToFileURL(join(ROOT, 'web/vendor/three.module.min.js')).href);
  const root = globalThis.document.createElement('body');
  const kit = K.createNPCKit({ THREE, scene: new THREE.Scene(), npcs: all.npcs, panelRoot: root, honesty: all.honesty,
    placeOf: (id) => (Object.hasOwn(all.places, id) ? { x: all.places[id][0], z: all.places[id][1] } : null),
    labels: LBL, now: () => 0 });
  const panel = root.children[0];
  const shown = [], undef = [];
  for (const a of kit.agents) {
    kit.talkTo(a.id);
    for (let i = 0; i < a.npc.knowledge.length; i++) {
      if (!panel.innerHTML.includes('<code>' + a.npc.knowledge[i].source + '</code>')) shown.push(`${a.id} line ${i + 1}`);
      if (/undefined|null/.test(panel.innerHTML)) undef.push(`${a.id} line ${i + 1}`);
      panel.fire('keydown', { key: 'ArrowRight', preventDefault() {} });
    }
    kit.closeDialogue();
  }
  ok(`wilds shape: all ${kit.agents.length} NPCs placed from {id: [x, z]} places`, kit.agents.length === npcs.length);
  ok('wilds shape: every line renders its own source path in the panel', shown.length === 0, shown);
  ok('wilds shape: no "undefined"/"null" anywhere in any rendered panel (5a footer bug)', undef.length === 0, undef);
  let hs = ''; try { K.createNPCKit({ THREE, scene: new THREE.Scene(), npcs: all.npcs, panelRoot: root,
    honesty: all.honesty.scripted, placeOf: () => null, labels: LBL }); } catch (e) { hs = e.message; }
  ok('wilds shape: passing honesty as a string (not the object) fails by name', /honesty\.scripted/.test(hs), [hs]);
  kit.dispose();
}

// ------------------------------------------ daily routine on sim time ----
{
  const THREE = await import(pathToFileURL(join(ROOT, 'web/vendor/three.module.min.js')).href);
  const x = npcs.find((n) => n.role === 'mentor' && n.schedule.some((sl) => sl.where === 'landmark'
    && reg.places.find((p) => p.id === sl.at).kind === 'landmark'));
  const spots = {};
  const at = (w) => x.schedule.find((sl) => sl.where === w).at;
  spots[at('home')] = { x: 0, z: 0 }; spots[at('station')] = { x: 60, z: 0 }; spots[at('landmark')] = { x: 0, z: 60 };
  const root = globalThis.document.createElement('body');
  const kit = K.createNPCKit({ THREE, scene: new THREE.Scene(), npcs: [x], panelRoot: root, honesty: reg.honesty,
    placeOf: (id) => spots[id], labels: LBL, now: () => 0 });
  const a = kit.agents[0];
  const clock = K.makeClock(5, 1 / 60);            // one game hour per simulated minute
  const seen = {}, walked = new Set();
  let prev = null;
  for (let step = 0; step < 24 * 60 * 10; step++) {  // 24 game hours at dt 0.1 s
    const h = clock.tick(0.1);
    kit.update(0.1, { x: 1e4, z: 1e4 }, h);
    walked.add(a.state);
    const slot = K.scheduledAt(x.schedule, h);
    const hr = Math.floor(h);
    if ([8, 12, 14, 18, 23].includes(hr) && prev !== hr && h - hr > 0.9) {
      const anc = a.anchors[slot.at];
      seen[hr] = { where: slot.where, d: Math.hypot(a.x - anc.x, a.z - anc.z), r: slot.radius_m };
      prev = hr;
    }
  }
  const want = { 8: 'home', 12: 'station', 14: 'landmark', 18: 'home', 23: 'home' };
  const miss = Object.entries(want).filter(([hr, w]) => !seen[hr] || seen[hr].where !== w || seen[hr].d > seen[hr].r + 2)
    .map(([hr]) => `${hr}h ${JSON.stringify(seen[hr])}`);
  ok('routine: over one simulated day the NPC is at home 8h, station 12h, landmark 14h, home 18h and 23h', miss.length === 0, miss);
  ok('routine: the NPC walks between places (walk state used) and idles at night', walked.has('walk') && walked.has('idle'), [[...walked].join(',')]);
  const c = K.makeClock(23, 1);
  ok('routine: makeClock wraps past midnight', Math.abs(c.tick(2) - 1) < 1e-9 && c.set(-1) === 23);
  // wave 6 midnight wrap: out-of-range hours map to the same slot as their wrapped hour
  const wrongSlot = [];
  for (const n of npcs) for (const [raw, w] of [[30, 6], [24, 0], [-0.5, 23.5], [47.9, 23.9], [-18, 6], [33.5, 9.5], [-11, 13]]) {
    if (K.scheduledAt(n.schedule, raw) !== K.scheduledAt(n.schedule, w)) wrongSlot.push(`${n.id} ${raw}h`);
  }
  ok('routine: scheduledAt wraps any hour at midnight (30 h = 06 h, -0.5 h = 23.5 h) for every NPC', wrongSlot.length === 0, wrongSlot.slice(0, 5));
  const back = K.makeClock(0.25, -1);
  const hs = [back.tick(0.5), back.tick(0.5), back.tick(30)];
  ok('routine: a clock running backwards across midnight stays in [0, 24)', hs.every((v) => v >= 0 && v < 24)
    && Math.abs(hs[0] - 23.75) < 1e-9 && Math.abs(hs[1] - 23.25) < 1e-9, [hs.join(',')]);
  const nf = []; for (const f of [() => K.scheduledAt(npcs[0].schedule, NaN), () => K.makeClock(0, 1).tick(NaN), () => K.makeClock(Infinity, 1)])
    { try { f(); nf.push('no throw'); } catch (e) { if (!/non-finite hour/.test(e.message)) nf.push(e.message); } }
  ok('routine: a non-finite hour fails closed by name', nf.length === 0, nf);
  kit.dispose();
}

// ------------------------------------------ idle animation timing (wave 6) ----
{
  const I = K.IDLE, ids = npcs.map((x) => x.id);
  const hash = (s) => { let h = 2166136261; for (let i = 0; i < s.length; i++) { h ^= s.charCodeAt(i); h = Math.imul(h, 16777619); } return h >>> 0; };
  const tms = npcs.map((x) => K.idleTiming(hash(x.id)));
  const tm0 = tms[0], tm0b = K.idleTiming(hash(ids[0]));
  ok('idle: timing is deterministic per NPC id and differs between NPCs',
    JSON.stringify(tm0) === JSON.stringify(tm0b) && new Set(tms.map((t) => t.breath.toFixed(4))).size > npcs.length * 0.9);
  const badB = [];
  for (const tm of tms) {
    if (!(tm.breath >= 3.2 && tm.breath <= 4.4)) badB.push('period ' + tm.breath);
    for (const t of [0.3, 1.7, 5.1]) {
      const p1 = K.idlePose(tm, t, 'idle', 0).breath, p2 = K.idlePose(tm, t + tm.breath, 'idle', 0).breath;
      if (Math.abs(p1 - p2) > 1e-9) badB.push('not periodic');
    }
    let mx = 0; for (let t = 0; t < 10; t += 0.05) mx = Math.max(mx, Math.abs(K.idlePose(tm, t, 'idle', 0).breath - 1));
    if (mx > 0.015 + 1e-12 || mx < 0.01) badB.push('amp ' + mx);
  }
  ok('idle: breathing period 3.2..4.4 s, periodic, amplitude <= 1.5 %', badB.length === 0, badB);
  const badG = [];
  for (const tm of tms.slice(0, 30)) {   // glance windows sampled at 60 fps over 120 s
    const starts = [], lens = []; let on = null, prevYaw = K.idlePose(tm, 0, 'wander', 0).yaw, maxStep = 0, prevSign = 0, alt = true;
    for (let f = 0; f <= 120 * 60; f++) {
      const t = f / 60, y = K.idlePose(tm, t, 'wander', 0).yaw;
      maxStep = Math.max(maxStep, Math.abs(y - prevYaw)); prevYaw = y;
      if (Math.abs(y) > 1e-9 && on === null) { on = t; const sg = Math.sign(y); if (prevSign && sg === prevSign) alt = false; prevSign = sg; }
      if (Math.abs(y) <= 1e-9 && on !== null) { starts.push(on); lens.push(t - on); on = null; }
      if (Math.abs(y) > 0.45 + 1e-9) badG.push('yaw ' + y);
    }
    if (starts[0] === 0) { starts.shift(); lens.shift(); }   // a glance already under way at t=0
    const gaps = starts.slice(1).map((v, i) => v - starts[i]);
    if (starts.length < 10) badG.push('few glances ' + starts.length);
    if (lens.some((l) => l > 1.4 + 1 / 30)) badG.push('long ' + Math.max(...lens));
    if (gaps.some((g) => Math.abs(g - tm.every) > 1 / 30)) badG.push('gap ' + gaps.join(','));
    if (!(tm.every >= 7 && tm.every <= 11)) badG.push('every ' + tm.every);
    if (maxStep > 0.02) badG.push('jump ' + maxStep);
    if (!alt) badG.push('sides do not alternate');
  }
  ok('idle: a glance every 7..11 s lasting <= 1.4 s, <= 0.45 rad, smooth (< 0.02 rad per frame), alternating sides', badG.length === 0, badG.slice(0, 5));
  const quiet = tms.every((tm) => [0, 0.5, 1, 2, 5, 9].every((t) => K.idlePose(tm, t, 'talk', 1).yaw === 0 && K.idlePose(tm, t, 'greet', 0).yaw === 0
    && K.idlePose(tm, t, 'idle', 3).gesture === 0 && K.idlePose(tm, t, 'wander', 3).gesture === 0));
  ok('idle: no glance while greeting/talking; no gesture unless talking', quiet);
  const g = (tt) => K.idlePose(tm0, 3, 'talk', tt).gesture;
  ok('idle: talk gesture starts at rest, peaks at half its 2.4 s cycle, repeats every 2.4 s',
    g(0) === 0 && Math.abs(g(I.gesturePeriod / 2) - I.gestureAmp) < 1e-12 && Math.abs(g(0.7) - g(0.7 + I.gesturePeriod)) < 1e-12
    && I.gesturePeriod === 2.4 && I.gestureAmp <= 0.5, [g(0), g(1.2)]);
  const THREE = await import(pathToFileURL(join(ROOT, 'web/vendor/three.module.min.js')).href);
  const root = globalThis.document.createElement('body');
  const here = npcs.slice(0, 40);
  const pl = {}; for (const x of here) { pl[x.home.place] = { x: 0, z: 0 }; for (const sl of x.schedule) pl[sl.at] = { x: 0, z: 0 }; }
  const rig = () => { const g0 = new THREE.Group(); const mk = (nm, par) => { const b = new THREE.Group(); b.name = nm; par.add(b); return b; };
    const chest = mk('chest', g0); mk('head', chest); mk('rightLowerArm', mk('rightUpperArm', chest)); return g0; };
  const kit = K.createNPCKit({ THREE, scene: new THREE.Scene(), npcs: here, panelRoot: root, honesty: reg.honesty,
    placeOf: (id) => pl[id], labels: LBL, makeBody: rig, now: () => 0, animMax: 12, detailMax: 1, detailDist: 50 });
  let st = null;
  for (let f = 0; f < 120; f++) st = kit.update(1 / 60, { x: 0.5, z: 0.5 }, 12);
  ok('idle: kit animates at most animMax (12) agents per frame', st.animated === 12, [JSON.stringify(st)]);
  const far = kit.update(1 / 60, { x: 1e4, z: 1e4 }, 12);
  ok('idle: nobody beyond animDist is animated', far.animated === 0, [JSON.stringify(far)]);
  let t2 = 0;
  const kit2 = K.createNPCKit({ THREE, scene: new THREE.Scene(), npcs: here, panelRoot: root, honesty: reg.honesty,
    placeOf: (id) => pl[id], labels: LBL, now: () => (t2 += 0.1), animBudgetMs: 0.3, budgetMs: 1.0 });
  const sb = kit2.update(1 / 60, { x: 0.5, z: 0.5 }, 12);
  ok('idle: the animation pass stops when its per-frame budget (0.3 ms) is spent', sb.animated >= 1 && sb.animated <= 3, [JSON.stringify(sb)]);
  kit2.dispose();
  kit.update(1 / 60, { x: 0.5, z: 0.5 }, 12);
  const a0 = kit.agents.find((a) => a.body);
  kit.talkTo(a0.id);
  let maxArm = 0, maxChest = 0;
  for (let f = 0; f < 150; f++) { kit.update(1 / 60, { x: a0.x, z: a0.z }, 12);
    maxArm = Math.max(maxArm, Math.abs(a0.bones.rightUpperArm.rotation.x)); maxChest = Math.max(maxChest, Math.abs(a0.bones.chest.scale.y - 1)); }
  ok('idle: a detailed body gestures with the rig\'s right arm while talking and breathes with its chest',
    a0.state === 'talk' && maxArm > 0.4 && maxArm <= 0.5 + 1e-9 && maxChest > 0.005 && maxChest <= 0.015 + 1e-9, [a0.state, maxArm, maxChest]);
  kit.closeDialogue(); kit.dispose();
  // proxies: each instance carries the build scale; the torso breathes; a bare head draws no hat, no vest draws none
  const bare = npcs.find((x) => x.appearance.proxy.hat === null), tall = npcs.find((x) => x.appearance.scale.xyz[1] > 1.1 && x.appearance.proxy.hat);
  const novest = npcs.find((x) => x.appearance.proxy.vest === null);
  const trio = [bare, tall, novest].filter(Boolean);
  const pl3 = {}; for (const x of trio) { pl3[x.home.place] = { x: 0, z: 0 }; for (const sl of x.schedule) pl3[sl.at] = { x: 0, z: 0 }; }
  const sc3 = new THREE.Scene();
  const kit3 = K.createNPCKit({ THREE, scene: sc3, npcs: trio, panelRoot: root, honesty: reg.honesty, placeOf: (id) => pl3[id], labels: LBL, now: () => 0 });
  const mesh = (k) => sc3.children.find((c) => c.isInstancedMesh && c.userData.npcPart === k);
  const M4 = new THREE.Matrix4(), P = new THREE.Vector3(), Q = new THREE.Quaternion(), S3 = new THREE.Vector3();
  const at = (k, i) => { mesh(k).getMatrixAt(i, M4); M4.decompose(P, Q, S3); return { y: P.y, s: S3.clone() }; };
  let tsy = [];
  for (let f = 0; f < 300; f++) { kit3.update(1 / 60, { x: 1, z: 1 }, 12); tsy.push(at('torso', 1).s.y); }
  const ti = trio.indexOf(tall), sxyz = tall.appearance.scale.xyz;
  const head = at('head', ti), legs = at('legs', ti);
  const pbad = [];
  if (Math.abs(legs.s.x - sxyz[0]) > 1e-6 || Math.abs(legs.s.y - sxyz[1]) > 1e-6 || Math.abs(legs.s.z - sxyz[2]) > 1e-6) pbad.push('legs scale ' + JSON.stringify(legs.s));
  if (Math.abs(head.y - 1.66 * sxyz[1]) > 1e-6) pbad.push('head y ' + head.y);
  const bre = Math.max(...tsy) / Math.min(...tsy);
  if (!(bre > 1.01 && bre < 1.031)) pbad.push('torso breath ratio ' + bre);
  if (bare && at('hat', trio.indexOf(bare)).s.length() > 1e-9) pbad.push('bare head draws a hat');
  if (novest && at('vest', trio.indexOf(novest)).s.length() > 1e-9) pbad.push('no vest draws a vest');
  ok('idle: proxy instances carry the build scale, the torso breathes, a bare head / no vest draws nothing', pbad.length === 0 && trio.length === 3, pbad);
  kit3.dispose();
}

if (bad) {
  console.log(`npcs/test: ${bad} FAILED, ${n} passed`);
  process.exit(1);
}
console.log(`npcs/test: all ${n} checks passed`);
