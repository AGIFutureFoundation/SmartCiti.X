/* swarm/optimise.mjs - a small swarm-optimisation demo: assign the simulated robots to training-task slots across the cells
 * of the whole network, three ways, and report what each measured. SCRIPTED (no model, no learning). A task slot is one
 * per cell that holds a campus, anchor or restoration-site pose; its kind is picked by the authored hash rule in the
 * registry. A robot may take a task only if the task's capability names its embodiment and the cell centre is within
 * the registry's max_km. Cost is the haversine distance in km, in a schematic simulation: nothing travels anywhere.
 *   naive   - tasks in cell order, each takes the first free eligible robot by id (first come, first served)
 *   greedy  - every eligible (robot, task) pair sorted by distance, take a pair when both are free
 *   optimal - the Hungarian method: the most tasks covered, then the least total distance (exact)
 * Deterministic: no clock, no randomness. `node swarm/optimise.mjs` prints the JSON report. */
import { readFileSync } from 'node:fs';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';
import { center } from './geohash.mjs';
import { haversineKm } from './geo.mjs';
import { sha256 } from './audit.mjs';

const ROOT = join(dirname(fileURLToPath(import.meta.url)), '..');
const BIG = 1e6;

export function buildProblem(reg) {
  const o = reg.optimise, kinds = o.task_kinds;
  const robots = reg.members.filter((m) => m.kind === 'robot').map((m) => ({ id: m.id, hive: m.hive, embodiment: m.role, lat: m.lat, lng: m.lon }))
    .sort((a, b) => (a.id < b.id ? -1 : 1));
  const tasks = [];
  for (const h of reg.hives) for (const [cell, why] of Object.entries(h.cells)) {
    if (!why.some((w) => ['campus', 'anchor', 'restoration-site'].includes(w))) continue;
    const kind = kinds[parseInt(sha256(cell + ':task').slice(0, 8), 16) % kinds.length], c = center(cell);
    tasks.push({ cell, hive: h.id, kind, embodiment: reg.capabilities[kind].embodiment, lat: c.lat, lng: c.lng });
  }
  tasks.sort((a, b) => (a.cell < b.cell ? -1 : 1));
  const cost = tasks.map((t) => robots.map((r) => {
    if (r.embodiment !== t.embodiment) return Infinity;
    const d = haversineKm(r, t);
    return d <= o.max_km ? d : Infinity;
  }));
  return { robots, tasks, cost, max_km: o.max_km };
}

export function naive(P) {
  const used = new Set(), pairs = [];
  P.tasks.forEach((t, i) => { const j = P.cost[i].findIndex((c, k) => c < Infinity && !used.has(k)); if (j >= 0) { used.add(j); pairs.push([i, j]); } });
  return pairs;
}

export function greedy(P) {
  const edges = [];
  P.cost.forEach((row, i) => row.forEach((c, j) => { if (c < Infinity) edges.push([c, P.robots[j].id, P.tasks[i].cell, i, j]); }));
  edges.sort((a, b) => a[0] - b[0] || (a[1] < b[1] ? -1 : a[1] > b[1] ? 1 : 0) || (a[2] < b[2] ? -1 : a[2] > b[2] ? 1 : 0));
  const ti = new Set(), rj = new Set(), pairs = [];
  for (const [, , , i, j] of edges) if (!ti.has(i) && !rj.has(j)) { ti.add(i); rj.add(j); pairs.push([i, j]); }
  return pairs.sort((a, b) => a[0] - b[0]);
}

/* Hungarian method (Kuhn-Munkres with potentials) on a square matrix; infeasible pairs cost BIG, which is larger than any
   sum of feasible costs, so the exact optimum covers the most tasks first and then minimises distance */
export function hungarian(cost, n, m) {
  const N = Math.max(n, m), a = Array.from({ length: N + 1 }, () => new Array(N + 1).fill(BIG));
  for (let i = 0; i < n; i++) for (let j = 0; j < m; j++) a[i + 1][j + 1] = cost[i][j] < Infinity ? cost[i][j] : BIG;
  const u = new Array(N + 1).fill(0), v = new Array(N + 1).fill(0), p = new Array(N + 1).fill(0), way = new Array(N + 1).fill(0);
  for (let i = 1; i <= N; i++) {
    p[0] = i; let j0 = 0;
    const minv = new Array(N + 1).fill(Infinity), used = new Array(N + 1).fill(false);
    do {
      used[j0] = true; const i0 = p[j0]; let delta = Infinity, j1 = 0;
      for (let j = 1; j <= N; j++) if (!used[j]) {
        const cur = a[i0][j] - u[i0] - v[j];
        if (cur < minv[j]) { minv[j] = cur; way[j] = j0; }
        if (minv[j] < delta) { delta = minv[j]; j1 = j; }
      }
      for (let j = 0; j <= N; j++) if (used[j]) { u[p[j]] += delta; v[j] -= delta; } else minv[j] -= delta;
      j0 = j1;
    } while (p[j0] !== 0);
    do { const j1 = way[j0]; p[j0] = p[j1]; j0 = j1; } while (j0);
  }
  const pairs = [];
  for (let j = 1; j <= N; j++) { const i = p[j]; if (i >= 1 && i <= n && j <= m && cost[i - 1][j - 1] < Infinity) pairs.push([i - 1, j - 1]); }
  return pairs.sort((x, y) => x[0] - y[0]);
}
export const optimal = (P) => hungarian(P.cost, P.tasks.length, P.robots.length);

export function score(P, pairs) {
  const km = pairs.reduce((s, [i, j]) => s + P.cost[i][j], 0);
  return { assigned: pairs.length, unassigned_tasks: P.tasks.length - pairs.length, total_km: Math.round(km * 1000) / 1000, mean_km: pairs.length ? Math.round(km / pairs.length * 1000) / 1000 : 0 };
}

export function report(reg) {
  const P = buildProblem(reg), by = { naive: naive(P), greedy: greedy(P), optimal: optimal(P) };
  const perKind = {};
  for (const t of P.tasks) perKind[t.kind] = (perKind[t.kind] ?? 0) + 1;
  const supply = {};
  for (const r of P.robots) supply[r.embodiment] = (supply[r.embodiment] ?? 0) + 1;
  return {
    schema: 'swarm-optimise/1', provenance: 'SCRIPTED', model: null,
    problem: { robots: P.robots.length, tasks: P.tasks.length, max_km: P.max_km, tasks_by_kind: perKind, robots_by_embodiment: supply },
    methods: Object.fromEntries(Object.entries(by).map(([k, v]) => [k, score(P, v)])),
    says: 'Distances are haversine kilometres between simulated positions; no robot moves. The number measures how well an assignment rule matches simulated robots to authored task slots, not how useful any task is or how a physical robot would perform.',
  };
}

if (process.argv[1] === fileURLToPath(import.meta.url)) {
  process.stdout.write(JSON.stringify(report(JSON.parse(readFileSync(join(ROOT, 'swarm/registry/swarm.json'), 'utf8'))), null, 1) + '\n');
}
