/* swarm/test.mjs - the Omega Swarm: node swarm/test.mjs. Prints "  ok <name>" per check and "FAIL <name>" at column 0;
 * exits 1 on any failure. Pure node, no browser. Every check re-derives its answer from the registries or from
 * independent code in this file; none trusts the builder's output on its own say-so. */
import { readFileSync, readdirSync, existsSync } from 'node:fs';
import { execFileSync } from 'node:child_process';
import { join, dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { createRouter, realHardwareSignals, SOURCES, REAL_HARDWARE_REFUSAL } from './router.mjs';
import { SwarmAudit, verifyRows, canonical, sha256 } from './audit.mjs';
import { encode, bounds, center, ring } from './geohash.mjs';
import { pointInPolygon, polygonTouchesRect, haversineKm, isSimple } from './geo.mjs';
import { createGate, gateDecision, NO_RECORD_RULE } from './gate.mjs';
import { createArena } from './dryrun.mjs';
import { canEnter, loadIndex } from '../safety_gate/gate.mjs';
import { loadArena, runOne } from '../robotics/arena/harness.mjs';
import { buildProblem, naive, greedy, optimal, hungarian, score, report } from './optimise.mjs';

const HERE = dirname(fileURLToPath(import.meta.url)), ROOT = join(HERE, '..');
const rd = (p) => JSON.parse(readFileSync(join(ROOT, p), 'utf8'));
let fails = 0, passes = 0;
const ok = (name, cond, detail) => { if (cond) { passes++; console.log('  ok ' + name); } else { fails++; console.log('FAIL ' + name + (detail ? ' :: ' + detail : '')); } };
const throws = (f) => { try { f(); return false; } catch { return true; } };
const R = rd('swarm/registry/swarm.json'), AUTH = rd('swarm/authored/swarm.json');
const GP = rd('spatial/registry/geopose.json'), HV = rd('hive/registry/hive.json'), CL = rd('robotics/claw/registry/claw.json'), RB = rd('robotics/registry/robotics.json');
const SIMS = rd('sims/registry/sims.json');
const strip = (row) => { const { seq, prev, hash, ...rest } = row; return rest; };
const noSha = (x) => ({ ...x, command: { ...x.command, sha256: null } });
const J = (x) => JSON.parse(JSON.stringify(x));

/* ---------------------------------------------------------------- the registry --- */
console.log('registry');
let cur = false; try { execFileSync('python3', [join(HERE, 'build.py'), '--check'], { stdio: 'pipe' }); cur = true; } catch { /* stale */ }
ok('registry is current: build.py --check', cur);
ok('schema swarm/1, pack smartcitix-swarm, 16-hex stamp', R.schema === 'swarm/1' && R.pack === 'smartcitix-swarm' && /^[0-9a-f]{16}$/.test(R.source_stamp));
ok('cell scheme is geohash at precision 5 with the standard alphabet', R.cell_scheme.name === 'geohash' && R.cell_scheme.precision === 5 && R.cell_scheme.alphabet === '0123456789bcdefghjkmnpqrstuvwxyz');
ok('geohash vector: (57.64911, 10.40744) -> u4pruydqqvj', encode(57.64911, 10.40744, 11) === 'u4pruydqqvj');
ok('geohash vector: (42.605, -5.603) -> ezs42', encode(42.605, -5.603, 5) === 'ezs42');
ok('geohash: every registry cell centre encodes back to the same cell', R.hives.every((h) => Object.keys(h.cells).every((c) => { const k = center(c); return encode(k.lat, k.lng, 5) === c; })));
ok('geohash: a prefix names every cell below it', encode(37.8, -122.3, 5).startsWith(encode(37.8, -122.3, 3)) && ring('9q9p3', 1).length === 9);

const camp = {}; for (const p of GP.poses) if (p.subject.kind === 'campus') camp[p.subject.id] = { lat: p.geopose.position.lat, lng: p.geopose.position.lon };
const names = Object.keys(camp).sort();
{ // single-linkage clusters recomputed here
  const par = Object.fromEntries(names.map((c) => [c, c])), f = (c) => (par[c] === c ? c : f(par[c]));
  for (const a of names) for (const b of names) if (a < b && haversineKm(camp[a], camp[b]) <= AUTH.cluster_rule.max_km) par[f(a)] = f(b);
  const g = {}; for (const c of names) (g[f(c)] ??= []).push(c);
  const derived = Object.values(g).map((x) => x.sort().join(',')).sort(), have = R.hives.map((h) => h.campuses.join(',')).sort();
  ok('hives are the single-linkage campus clusters at ' + AUTH.cluster_rule.max_km + ' km (' + R.hives.length + ' hives, 10 campuses)', JSON.stringify(derived) === JSON.stringify(have) && R.hives.length === 9);
}
ok('every campus is in exactly one hive', names.every((c) => R.hives.filter((h) => h.campuses.includes(c)).length === 1));
const hiveOfCampus = Object.fromEntries(R.hives.flatMap((h) => h.campuses.map((c) => [c, h.id])));
const allCells = R.hives.flatMap((h) => Object.keys(h.cells));
ok('no cell belongs to two hives (' + allCells.length + ' cells)', new Set(allCells).size === allCells.length && R.counts.cells === allCells.length);
const reasonsOk = new Set(['campus', 'anchor', 'restoration-site', 'ring', 'parish']);
ok('every cell carries at least one reason, all from the documented set', R.hives.every((h) => Object.values(h.cells).every((w) => w.length && w.every((x) => reasonsOk.has(x)))));
ok('every campus owns the full ring of cells around its own cell', names.every((c) => { const h = R.hives.find((x) => x.id === hiveOfCampus[c]); return ring(encode(camp[c].lat, camp[c].lng, 5), AUTH.cell_scheme.campus_ring).every((x) => x in h.cells); }));
// every hive cell covers its anchors: re-derived here from GeoPose with the JS geohash
for (const h of R.hives) {
  const mine = GP.poses.filter((p) => hiveOfCampus[p.subject.campus] === h.id);
  const bad = mine.filter((p) => !(encode(p.geopose.position.lat, p.geopose.position.lon, 5) in h.cells));
  ok('hive ' + h.id + ' covers all ' + mine.length + ' of its campus, anchor and site poses', mine.length > 0 && bad.length === 0, bad.map((p) => p.subject.ref).join(','));
}
ok('coverage lists all ' + GP.poses.length + ' GeoPose poses once, each with the cell the JS geohash gives', R.coverage.length === GP.poses.length && new Set(R.coverage.map((c) => c.ref)).size === GP.poses.length
  && GP.poses.every((p) => { const c = R.coverage.find((x) => x.ref === p.subject.ref); return c && c.cell === encode(p.geopose.position.lat, p.geopose.position.lon, 5) && c.hive === hiveOfCampus[p.subject.campus]; }));
ok('the unposed site is listed with GeoPose\'s own reason and has no cell', R.unposed.length === GP.unposed.length && GP.unposed.every((u) => R.unposed.some((x) => x.ref === u.subject.ref && x.why === u.why)) && !R.coverage.some((c) => R.unposed.some((u) => u.ref === c.ref)));
ok('the 10 campuses, 69 anchors and 10 posed restoration sites are all covered', ['campus', 'anchor', 'restoration-site'].map((k) => R.coverage.filter((c) => c.kind === k).length).join() === '10,69,10');

// members
console.log('members');
const hvIds = new Set(HV.agents.map((a) => a.id)), clIds = CL.agents.map((a) => a.id);
for (const h of R.hives) {
  const m = R.members.filter((x) => x.hive === h.id && x.kind === 'software');
  const n = (k) => m.filter((x) => x.role_kind === k).length;
  ok('hive ' + h.id + ' roster: 5 claw, 9 advisor, 20 crew-role (+ ' + n('npc') + ' parish guides)', n('claw') === 5 && n('advisor') === 9 && n('crew-role') === 20);
}
ok('168 parish guides in all, each an Omega Hive NPC once', R.members.filter((m) => m.role_kind === 'npc').length === 168 && new Set(R.members.filter((m) => m.role_kind === 'npc').map((m) => m.role)).size === 168 && R.members.filter((m) => m.role_kind === 'npc').every((m) => hvIds.has(m.role)));
ok('every software member is SCRIPTED and its role is a Hive or Claw agent id', R.members.filter((m) => m.kind === 'software').every((m) => m.provenance === 'SCRIPTED' && (hvIds.has(m.role) || clIds.includes(m.role))));
ok('software roles are exactly the Claw 5 + Hive advisors 9 + crew roles 20 + NPCs 168 per roster', R.counts.software === 9 * 34 + 168 && R.counts.software === R.members.filter((m) => m.kind === 'software').length);
ok('member ids are unique and every member stands in a cell its own hive owns, equal to the JS geohash of its position', new Set(R.members.map((m) => m.id)).size === R.members.length
  && R.members.every((m) => encode(m.lat, m.lon, 5) === m.cell && m.cell in R.hives.find((h) => h.id === m.hive).cells));
const bots = R.members.filter((m) => m.kind === 'robot');
ok('60 simulated robots: 2 of each of 3 embodiments on each of 10 campuses', bots.length === 60 && names.every((c) => Object.keys(RB.embodiments).every((e) => bots.filter((b) => b.campus === c && b.role === e).length === 2)));
ok('every robot is AUTHORED, simulated:true, real_hardware:false, an arena embodiment', bots.every((b) => b.provenance === 'AUTHORED' && b.simulated === true && b.real_hardware === false && b.role in RB.embodiments));
ok('every robot stands at a GeoPose pose of its own campus (a survey ROV at a restoration site where its campus has one)', bots.every((b) => {
  const p = GP.poses.find((x) => x.subject.ref === b.placed_at);
  const sites = GP.poses.filter((x) => x.subject.campus === b.campus && x.subject.kind === 'restoration-site');
  return p && p.subject.campus === b.campus && p.geopose.position.lat === b.lat && p.geopose.position.lon === b.lon && (b.role !== 'rov.survey' || !sites.length || p.subject.kind === 'restoration-site'); }));
ok('no real hardware in the registry: operators [], real_hardware_members 0, models 0', R.real_hardware.operators.length === 0 && R.counts.real_hardware_members === 0 && R.counts.models === 0 && R.counts.operators === 0);
ok('no member carries a model, endpoint, address or device field', R.members.every((m) => !Object.keys(m).some((k) => /model|llm|endpoint|address|device|host|^ip$|url|port/i.test(k))));
ok('the registry\'s refusal sentence is the one the brief names', R.real_hardware.refusal === 'real hardware needs a named human operator; none is configured' && REAL_HARDWARE_REFUSAL === R.real_hardware.refusal);
ok('honesty lines: simulation only, gate not a real-world safety system, sim-to-real gap, no learner location', /Nothing in this pack sends a command to a real robot/.test(R.honesty.simulation_only)
  && /not a real-world safety system/.test(R.honesty.gate) && /say nothing about how a physical robot/.test(R.honesty.sim_to_real) && /No learner location/.test(R.honesty.location) && /needs a named human operator/.test(R.honesty.real_hardware));

// capabilities
console.log('capabilities');
const IDX = loadIndex(ROOT);
for (const [cid, c] of Object.entries(R.capabilities).filter(([, x]) => x.kind === 'robot')) {
  const env = RB.envs[c.env];
  const seatHalls = c.gate_targets.length ? c.gate_targets : null;
  ok(cid + ' -> arena world ' + c.env + ' (robokit, embodiment ' + c.embodiment + ', gate records ' + c.gate_targets.length + ')', env && env.runner === 'robokit' && env.embodiments[0] === c.embodiment && JSON.stringify(c.seeds) === JSON.stringify(env.seeds)
    && c.levels.join() === env.curriculum.levels.map((l) => l.level).join() && (seatHalls ? seatHalls.every((t) => IDX.targets.has(t)) : c.gate_probe === 'sim:' + c.env.split('.')[1] + '@arena' && !IDX.targets.has(c.gate_probe)));
}
{
  const fd = RB.envs['world.gate-drive'].sources.find((s) => /sims\.forklift-run/.test(s));
  ok('gate-drive maps to every hall record of the forklift-run seat (derived from the arena world\'s own source)', !!fd && R.capabilities['robot.gate-drive'].gate_targets.join() === SIMS.sims['forklift-run'].halls.slice().sort().map((h) => 'sim:forklift-run@' + h).join()
    && R.capabilities['robot.gate-drive'].gate_targets.every((t) => IDX.targets.get(t).hazardous));
}
{
  const res = (ref) => { const [rel, path] = ref.split('#'); return path.split('.').reduce((n, k) => n[k], rd(rel)); };
  ok('software payload values equal the registry value at their source path', Object.values(R.capabilities).filter((c) => c.kind === 'software').every((c) => Object.values(c.payload).every((p) => JSON.stringify(res(p.source)) === JSON.stringify(p.value))));
  ok('each software capability names a role every hive has exactly once', Object.values(R.capabilities).filter((c) => c.kind === 'software').every((c) => R.hives.every((h) => R.members.filter((m) => m.hive === h.id && m.role === c.role).length === 1)));
}

/* ----------------------------------------------------------------- geometry --- */
console.log('geometry');
{
  const sq = [[0, 0], [0, 4], [4, 4], [4, 0]].map(([lat, lng]) => ({ lat, lng }));
  ok('point in polygon: inside, outside, on an edge and on a vertex', pointInPolygon({ lat: 2, lng: 2 }, sq) && !pointInPolygon({ lat: 5, lng: 2 }, sq) && pointInPolygon({ lat: 0, lng: 2 }, sq) && pointInPolygon({ lat: 4, lng: 4 }, sq));
  const L = [[0, 0], [0, 6], [2, 6], [2, 2], [6, 2], [6, 0]].map(([lat, lng]) => ({ lat, lng }));
  ok('point in polygon: a concave L-shape excludes its notch', pointInPolygon({ lat: 1, lng: 5 }, L) && !pointInPolygon({ lat: 4, lng: 4 }, L));
  const r = { s: 1, w: 1, n: 2, e: 2 };
  ok('polygon vs cell rect: contains it, inside it, crosses it with no vertex inside, and misses it', polygonTouchesRect(sq, r)
    && polygonTouchesRect([[1.2, 1.2], [1.2, 1.8], [1.8, 1.5]].map(([lat, lng]) => ({ lat, lng })), r)
    && polygonTouchesRect([[0, 1.4], [0, 1.6], [3, 1.6], [3, 1.4]].map(([lat, lng]) => ({ lat, lng })), r)
    && !polygonTouchesRect([[5, 5], [5, 6], [6, 6]].map(([lat, lng]) => ({ lat, lng })), r));
  ok('simple-polygon test accepts a square and rejects a bow-tie', isSimple(sq) && !isSimple([[0, 0], [4, 4], [0, 4], [4, 0]].map(([lat, lng]) => ({ lat, lng }))));
  ok('haversine: Oakland to Treasure Island campus matches the 9.0 km route in the geo registry', Math.abs(haversineKm(camp.oakland, camp['treasure-island']) - 9.0) < 0.1);
}

/* ------------------------------------------------------------------- router --- */
console.log('router');
const box = (lat, lng, d = 0.03) => [[lat - d, lng - d], [lat - d, lng + d], [lat + d, lng + d], [lat + d, lng - d]];
const cmd = (over = {}) => ({ schema: 'swarm-command/1', id: 'c1', capability: 'robot.litter-pickup', region: { polygon: box(camp.oakland.lat, camp.oakland.lng) }, ...over });
const inBox = (m, p) => { const lats = p.map((v) => v[0]), lngs = p.map((v) => v[1]); return m.lat >= Math.min(...lats) && m.lat <= Math.max(...lats) && m.lon >= Math.min(...lngs) && m.lon <= Math.max(...lngs); };
{
  const r = createRouter();
  const b = box(camp.oakland.lat, camp.oakland.lng), row = r.route(cmd());
  const want = bots.filter((m) => m.role === 'rover.wheeled' && inBox(m, b)).map((m) => m.id).sort();
  ok('a fence round the Oakland campus resolves the bay-area hive and exactly the rovers inside it (independent bounding-box count)', row.status === 'routed' && row.resolved.hives.join() === 'bay-area' && want.length > 0 && JSON.stringify(row.resolved.targets) === JSON.stringify(want), JSON.stringify([row.status, row.resolved.targets, want]));
  ok('resolution counts robots and software inside the fence', row.resolved.robots_in_region === bots.filter((m) => inBox(m, b)).length && row.resolved.software_in_region === R.members.filter((m) => m.kind === 'software' && inBox(m, b)).length);
  ok('every cell the fence touches is owned by the hive it names, and a touched cell is truly touched (bounds test)', row.resolved.cells.every((c) => R.hives.find((h) => h.id === 'bay-area').cells[c] && polygonTouchesRect(b.map(([lat, lng]) => ({ lat, lng })), bounds(c))));
  const c5 = encode(camp.oakland.lat, camp.oakland.lng, 5);
  const byCell = r.route(cmd({ id: 'c2', region: { cells: [c5] } }));
  ok('a cell-set region resolves that cell\'s hive and the robots standing in it', byCell.resolved.cells.join() === c5 && byCell.resolved.hives.join() === 'bay-area' && JSON.stringify(byCell.resolved.targets) === JSON.stringify(bots.filter((m) => m.role === 'rover.wheeled' && m.cell === c5).map((m) => m.id).sort()));
  const cb = bounds(c5), e = (cb.n - cb.s) * 0.1, inset = [[cb.s + e, cb.w + e], [cb.s + e, cb.e - e], [cb.n - e, cb.e - e], [cb.n - e, cb.w + e]];
  const poly = r.route(cmd({ id: 'c3', region: { polygon: inset } }));
  ok('a polygon drawn inside one cell resolves the same cell, hive and targets as the cell set', poly.resolved.cells.join() === byCell.resolved.cells.join() && poly.resolved.hives.join() === byCell.resolved.hives.join() && JSON.stringify(poly.resolved.targets) === JSON.stringify(byCell.resolved.targets));
  const pre = r.route(cmd({ id: 'c4', region: { cells: ['9q9'] } }));
  ok('a shorter cell string names every registry cell beneath it', pre.resolved.cells.length > 1 && pre.resolved.cells.every((c) => c.startsWith('9q9')) && pre.resolved.cells.length === allCells.filter((c) => c.startsWith('9q9')).length);
  const us = r.route(cmd({ id: 'c5', region: { polygon: [[24, -125], [24, -66], [49.5, -66], [49.5, -125]] } }));
  ok('a fence over the continental US reaches all 9 hives and all 20 rovers', us.resolved.hives.length === 9 && us.resolved.targets.length === 20 && us.status === 'routed' && us.results.every((x) => x.status === 'dry-run-ok'));
  const sea = r.route(cmd({ id: 'c6', region: { polygon: [[30, -60], [30, -50], [35, -50], [35, -60]] } }));
  ok('a fence over open ocean is refused: no-hive-in-region, with the reason named', sea.status === 'refused' && sea.refusal.code === 'no-hive-in-region' && sea.refusal.reason.length > 10);
  const lone = R.hives.flatMap((h) => Object.entries(h.cells).filter(([c, w]) => w.join() === 'ring' && !R.members.some((m) => m.cell === c)).map(([c]) => [h.id, c]))[0];
  const far = r.route(cmd({ id: 'c7', region: { cells: [lone[1]] } }));
  ok('a cell of a hive that holds no matching robot is refused: no-target-in-region, with the hive resolved', far.status === 'refused' && far.refusal.code === 'no-target-in-region' && far.resolved.hives.join() === lone[0] && far.resolved.cells.join() === lone[1]);
  const rot = (a, k) => a.slice(k).concat(a.slice(0, k));
  const hex = [[37.76, -122.33], [37.74, -122.25], [37.80, -122.20], [37.86, -122.24], [37.85, -122.34], [37.80, -122.30]];
  const base = r.route(cmd({ id: 'rot', region: { polygon: hex } })), v = [rot(hex, 1), rot(hex, 2), rot(hex, 4), hex.slice().reverse(), [...hex, hex[0]]].map((p) => strip(r.route(cmd({ id: 'rot', region: { polygon: p } }))));
  ok('the 6-vertex fence round both East Bay campuses reaches the bay-area hive and several cells', base.resolved.hives.join() === 'bay-area' && base.resolved.cells.length >= 8);
  ok('vertex order, start vertex and a closing vertex do not change the result', v.every((x) => canonical(noSha(x)) === canonical(noSha(strip(base)))));
  const tg = r.route(cmd({ id: 'tg', targets: [want[0]] }));
  ok('a targets list narrows to the named registry members', tg.resolved.targets.join() === want[0] && tg.results.length === 1);
}
{ // invalid commands are refused with a named code, and audited
  const r = createRouter(), bad = [
    ['not an object', 'hello', 'invalid-command'], ['array', [], 'invalid-command'], ['unknown field', cmd({ colour: 'red' }), 'invalid-command'],
    ['wrong schema', cmd({ schema: 'x' }), 'invalid-command'], ['bad id', cmd({ id: 'a b' }), 'invalid-command'], ['unknown capability', cmd({ capability: 'robot.fly' }), 'unknown-capability'],
    ['capability is __proto__', cmd({ capability: '__proto__' }), 'unknown-capability'],
    ['both polygon and cells', cmd({ region: { polygon: box(37, -122), cells: ['9q9p3'] } }), 'invalid-command'], ['two-vertex polygon', cmd({ region: { polygon: [[1, 1], [2, 2]] } }), 'invalid-command'],
    ['NaN vertex', cmd({ region: { polygon: [[1, 1], [NaN, 2], [3, 3]] } }), 'invalid-command'], ['latitude 91', cmd({ region: { polygon: [[91, 1], [2, 2], [3, 3]] } }), 'invalid-command'],
    ['bow-tie polygon', cmd({ region: { polygon: [[0, 0], [4, 4], [0, 4], [4, 0]] } }), 'invalid-command'], ['zero-area polygon', cmd({ region: { polygon: [[1, 1], [2, 2], [3, 3]] } }), 'invalid-command'],
    ['antimeridian span', cmd({ region: { polygon: [[0, -179], [0, 179], [5, 179], [5, -179]] } }), 'invalid-command'], ['not a geohash', cmd({ region: { cells: ['a1'] } }), 'invalid-command'],
    ['too many cells', cmd({ region: { cells: Array.from({ length: 300 }, (_, i) => encode(i % 80, i % 170, 4) + String(i % 10)).map((x) => x.replace(/[aoil]/g, 'b')) } }), 'invalid-command'],
    ['param not integer', cmd({ params: { level: 1.5 } }), 'invalid-command'], ['unknown param', cmd({ params: { speed: 3 } }), 'invalid-command'], ['undeclared level', cmd({ params: { level: 99 } }), 'invalid-command'],
    ['undeclared seed', cmd({ params: { seed: 9999 } }), 'invalid-command'], ['params on software', cmd({ capability: 'software.advise-visitor', params: { level: 1 } }), 'invalid-command'],
  ];
  const outs = bad.map(([n, c, code]) => [n, r.route(c), code]);
  ok('all ' + bad.length + ' malformed commands are refused with their named code (' + [...new Set(bad.map((x) => x[2]))].join(', ') + ')', outs.every(([, row, code]) => row.status === 'refused' && row.refusal.code === code), JSON.stringify(outs.filter(([, row, code]) => row.refusal?.code !== code).map(([n, row]) => [n, row.refusal?.code])));
  ok('every malformed command left an audit row and none ran a robot', r.audit.length === bad.length && r.audit.rows().every((x) => x.results.length === 0 && x.gate.consulted === 0));
}

// real hardware
console.log('real hardware');
const spy = () => {
  const events = []; const g = createGate({ root: ROOT, epochMs: R.dry_run.epoch_ms }), a = createArena({ root: ROOT, policy: 'scripted' });
  return { events, gate: { ...g, consult: (...x) => { events.push('consult:' + x[0].id + ':' + x[1]); return g.consult(...x); } }, arena: { ...a, run: (...x) => { events.push('run:' + g.actorFor(x[1]).id); return a.run(...x); } } };
};
const REAL = [
  ['mode live', { mode: 'live' }], ['mode real', { mode: 'real' }], ['mode execute', { mode: 'execute' }], ['mode DRY-RUN (wrong spelling)', { mode: 'DRY-RUN' }], ['mode null', { mode: null }], ['mode empty', { mode: '' }], ['mode true', { mode: true }], ['mode 0', { mode: 0 }],
  ['hardware real', { hardware: 'real' }], ['hardware true', { hardware: true }], ['hardware robot', { hardware: 'robot' }], ['hardware 1', { hardware: 1 }], ['hardware empty object', { hardware: {} }], ['hardware null', { hardware: null }],
  ['operator named', { operator: 'A. Person' }], ['operator empty', { operator: '' }], ['operator null', { operator: null }], ['operator object', { operator: { name: 'x', id: 7 } }],
  ['target device:', { targets: ['device:arm-1'] }], ['target robot:', { targets: ['robot:real-1'] }], ['target ip', { targets: ['192.168.1.5'] }], ['target unknown sim id', { targets: ['sim-robot:nowhere/x/rover.wheeled-9'] }], ['target number', { targets: [123] }], ['target ros2 uri', { targets: ['ros2:/cmd_vel'] }], ['target http uri', { targets: ['http://robot.local/cmd'] }],
  ['device field in region', { region: { polygon: box(37.8, -122.27), device: 'x' } }], ['ip field in params', { params: { ip: '10.0.0.7' } }], ['nested ros topic', { params: { a: { b: { ros: '/cmd_vel' } } } }],
  ['serial port field', { serial: '/dev/ttyUSB0' }], ['endpoint field', { endpoint: 'robot.local' }], ['live flag', { live: true }], ['physical flag', { physical: 1 }], ['real flag', { real: true }],
  ['real + unknown capability', { capability: 'robot.fly', mode: 'live' }], ['real + bad region', { region: 'nowhere', hardware: 'real' }], ['real + no region at all', { region: undefined, operator: 'x' }],
  ['operator named while a configured operator exists', { operator: 'alice' }, true],
];
{
  const outs = REAL.map(([n, over, withOp]) => {
    const s = spy(), reg = J(R); if (withOp) reg.real_hardware.operators = [{ name: 'alice' }];
    const r = createRouter({ registry: reg, gate: s.gate, arena: s.arena }), row = r.route(cmd({ id: 'hw', ...over }));
    return { n, row, s, r };
  });
  ok('all ' + REAL.length + ' real-hardware spellings are refused with code real-hardware', outs.every((o) => o.row.status === 'refused' && o.row.refusal.code === 'real-hardware'), JSON.stringify(outs.filter((o) => o.row.refusal?.code !== 'real-hardware').map((o) => o.n)));
  ok('every refusal carries the exact sentence: "real hardware needs a named human operator; none is configured"', outs.every((o) => o.row.refusal.reason === 'real hardware needs a named human operator; none is configured'));
  ok('every refusal names its signals, sorted', outs.every((o) => o.row.refusal.signals.length > 0 && JSON.stringify(o.row.refusal.signals) === JSON.stringify([...o.row.refusal.signals].sort())));
  ok('a refused real-hardware command consulted no gate, ran no episode and resolved no target', outs.every((o) => o.s.events.length === 0 && o.row.gate.consulted === 0 && o.row.results.length === 0 && o.row.resolved.targets.length === 0));
  ok('naming an operator opens no path: a configured operator is still refused', outs.at(-1).row.refusal?.code === 'real-hardware' && outs.at(-1).r.registry.real_hardware.operators.length === 1);
  ok('each refusal is an audit row that verifies, with real_hardware "refused" in its provenance', outs.every((o) => o.r.audit.length === 1 && o.r.audit.verify().ok && o.row.provenance.real_hardware === 'refused'));
  ok('hardware "simulated" and mode "dry-run" are the only accepted spellings', createRouter().route(cmd({ hardware: 'simulated', mode: 'dry-run' })).status === 'routed');
  ok('non-hardware commands are never refused as real hardware (no over-refusal)', ['robot.litter-pickup', 'robot.litter-sort', 'robot.rov-survey', 'software.advise-visitor'].every((c) => createRouter().route(cmd({ capability: c })).refusal?.code !== 'real-hardware'));
}
{ // property loop: every command with a marker is refused as real hardware; none without one is
  let seed = 20261022; const rnd = () => { seed = (Math.imul(seed, 1664525) + 1013904223) >>> 0; return seed / 4294967296; };
  const pick = (a) => a[Math.floor(rnd() * a.length)];
  const markers = REAL.slice(0, -1).map((x) => x[1]).filter((o) => !('region' in o) || o.region !== undefined);
  let n = 0, marked = 0, refusedHw = 0, cleanHw = 0, r = createRouter();
  for (let i = 0; i < 400; i++) {
    const c = cmd({ id: 'p' + i, capability: pick(['robot.litter-pickup', 'robot.litter-sort', 'robot.rov-survey', 'software.advise-visitor', 'software.audit-dataset']),
      region: pick([{ polygon: box(camp.oakland.lat, camp.oakland.lng) }, { cells: [encode(camp.chicago.lat, camp.chicago.lng, 5)] }, { polygon: box(10, 10) }]) });
    const k = Math.floor(rnd() * 3); const m = [];
    for (let j = 0; j < k; j++) { const mk = pick(markers); Object.assign(c, J(mk)); m.push(mk); }
    const row = r.route(c); n++;
    if (m.length) { marked++; if (row.refusal?.code === 'real-hardware') refusedHw++; } else if (row.refusal?.code === 'real-hardware') cleanHw++;
  }
  ok('property: ' + marked + ' of ' + n + ' random commands carried a real-hardware marker and all ' + refusedHw + ' were refused as such; ' + (n - marked) + ' clean ones, ' + cleanHw + ' refused as such', marked > 100 && refusedHw === marked && cleanHw === 0);
}
{ // a registry that holds a non-simulated robot refuses the command
  for (const [n, mut] of [['simulated:false', (m) => { m.simulated = false; }], ['real_hardware:true', (m) => { m.real_hardware = true; }], ['simulated missing', (m) => { delete m.simulated; }], ['real_hardware missing', (m) => { delete m.real_hardware; }]]) {
    const reg = J(R), rov = reg.members.find((m) => m.id.startsWith('sim-robot:bay-area/oakland/rover.wheeled')); mut(rov);
    const s = spy(), row = createRouter({ registry: reg, gate: s.gate, arena: s.arena }).route(cmd({ region: { polygon: [[24, -125], [24, -66], [49.5, -66], [49.5, -125]] } }));
    ok('a registry robot with ' + n + ' in the fence refuses the whole command as real hardware, nothing run', row.refusal?.code === 'real-hardware' && row.refusal.reason === REAL_HARDWARE_REFUSAL && s.events.length === 0);
  }
}

// gate
console.log('safety gate');
{
  const s = spy(), r = createRouter({ gate: s.gate, arena: s.arena });
  const row = r.route(cmd({ id: 'g1', region: { polygon: [[24, -125], [24, -66], [49.5, -66], [49.5, -125]] } }));
  const consults = s.events.filter((e) => e.startsWith('consult:')), runs = s.events.filter((e) => e.startsWith('run:'));
  ok('litter-pickup on 20 rovers: the gate was consulted once per robot (' + consults.length + ') and every robot ran (' + runs.length + ')', consults.length === 20 && runs.length === 20 && row.gate.consulted === 20);
  ok('the gate is consulted BEFORE the episode for every robot: each run is preceded by a consult for that robot\'s own actor', runs.length === 20 && s.events.every((e, i) => !e.startsWith('run:') || s.events.slice(0, i).some((p) => p.startsWith('consult:' + e.slice(4) + ':'))));
  ok('the gate has no record of the headless litter world: its own answer is unknown-target and the audit says no-record', row.gate.entries.every((e) => e.verdict === 'no-record' && e.consulted[0].reasons[0].startsWith('unknown-target')) && row.results.every((x) => x.note && x.gate_verdict === 'no-record'));
  const d = canEnter(J(Object.assign({}, { id: row.gate.entries[0].actor, tenant: 'sim', inductions: [], passed: [] })), 'sim:litter-pickup@arena', { index: IDX, now: R.dry_run.epoch_ms, asOf: R.dry_run.epoch_ms });
  ok('the router quotes the gate\'s own decision verbatim (compared with a direct canEnter call)', JSON.stringify(d.reasons) === JSON.stringify(row.gate.entries[0].consulted[0].reasons) && d.allow === row.gate.entries[0].consulted[0].allow);
}
{
  const s = spy(), r = createRouter({ gate: s.gate, arena: s.arena });
  const row = r.route(cmd({ id: 'g2', capability: 'robot.gate-drive' }));
  const halls = R.capabilities['robot.gate-drive'].gate_targets;
  ok('gate-drive (the forklift-run lane) is held by the gate: every robot refused on every hall record, no episode run', row.status === 'held' && row.results.length > 0 && row.results.every((x) => x.status === 'held-by-gate' && x.run === null) && s.events.every((e) => e.startsWith('consult:')) && !s.events.some((e) => e.startsWith('run:')));
  ok('gate-drive consults every one of the seat\'s ' + halls.length + ' hall records for each robot', s.events.length === row.results.length * halls.length && row.gate.entries.every((e) => e.consulted.length === halls.length && e.verdict === 'deny'));
  const e0 = row.gate.entries[0], d = canEnter({ id: e0.actor, tenant: 'sim', inductions: [], passed: [] }, halls[0], { index: IDX, now: R.dry_run.epoch_ms, asOf: R.dry_run.epoch_ms });
  ok('the held reasons are the gate\'s own (ppe, induction, permit, tier) and the robot actor holds no credential', JSON.stringify(e0.consulted[0].reasons) === JSON.stringify(d.reasons) && d.reasons.some((x) => /^(induction|ppe|permit|tier)/.test(x)) && s.gate.actorFor('x').inductions.length === 0 && s.gate.actorFor('x').passed.length === 0);
}
{ // a gate that says yes, no, unknown or throws
  const run = (consult, cap = 'robot.gate-drive') => { const ev = []; const a = createArena({ root: ROOT, policy: 'scripted' });
    const row = createRouter({ gate: { stamps: {}, actorFor: (id) => ({ id: 'simbot-' + id.length, tenant: 'sim', inductions: [], passed: [] }), consult }, arena: { stamp: a.stamp, run: (...x) => { ev.push('run'); return a.run(...x); } } }).route(cmd({ id: 'g3', capability: cap })); return { row, ev }; };
  const allow = (t) => ({ target: t, allow: true, via: 'credentials', code: 'allow', reasons: ['allow: test'] });
  ok('a gate that allows every record lets gate-drive run (so the hold above is the gate\'s decision, not the router\'s)', run((a, t) => allow(t)).row.status === 'routed' && run((a, t) => allow(t)).ev.length > 0);
  ok('one denying record among allowing ones still holds the robot (strictest wins)', (() => { let n = 0; const o = run((a, t) => (++n % 5 === 0 ? { target: t, allow: false, via: null, code: 'ppe', reasons: ['ppe: test'] } : allow(t))); return o.row.status === 'held' && o.ev.length === 0; })());
  ok('a gate that throws holds the robot (fail closed)', (() => { const o = run(() => { throw new Error('boom'); }); return o.row.status === 'held' && o.ev.length === 0 && o.row.gate.entries[0].consulted[0].reasons[0].startsWith('gate-error'); })());
  ok('unknown-target on a world that HAS gate records is a deny, not a no-record', (() => { const o = run((a, t) => ({ target: t, allow: false, via: null, code: 'unknown-target', reasons: ['unknown-target: test'] })); return o.row.status === 'held' && o.ev.length === 0; })());
  ok('a deny on a headless world with no record (not unknown-target) holds it', (() => { const o = run((a, t) => ({ target: t, allow: false, via: null, code: 'ppe', reasons: ['ppe: test'] }), 'robot.litter-pickup'); return o.row.status === 'held' && o.ev.length === 0; })());
  ok('software commands run no episode and ask the gate nothing (gate guards robots)', (() => { const s = spy(); const row = createRouter({ gate: s.gate, arena: s.arena }).route(cmd({ id: 'g4', capability: 'software.audit-dataset' })); return row.status === 'routed' && s.events.length === 0 && row.results.every((x) => x.kind === 'software'); })());
}
{ // the dry run is the arena's own episode
  const A = loadArena(ROOT), s = spy(), r = createRouter({ gate: s.gate, arena: s.arena });
  const row = r.route(cmd({ id: 'd1', capability: 'robot.rov-survey', params: { level: 1, seed: 5 }, region: { polygon: [[24, -125], [24, -66], [49.5, -66], [49.5, -125]] } }));
  ok('rov-survey with seed 5 on 20 simulated ROVs: every result equals an independent runOne of the arena harness', row.results.length === 20 && row.results.every((x) => {
    const env = A.reg.envs['world.rov-survey'], q = runOne(A, 'scripted', env, 1, 5).row;
    return x.run.seed === 5 && x.run.steps === q[5] && x.run.path_m === q[6] && x.run.return === q[8] && x.run.success === (q[4] === 1) && x.run.env === 'world.rov-survey'; }));
  const a = r.route(cmd({ id: 'd2', capability: 'robot.litter-pickup' })), b = createRouter().route(cmd({ id: 'd2', capability: 'robot.litter-pickup' }));
  ok('default seed is derived from command id and robot id, same every time', canonical(strip(a)) === canonical(strip(b)) && a.results.every((x) => R.capabilities['robot.litter-pickup'].seeds.includes(x.run.seed)));
}
{
  const row = createRouter().route(cmd({ id: 's1', capability: 'software.schedule-tournament', region: { polygon: [[24, -125], [24, -66], [49.5, -66], [49.5, -125]] } }));
  ok('software.schedule-tournament reaches the Scheduler in all 9 hives and quotes the Claw registry\'s own queue size ' + CL.tournament.queue_size, row.results.length === 9 && row.results.every((x) => x.result.queue_runs.value === CL.tournament.queue_size && x.role === 'claw:scheduler'));
}

// the no-record rule
console.log('no-record rule');
{
  ok('the rule is explicit: no record proceeds only in dry-run, otherwise held with "no safety record for this target: held"', NO_RECORD_RULE.proceeds_only_in === 'dry-run' && NO_RECORD_RULE.hold_reason === 'no safety record for this target: held' && Object.isFrozen(NO_RECORD_RULE));
  ok('no-record in dry-run mode proceeds', gateDecision('no-record', 'dry-run').proceed === true);
  const others = ['live', 'real', 'execute', 'hardware', 'DRY-RUN', 'dry_run', '', undefined, null, 0, true];
  ok('no-record in any other mode (' + others.length + ' spellings) holds with the named reason', others.every((m) => { const d = gateDecision('no-record', m); return d.proceed === false && d.reason === 'no safety record for this target: held'; }));
  ok('a deny holds in every mode, and an allow proceeds in dry-run', ['dry-run', 'live', undefined].every((m) => gateDecision('deny', m).proceed === false) && gateDecision('allow', 'dry-run').proceed === true);
  ok('an unknown verdict never proceeds', ['', 'maybe', undefined, null].every((v) => gateDecision(v, 'dry-run').proceed === false));
  const s = spy(), row = createRouter({ gate: s.gate, arena: s.arena }).route(cmd({ id: 'nr1' }));
  ok('a simulated no-record command runs as a dry run and the row says no-record', row.status === 'routed' && row.results.every((x) => x.gate_verdict === 'no-record' && x.run));
  const s2 = spy(), live = createRouter({ gate: s2.gate, arena: s2.arena }).route(cmd({ id: 'nr2', mode: 'live' }));
  ok('the same command in live mode is refused (real hardware) before any gate consult or run', live.status === 'refused' && live.refusal.code === 'real-hardware' && s2.events.length === 0);
  ok('the router asks gateDecision with the command\'s own mode, and has no other path that lets a no-record target run', /gateDecision\(verdict, typeof cmd\.mode === 'string' \? cmd\.mode : 'dry-run'\)/.test(readFileSync(join(HERE, 'router.mjs'), 'utf8')) && !/verdict === 'no-record'\)\s*\{?\s*run/.test(readFileSync(join(HERE, 'router.mjs'), 'utf8')));
}

// determinism and audit
console.log('audit');
{
  const seq = [cmd({ id: 'a1' }), cmd({ id: 'a2', capability: 'robot.gate-drive' }), cmd({ id: 'a3', capability: 'software.advise-visitor', region: { cells: ['dp3'] } }), cmd({ id: 'a4', mode: 'live' }), cmd({ id: 'a5', region: { polygon: [[0, 0], [0, 1], [1, 1]] } })];
  const j1 = (() => { const r = createRouter(); seq.forEach((c) => r.route(c)); return r.audit.toJSONL(); })(), j2 = (() => { const r = createRouter(); seq.forEach((c) => r.route(c)); return r.audit.toJSONL(); })();
  ok('routing is deterministic: two fresh routers give byte-identical audit logs for the same commands', j1 === j2 && j1.split('\n').length === seq.length + 1);
  const rev = (() => { const r = createRouter(); [...seq].reverse().forEach((c) => r.route(c)); return r.audit.rows().map(strip).map((x) => canonical(x)).sort(); })();
  ok('routing is order-independent: the same commands in reverse order give the same rows apart from seq, prev and hash', JSON.stringify(rev) === JSON.stringify(createRouter().audit.rows().concat((() => { const r = createRouter(); seq.forEach((c) => r.route(c)); return r.audit.rows(); })()).map(strip).map((x) => canonical(x)).sort()));
  const r = createRouter(); const rows = seq.map((c) => r.route(c));
  ok('one audit row per command, refused ones included, in order', r.audit.length === seq.length && rows.map((x) => x.command.id).join() === 'a1,a2,a3,a4,a5' && rows.map((x) => x.status).join() === 'routed,held,routed,refused,refused');
  ok('rows carry the swarm-audit/1 fields: command, status, refusal, resolved, gate, results, provenance', rows.every((x) => x.schema === 'swarm-audit/1' && ['command', 'status', 'refusal', 'resolved', 'gate', 'results', 'provenance'].every((k) => k in x)));
  ok('command.sha256 is the digest of the canonical command', rows[0].command.sha256 === sha256(canonical(seq[0])) && rows[3].command.mode === 'live');
  ok('provenance says SCRIPTED, model null, simulation only, no network, real hardware refused', rows.every((x) => x.provenance.kind === 'SCRIPTED' && x.provenance.model === null && x.provenance.simulation_only === true && x.provenance.network === false && x.provenance.real_hardware === 'refused'));
  ok('provenance pins the router source digest, the registry stamp and the gate stamps', rows.every((x) => x.provenance.router_sha16 === sha256(SOURCES.map((f) => readFileSync(join(HERE, f), 'utf8')).join('\u0000')).slice(0, 16) && x.provenance.registry_stamp === R.source_stamp && x.provenance.gate_stamps.sims === IDX.stamps.sims));
  const keys = new Set(); (function walk(o) { if (o && typeof o === 'object') for (const [k, v] of Object.entries(o)) { keys.add(k); walk(v); } })(rows);
  ok('no clock field anywhere in a row (no ts, time, date, at, created)', ![...keys].some((k) => /^(ts|time|timestamp|date|at|created|when|now)$/i.test(k)));
  ok('the chain verifies from genesis', r.audit.verify().ok && r.audit.verify(r.audit.head).ok && !r.audit.verify('0'.repeat(64)).ok);
  const parsed = r.audit.toJSONL().trim().split('\n').map((l) => JSON.parse(l));
  ok('a log written as JSONL and read back still verifies', verifyRows(parsed.map((x) => Object.freeze(x))).ok);
  const t = (f) => { const c = J(parsed); f(c); return verifyRows(c); };
  ok('tamper: an edited status, a changed target, a deleted row, a swapped pair and a dropped refusal all break the chain',
    !t((c) => { c[1].status = 'routed'; }).ok && !t((c) => { c[0].resolved.targets[0] = 'sim-robot:x'; }).ok && !t((c) => c.splice(1, 1)).ok && !t((c) => { [c[0], c[1]] = [c[1], c[0]]; }).ok && !t((c) => { c[3].refusal = null; }).ok);
  ok('tamper: a forged hash fixed up for one row still breaks the next row\'s prev', (() => { const c = J(parsed); c[0].status = 'held'; const { hash, ...rest } = c[0]; c[0].hash = sha256(c[0].prev + '\n' + canonical(rest)); return !verifyRows(c).ok; })());
  ok('audit.append refuses a body missing a required field', throws(() => new SwarmAudit().append({ command: {} })));
  ok('canonical() refuses non-finite numbers, functions and class instances', throws(() => canonical({ a: NaN })) && throws(() => canonical({ a: () => 1 })) && throws(() => canonical({ a: new Date(0) })));
}

// no network or device API
console.log('no network or device API');
{
  const files = readdirSync(HERE).filter((f) => f.endsWith('.mjs') && f !== 'test.mjs').sort();
  const code = (f, base = HERE) => readFileSync(join(base, f), 'utf8').replace(/\/\*[\s\S]*?\*\//g, '').replace(/(^|\s)\/\/.*$/gm, '$1');
  const NET = /\bfetch\s*\(|\bXMLHttpRequest\b|\bWebSocket\b|\bEventSource\b|\bnavigator\b|\bsendBeacon\b|\bchild_process\b|\bnode:(?:net|http|https|http2|dgram|dns|tls|cluster|worker_threads|inspector|vm|readline|os)\b|\brequire\s*\(|\bimport\s*\(|\bprocess\.env\b|\beval\s*\(|\bnew\s+Function\b|\bsetTimeout\b|\bsetInterval\b/;
  const NET_STRICT = /\bfetch\s*\(|\bXMLHttpRequest\b|\bWebSocket\b|\bEventSource\b|\bnavigator\b|\bsendBeacon\b|\bchild_process\b|\bnode:(?:net|http|https|http2|dgram|dns|tls|cluster|worker_threads|inspector|vm|readline|os)\b|\bimport\s*\(|\bprocess\.env\b|\bsetTimeout\b|\bsetInterval\b/;
  const CLOCK = /\bDate\.now\b|\bnew\s+Date\b|\bMath\.random\b|\bperformance\.now\b|\bhrtime\b/;
  const WRITE = /\bwriteFile(?:Sync)?\b|\bappendFile(?:Sync)?\b|\bcreateWriteStream\b|\bunlink(?:Sync)?\b|\brmSync\b|\bmkdirSync\b|\bcopyFile\b|\brename(?:Sync)?\b/;
  ok('swarm/*.mjs (' + files.length + ' files, without test): no network, child-process, timer, eval, require or dynamic-import API (and, by the import allowlist below, no serial, ROS, USB or Bluetooth library)', files.every((f) => !NET.test(code(f))), files.filter((f) => NET.test(code(f))).join());
  ok('swarm/*.mjs: no clock and no randomness (Date, Math.random, performance.now, hrtime)', files.every((f) => !CLOCK.test(code(f))), files.filter((f) => CLOCK.test(code(f))).join());
  ok('swarm/*.mjs: no file writes (the router reads registries and writes nothing)', files.every((f) => !WRITE.test(code(f))));
  const imports = (f, base = HERE) => [...code(f, base).matchAll(/(?:import|export)\s[^;]*?from\s+'([^']+)'/g)].map((m) => m[1]);
  const okImp = (s) => ['node:fs', 'node:crypto', 'node:path', 'node:url'].includes(s) || /^\.\/[a-z]+\.mjs$/.test(s) || s === '../safety_gate/gate.mjs' || s === '../robotics/arena/harness.mjs';
  ok('swarm/*.mjs import only node:fs/crypto/path/url, each other, safety_gate/gate.mjs and the arena harness', files.every((f) => imports(f).every(okImp)), files.map((f) => imports(f).filter((s) => !okImp(s)).join()).join());
  ok('node:fs is imported for readFileSync only', files.every((f) => [...code(f).matchAll(/import\s*\{([^}]*)\}\s*from\s*'node:fs'/g)].every((m) => m[1].split(',').map((x) => x.trim()).filter(Boolean).every((x) => x === 'readFileSync'))));
  ok('router: gate.mjs never calls enter(), grantOverride() or issuePermit() (it cannot mint an override or a permit)', !/\b(enter|grantOverride|issuePermit|createIssuer)\s*\(/.test(code('gate.mjs') + code('router.mjs')) && /\bcanEnter\b/.test(code('gate.mjs')));
  { // the transitive closure of what the router imports from outside swarm/
    const seen = new Set(), todo = [join(ROOT, 'safety_gate/gate.mjs'), join(ROOT, 'robotics/arena/harness.mjs')];
    while (todo.length) { const f = todo.pop(); if (seen.has(f)) continue; seen.add(f); for (const s of imports(f, '/')) if (s.startsWith('.')) todo.push(resolve(dirname(f), s)); }
    const names = [...seen].map((f) => f.slice(ROOT.length + 1)).sort();
    ok('what the router pulls in beyond swarm/ (' + names.join(', ') + ') holds no network, device, child-process or timer API either (the harness evaluates only the repo\'s own SIM_CORE and policy blocks with new Function)', [...seen].every((f) => !NET_STRICT.test(code(f, '/'))), [...seen].filter((f) => NET_STRICT.test(code(f, '/'))).join());
  }
  ok('realHardwareSignals reads only its argument (pure) and ignores non-objects', realHardwareSignals(null).length === 0 && realHardwareSignals('device:x').length === 0 && realHardwareSignals({ mode: 'dry-run' }).length === 0);
}

// the swarm-optimisation demo
console.log('swarm optimisation demo');
{
  const P = buildProblem(R), M = { naive: naive(P), greedy: greedy(P), optimal: optimal(P) };
  const valid = (pairs) => new Set(pairs.map((p) => p[0])).size === pairs.length && new Set(pairs.map((p) => p[1])).size === pairs.length && pairs.every(([i, j]) => P.cost[i][j] < Infinity);
  ok('one task slot per cell that holds a campus, anchor or site pose (' + P.tasks.length + ' tasks, ' + P.robots.length + ' robots)', P.tasks.length === new Set(R.coverage.map((c) => c.cell)).size && P.robots.length === 60);
  ok('every method returns a valid matching: each robot and task once, only eligible pairs (right embodiment, within ' + P.max_km + ' km)', Object.values(M).every(valid));
  { // Hungarian against brute force on small random matrices with forbidden pairs
    let seed = 7; const rnd = () => { seed = (Math.imul(seed, 1664525) + 1013904223) >>> 0; return seed / 4294967296; };
    const brute = (c, n, m) => { let best = [-1, Infinity]; const used = new Set(); const go = (i, cnt, km) => { if (i === n) { if (cnt > best[0] || (cnt === best[0] && km < best[1] - 1e-9)) best = [cnt, km]; return; } go(i + 1, cnt, km); for (let j = 0; j < m; j++) if (!used.has(j) && c[i][j] < Infinity) { used.add(j); go(i + 1, cnt + 1, km + c[i][j]); used.delete(j); } }; go(0, 0, 0); return best; };
    let agree = 0, total = 120;
    for (let t = 0; t < total; t++) {
      const n = 1 + Math.floor(rnd() * 6), m = 1 + Math.floor(rnd() * 6), c = Array.from({ length: n }, () => Array.from({ length: m }, () => (rnd() < 0.35 ? Infinity : Math.round(rnd() * 500) / 10)));
      const pr = hungarian(c, n, m), b = brute(c, n, m), km = pr.reduce((s, [i, j]) => s + c[i][j], 0);
      if (pr.length === b[0] && Math.abs(km - (b[0] ? b[1] : 0)) < 1e-6) agree++;
    }
    ok('Hungarian matches exhaustive search on ' + total + ' random small problems (most pairs covered, then least distance): ' + agree + ' of ' + total, agree === total);
  }
  const S = Object.fromEntries(Object.entries(M).map(([k, v]) => [k, score(P, v)]));
  ok('optimal covers at least as many tasks as greedy and naive, and for equal coverage no more distance than either', S.optimal.assigned >= S.greedy.assigned && S.optimal.assigned >= S.naive.assigned
    && (S.optimal.assigned > S.greedy.assigned || S.optimal.total_km <= S.greedy.total_km + 1e-9) && (S.optimal.assigned > S.naive.assigned || S.optimal.total_km <= S.naive.total_km + 1e-9));
  ok('measured: naive ' + S.naive.assigned + ' tasks / ' + S.naive.total_km + ' km, greedy ' + S.greedy.assigned + ' / ' + S.greedy.total_km + ' km, optimal ' + S.optimal.assigned + ' / ' + S.optimal.total_km + ' km (of ' + P.tasks.length + ' tasks)', true);
  ok('the report is deterministic and says plainly that no robot moves', canonical(report(R)) === canonical(report(R)) && /no robot moves/.test(report(R).says) && report(R).model === null && report(R).provenance === 'SCRIPTED');
}

// documentation
console.log('documentation');
{
  const doc = existsSync(join(HERE, 'README.md')) ? readFileSync(join(HERE, 'README.md'), 'utf8') : '';
  ok('swarm/README.md exists and states the real-hardware refusal sentence, the dry-run-only rule and that the gate is not a real-world safety system', doc.includes('real hardware needs a named human operator; none is configured') && /dry.run/i.test(doc) && /not a real-world safety system/i.test(doc));
  ok('swarm/README.md states the no-record rule', doc.includes('no safety record for this target: held') && /only as a dry run/i.test(doc));
  ok('swarm/README.md says SCRIPTED, no AI model, the sim-to-real gap and the cell scheme', /SCRIPTED/.test(doc) && /no AI model/i.test(doc) && /sim-to-real/i.test(doc) && /geohash/i.test(doc));
  ok('swarm/README.md names no buyer, price, partner or demand', !/\b(buyer|customer|price|pricing|licen[cs]e deal|partner(?:s|ship)?\b(?! stay)|demand)\b/i.test(doc.replace(/no buyer, price, partner or demand/gi, '')));
}
console.log(`\nswarm: ${passes} ok, ${fails} failed`);
process.exit(fails ? 1 : 0);
