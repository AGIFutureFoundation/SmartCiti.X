/* swarm/router.mjs - the geo-targeted command router of the Omega Swarm (SCRIPTED; no AI model).
 *
 * A command names a REGION (a geofence polygon or a set of geohash cells) and a CAPABILITY. The router
 *   1. refuses anything that names real hardware, a live mode, an operator or a target outside the registry;
 *   2. finds the hives whose cells the region touches and the simulated robots and SCRIPTED software roles inside it;
 *   3. sends every robot target through safety_gate/ (one pure canEnter per gate record) BEFORE its dry run, and holds
 *      the target when the gate says no;
 *   4. dry-runs what the gate lets through against the robotics arena worlds, and writes one audit row per command.
 * It has no path to a robot or a device: no network, no serial, no ROS, no clock, no randomness, no file writes. The only
 * things it imports are node:fs (to read registries), the gate, the arena harness and its own helpers.
 * Deterministic: the same command against the same registries gives the same row. */
import { readFileSync } from 'node:fs';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';
import { SwarmAudit, canonical, sha256 } from './audit.mjs';
import { CELL_RE, bounds, encode } from './geohash.mjs';
import { pointInPolygon, polygonTouchesRect, area, isSimple } from './geo.mjs';
import { createGate } from './gate.mjs';
import { createArena } from './dryrun.mjs';

const HERE = dirname(fileURLToPath(import.meta.url));
export const ROOT = join(HERE, '..');
export const REAL_HARDWARE_REFUSAL = 'real hardware needs a named human operator; none is configured';
export const SOURCES = ['router.mjs', 'geo.mjs', 'geohash.mjs', 'audit.mjs', 'gate.mjs', 'dryrun.mjs'];

const ALLOWED = new Set(['schema', 'id', 'capability', 'region', 'mode', 'params', 'hardware', 'operator', 'targets']);
const CMD_ID = /^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$/;
const DEVICE_KEY = /^(device|devices|robot_ip|ros|ros_topic|serial|port|host|hostname|ip|url|endpoint|address|hardware|real|live|operator|operators|physical|fleet_manager)$/i;
const DEVICE_SCHEME = /^(device|robot|ros2?|serial|tty|ip|tcp|udp|http|https|ws|wss|mqtt|ssh|usb|bluetooth|can|modbus|opc|rtsp|fleet):/i;
const MEMBER_ID = /^(sim-robot|sw):/;

/* every sign in a command that points at real hardware, found by walking the whole value (keys and strings) */
export function realHardwareSignals(cmd) {
  const sig = new Set(), seen = new Set();
  const walk = (v, path, depth) => {
    if (depth > 8 || (v && typeof v === 'object' && seen.has(v))) { if (depth > 8) sig.add('nesting too deep to inspect'); return; }
    if (typeof v === 'string') { if (DEVICE_SCHEME.test(v.trim())) sig.add(`device address at ${path}`); return; }
    if (!v || typeof v !== 'object') return;
    seen.add(v);
    for (const k of Array.isArray(v) ? v.keys() : Object.keys(v)) {
      const p = path + (Array.isArray(v) ? `[${k}]` : '.' + k);
      if (!Array.isArray(v) && DEVICE_KEY.test(k) && !(depth === 0 && k === 'hardware' && v[k] === 'simulated')) sig.add(`field ${p}`);
      walk(v[k], p, depth + 1);
    }
  };
  if (cmd === null || typeof cmd !== 'object') return [];
  if ('mode' in cmd && cmd.mode !== 'dry-run') sig.add(`mode ${JSON.stringify(cmd.mode)} is not dry-run`);
  walk(cmd, '$', 0);
  return [...sig].sort();
}

const isNum = (x) => typeof x === 'number' && Number.isFinite(x);
const fail = (code, detail) => ({ fail: { code, detail } });

function parseRegion(region, lim) {
  if (!region || typeof region !== 'object' || Array.isArray(region)) return fail('invalid-command', 'region must be an object with polygon or cells');
  const keys = Object.keys(region);
  if (keys.length !== 1 || !['polygon', 'cells'].includes(keys[0])) return fail('invalid-command', 'region must hold exactly one of polygon or cells');
  if (keys[0] === 'cells') {
    const c = region.cells;
    if (!Array.isArray(c) || c.length < 1 || c.length > lim.max_cells) return fail('invalid-command', `cells must be 1..${lim.max_cells} strings`);
    for (const x of c) if (typeof x !== 'string' || !CELL_RE.test(x) || x.length < lim.cell_min_length || x.length > lim.cell_max_length) return fail('invalid-command', 'a cell is not a geohash string of allowed length');
    return { region: { kind: 'cells', cells: [...new Set(c)].sort() } };
  }
  let p = region.polygon;
  if (!Array.isArray(p)) return fail('invalid-command', 'polygon must be a list of [lat, lng] pairs');
  const ring = [];
  for (const v of p) {
    if (!Array.isArray(v) || v.length !== 2 || !isNum(v[0]) || !isNum(v[1])) return fail('invalid-command', 'a polygon vertex is not a [lat, lng] pair of finite numbers');
    if (v[0] < -90 || v[0] > 90 || v[1] < -180 || v[1] > 180) return fail('invalid-command', 'a polygon vertex is out of range');
    ring.push({ lat: v[0], lng: v[1] });
  }
  if (ring.length > 1 && ring[0].lat === ring[ring.length - 1].lat && ring[0].lng === ring[ring.length - 1].lng) ring.pop();
  if (ring.length < 3 || ring.length > lim.max_vertices) return fail('invalid-command', `polygon needs 3..${lim.max_vertices} vertices`);
  const lngs = ring.map((v) => v.lng);
  if (Math.max(...lngs) - Math.min(...lngs) > 180) return fail('invalid-command', 'polygon crosses the antimeridian or spans more than 180 degrees of longitude');
  if (!(area(ring) > 0)) return fail('invalid-command', 'polygon has no area');
  if (!isSimple(ring)) return fail('invalid-command', 'polygon edges cross each other');
  return { region: { kind: 'polygon', ring } };
}

export function createRouter({ root = ROOT, registry, gate, arena, audit } = {}) {
  const reg = registry ?? JSON.parse(readFileSync(join(root, 'swarm/registry/swarm.json'), 'utf8'));
  const G = gate ?? createGate({ root, epochMs: reg.dry_run.epoch_ms });
  const AR = arena ?? createArena({ root, policy: reg.dry_run.policy });
  const log = audit ?? new SwarmAudit();
  const routerSha16 = sha256(SOURCES.map((f) => readFileSync(join(HERE, f), 'utf8')).join('\u0000')).slice(0, 16);
  const owner = new Map(), rects = new Map();
  for (const h of reg.hives) for (const c of Object.keys(h.cells)) { owner.set(c, h.id); rects.set(c, bounds(c)); }
  const members = new Map(reg.members.map((m) => [m.id, m]));
  const cellsSorted = [...owner.keys()].sort();

  const provenance = () => ({ kind: 'SCRIPTED', model: null, router_sha16: routerSha16, registry_stamp: reg.source_stamp, gate_stamps: G.stamps ?? null,
    arena_stamp: AR.stamp ?? null, simulation_only: true, real_hardware: 'refused', network: false });
  const hashCmd = (cmd) => { try { return sha256(canonical(cmd)); } catch { return 'unhashable'; } };
  const headOf = (cmd, region) => ({ id: cmd && typeof cmd === 'object' && typeof cmd.id === 'string' ? cmd.id.slice(0, 64) : null, sha256: hashCmd(cmd),
    capability: cmd && typeof cmd === 'object' && typeof cmd.capability === 'string' ? cmd.capability.slice(0, 64) : null,
    region_kind: region ? region.kind : null, region_cells: region && region.kind === 'cells' ? region.cells : null,
    mode: cmd && typeof cmd === 'object' && 'mode' in cmd ? (typeof cmd.mode === 'string' ? cmd.mode.slice(0, 32) : '(not a string)') : 'dry-run' });
  const emptyRes = { cells: [], hives: [], robots_in_region: 0, software_in_region: 0, targets: [] };
  const refuse = (cmd, region, code, reason, extra = {}, resolved = emptyRes) =>
    log.append({ command: headOf(cmd, region), status: 'refused', refusal: { code, reason, ...extra }, resolved, gate: { consulted: 0, entries: [] }, results: [], provenance: provenance() });

  function route(cmd) {
    // 1. real hardware first: it outranks every other check, so it is named even for a command that is wrong in other ways
    const signals = realHardwareSignals(cmd);
    let ids = [];
    if (cmd && typeof cmd === 'object' && Array.isArray(cmd.targets)) ids = cmd.targets.filter((t) => typeof t !== 'string' || !members.has(t));
    if (signals.length || ids.length) {
      return refuse(cmd, null, 'real-hardware', REAL_HARDWARE_REFUSAL,
        { signals: [...signals, ...ids.map((t) => `target ${JSON.stringify(typeof t === 'string' ? t.slice(0, 80) : '?')} is not a registry-simulated member`)].sort() });
    }
    // 2. shape
    if (!cmd || typeof cmd !== 'object' || Array.isArray(cmd)) return refuse(cmd, null, 'invalid-command', 'a command is an object');
    for (const k of Object.keys(cmd)) if (!ALLOWED.has(k)) return refuse(cmd, null, 'invalid-command', `unknown field ${JSON.stringify(k.slice(0, 40))}`);
    if (cmd.schema !== 'swarm-command/1') return refuse(cmd, null, 'invalid-command', 'schema must be "swarm-command/1"');
    if (typeof cmd.id !== 'string' || !CMD_ID.test(cmd.id)) return refuse(cmd, null, 'invalid-command', 'id must be 1-64 letters, digits, dot, dash or underscore');
    const cap = typeof cmd.capability === 'string' && Object.hasOwn(reg.capabilities, cmd.capability) ? reg.capabilities[cmd.capability] : null;
    if (!cap) return refuse(cmd, null, 'unknown-capability', 'capability is not in the registry');
    const pr = parseRegion(cmd.region, reg.region_limits);
    if (pr.fail) return refuse(cmd, null, pr.fail.code, pr.fail.detail);
    const region = pr.region;
    const params = cmd.params ?? {};
    if (typeof params !== 'object' || Array.isArray(params) || Object.keys(params).some((k) => !['level', 'seed'].includes(k)) || (params.level !== undefined && !Number.isInteger(params.level)) || (params.seed !== undefined && !Number.isInteger(params.seed)))
      return refuse(cmd, region, 'invalid-command', 'params may hold only integer level and seed');
    if (cap.kind === 'software' && Object.keys(params).length) return refuse(cmd, region, 'invalid-command', 'a software capability takes no params');
    if (cap.kind === 'robot' && ((params.level !== undefined && !cap.levels.includes(params.level)) || (params.seed !== undefined && !cap.seeds.includes(params.seed))))
      return refuse(cmd, region, 'invalid-command', 'level or seed is not declared for the arena world ' + cap.env);
    if (cmd.targets !== undefined && !Array.isArray(cmd.targets)) return refuse(cmd, region, 'invalid-command', 'targets must be a list of member ids');

    // 3. resolve: cells -> hives, region -> members
    const hit = cellsSorted.filter((c) => region.kind === 'polygon' ? polygonTouchesRect(region.ring, rects.get(c))
      : region.cells.some((r) => c.startsWith(r) || r.startsWith(c)));
    if (!hit.length) return refuse(cmd, region, 'no-hive-in-region', 'no hive owns a cell the region touches');
    const hives = [...new Set(hit.map((c) => owner.get(c)))].sort();
    const inRegion = (m) => region.kind === 'polygon' ? pointInPolygon({ lat: m.lat, lng: m.lon }, region.ring)
      : region.cells.some((r) => encode(m.lat, m.lon, r.length) === r);
    const inside = reg.members.filter(inRegion);
    const resolved = { cells: hit, hives, robots_in_region: inside.filter((m) => m.kind === 'robot').length, software_in_region: inside.filter((m) => m.kind === 'software').length, targets: [] };
    // defence in depth: a registry member that is not a simulated robot refuses the whole command
    const notSim = inside.filter((m) => m.kind === 'robot' && (m.simulated !== true || m.real_hardware !== false));
    if (notSim.length) return refuse(cmd, region, 'real-hardware', REAL_HARDWARE_REFUSAL, { signals: notSim.map((m) => `member ${m.id} is not marked simulated`).sort() }, resolved);

    let targets = inside.filter((m) => cap.kind === 'robot' ? m.kind === 'robot' && m.role === cap.embodiment : m.kind === 'software' && m.role === cap.role);
    if (Array.isArray(cmd.targets)) { const want = new Set(cmd.targets); targets = targets.filter((m) => want.has(m.id)); }
    targets.sort((a, b) => (a.id < b.id ? -1 : a.id > b.id ? 1 : 0));
    if (!targets.length) return refuse(cmd, region, 'no-target-in-region', `the region holds no ${cap.kind === 'robot' ? 'simulated ' + cap.embodiment : 'role ' + cap.role} the command selects`, {}, resolved);
    if (targets.length > reg.dry_run.max_targets) return refuse(cmd, region, 'too-many-targets', `${targets.length} targets exceed the limit of ${reg.dry_run.max_targets}`, {}, resolved);
    resolved.targets = targets.map((m) => m.id);

    // 4. act: the gate first for every robot, then the dry run only if the gate lets it through
    const entries = [], results = [];
    for (const t of targets) {
      if (cap.kind === 'software') {
        results.push({ target: t.id, kind: 'software', hive: t.hive, cell: t.cell, status: 'dry-run-ok', role: t.role, result: Object.fromEntries(Object.entries(cap.payload).map(([k, v]) => [k, { value: v.value, source: v.source }])) });
        continue;
      }
      const actor = G.actorFor(t.id), probe = cap.gate_targets.length ? cap.gate_targets : [cap.gate_probe];
      const consulted = [];
      for (const gid of probe) {
        try { consulted.push(G.consult(actor, gid)); }
        catch (e) { consulted.push({ target: gid, allow: false, via: null, code: 'gate-error', reasons: ['gate-error: ' + String(e && e.message).slice(0, 120)] }); }
      }
      let verdict;
      if (consulted.every((c) => c.allow === true)) verdict = 'allow';
      else if (cap.gate_targets.length === 0 && consulted.every((c) => c.code === 'unknown-target')) verdict = 'no-record';
      else verdict = 'deny';
      entries.push({ robot: t.id, actor: actor.id, verdict, consulted: consulted.map((c) => ({ target: c.target, allow: c.allow, via: c.via, reasons: [...c.reasons] })) });
      if (verdict === 'deny') {
        results.push({ target: t.id, kind: 'robot', hive: t.hive, cell: t.cell, status: 'held-by-gate', gate_verdict: verdict, run: null,
          why: 'the safety gate refused ' + consulted.filter((c) => !c.allow).length + ' of ' + consulted.length + ' record(s): ' + [...new Set(consulted.filter((c) => !c.allow).map((c) => c.code))].sort().join(', ') });
        continue;
      }
      let run;
      try { run = AR.run(cap, t.id, cmd.id, params); }
      catch (e) { results.push({ target: t.id, kind: 'robot', hive: t.hive, cell: t.cell, status: 'error', gate_verdict: verdict, run: null, why: String(e && e.message).slice(0, 160) }); continue; }
      results.push({ target: t.id, kind: 'robot', hive: t.hive, cell: t.cell, status: 'dry-run-ok', gate_verdict: verdict, run,
        ...(verdict === 'no-record' ? { note: 'the gate holds no record for this headless arena world; run as a dry run' } : {}) });
    }
    const ok = results.filter((r) => r.status === 'dry-run-ok').length, held = results.filter((r) => r.status === 'held-by-gate').length;
    const status = ok === results.length ? 'routed' : held === results.length ? 'held' : 'partial';
    return log.append({ command: headOf(cmd, region), status, refusal: null, resolved, gate: { consulted: entries.reduce((a, e) => a + e.consulted.length, 0), entries }, results, provenance: provenance() });
  }
  return Object.freeze({ route, audit: log, registry: reg, routerSha16 });
}
