/**
 * Wilds verification.
 *
 * Every claim in wilds/registry/wilds.json is recomputed from the registry
 * that owns it and the shipped registry is held to the answer: stamps match
 * the builder and the terrain core, every hall and lesson id resolves (names
 * and titles copied, not typed), a lesson only stands at a site its own hall
 * works at, everything authored lies inside its world, the trail network is
 * re-derived as the same minimum spanning tree, every cache is as far off the
 * trail as the registry says, the ground is deterministic from the seed, and
 * the provenance and honesty words are the ones the rules require.
 *
 *   node wilds/test.mjs
 *   node wilds/test.mjs --root=/tmp/copy      (mutation runs: a broken copy)
 */
import { createHash } from 'node:crypto';
import { readFileSync } from 'node:fs';
import { join, resolve, dirname } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const HERE = dirname(fileURLToPath(import.meta.url));
const hit = process.argv.slice(2).find((a) => a.startsWith('--root='));
const ROOT = resolve(hit ? hit.slice(7) : join(HERE, '..'));

let n = 0, bad = 0;
const ok = (m, c, evidence = []) => {
  if (c) { n++; console.log('  ok  ' + m); return; }
  bad++;
  console.log('FAIL  ' + m);
  for (const e of evidence.slice(0, 6)) console.log('      ' + e);
};
const readJSON = (rel) => JSON.parse(readFileSync(join(ROOT, rel), 'utf8'));
const sha16 = (rel) => createHash('sha256').update(readFileSync(join(ROOT, rel))).digest('hex').slice(0, 16);

const reg = readJSON('wilds/registry/wilds.json');
const halls = new Map(readJSON('pack/registry/halls.json').halls.map((h) => [h.slug, h]));
const lessons = readJSON('lessons/registry/lessons.json').lessons;
const campuses = readJSON('geo/registry/campuses_geo.json').campuses;
const coreSrc = readFileSync(join(ROOT, 'wilds/core.mjs'), 'utf8');
const { wildsTerrain, wildsHash } = await import(pathToFileURL(join(ROOT, 'wilds/core.mjs')).href);

/* ------------------------------------------------------------ stamps -- */
ok('[stamp] source_stamp is sha256 of wilds/build.py', reg.source_stamp === sha16('wilds/build.py'), [`have ${reg.source_stamp}`]);
ok('[stamp] core_stamp is sha256 of wilds/core.mjs', reg.core_stamp === sha16('wilds/core.mjs'), [`have ${reg.core_stamp}`]);

/* ------------------------------------------------------------ worlds -- */
const W = reg.worlds;
const ids = W.map((w) => w.id);
ok('[worlds] mountain and forest exist, at least two worlds', ids.includes('mountain') && ids.includes('forest') && W.length >= 2, ids);
ok('[worlds] world ids unique', new Set(ids).size === ids.length);
ok('[worlds] seeds are integers and unique', W.every((w) => Number.isInteger(w.seed)) && new Set(W.map((w) => w.seed)).size === W.length);
ok('[worlds] extent is many square kilometres (>= 4 km across) and a whole number of chunks',
  W.every((w) => w.extent_m >= 4000 && w.extent_m % w.chunk_m === 0 && w.chunks_across === w.extent_m / w.chunk_m),
  W.map((w) => `${w.id} ${w.extent_m}/${w.chunk_m}`));
ok('[worlds] area_km2 is derived from extent', W.every((w) => w.area_km2 === Math.round((w.extent_m / 1000) ** 2 * 10) / 10));
ok('[worlds] inspiration campus resolves in geo/registry/campuses_geo.json and its city is copied',
  W.every((w) => campuses[w.inspiration.campus] && campuses[w.inspiration.campus].city === w.inspiration.campus_city),
  W.map((w) => `${w.id} -> ${w.inspiration.campus}`));

/* ------------------------------------------------------- id resolution -- */
const hallMiss = [], lessonMiss = [], borrowed = [];
for (const w of W) for (const s of w.sites) {
  if (s.halls.length === 0) hallMiss.push(`${s.id} names no hall`);
  for (const h of s.halls) if (!halls.has(h.id) || halls.get(h.id).name !== h.name) hallMiss.push(`${s.id}: ${h.id} "${h.name}"`);
  for (const l of s.lessons) {
    const L = lessons[l.id];
    if (!L || L.title !== l.title || L.hall !== l.hall) lessonMiss.push(`${s.id}: ${l.id}`);
    else if (!s.halls.some((h) => h.id === L.hall)) borrowed.push(`${s.id}: ${l.id} belongs to ${L.hall}`);
  }
}
ok('[ids] every site hall id resolves in pack/registry/halls.json with its name copied', hallMiss.length === 0, hallMiss);
ok('[ids] every site lesson id resolves in lessons/registry/lessons.json with its title copied', lessonMiss.length === 0, lessonMiss);

/* LEARN's site walks (lessons.json spread.site_walks): each site carries
   exactly its own walk, and the map names no site the wilds lack. */
const walks = readJSON('lessons/registry/lessons.json').spread.site_walks;
const walkBad = [];
for (const w of W) for (const s of w.sites) {
  const mine = s.lessons.filter((l) => /-site-walk$/.test(l.id)).map((l) => l.id);
  if (!(s.id in walks)) walkBad.push(`${s.id}: no walk in spread.site_walks`);
  else if (mine.length !== 1 || mine[0] !== walks[s.id]) walkBad.push(`${s.id}: carries ${JSON.stringify(mine)}, expected ${walks[s.id]}`);
}
const siteSet = new Set(W.flatMap((w) => w.sites.map((s) => s.id)));
for (const k of Object.keys(walks)) if (!siteSet.has(k)) walkBad.push(`spread.site_walks names ${k}, not a wilds site`);
ok('[walks] every site carries exactly its LEARN site walk (spread.site_walks), and no walk names a missing site', walkBad.length === 0, walkBad);
ok('[ids] a lesson only stands at a site its own hall works at', borrowed.length === 0, borrowed);
const allIds = W.flatMap((w) => [...w.sites.map((s) => s.id), ...w.caches.map((c) => c.id)]);
ok('[ids] site and cache ids unique across every world (quests use them as places)', new Set(allIds).size === allIds.length);
ok('[ids] site and cache ids are kebab-case', allIds.every((i) => /^[a-z0-9]+(-[a-z0-9]+)*$/.test(i)));

/* ----------------------------------------------------------- extents -- */
const outside = [];
for (const w of W) {
  const lim = w.extent_m / 2 - w.biome.rim_width_m;
  for (const p of [{ id: 'trailhead', ...w.trailhead }, ...w.sites, ...w.caches.filter((c) => c.kind !== 'summit')]) {
    if (!(Math.abs(p.x) <= lim && Math.abs(p.z) <= lim)) outside.push(`${w.id}/${p.id} (${p.x}, ${p.z}) lim ${lim}`);
  }
}
ok('[extent] every trailhead, site and placed cache lies inside its world, clear of the rim', outside.length === 0, outside);

/* ------------------------------------------------------------ trails -- */
const dist = (a, b) => Math.hypot(a.x - b.x, a.z - b.z);
function mst(nodes) {
  const inside = new Set([nodes[0].id]), legs = [], by = new Map(nodes.map((n) => [n.id, n]));
  while (inside.size < nodes.length) {
    let best = null;
    for (const a of [...inside].sort()) for (const b of nodes) {
      if (inside.has(b.id)) continue;
      const d = dist(by.get(a), b);
      if (best === null || d < best[0] || (d === best[0] && (a < best[1] || (a === best[1] && b.id < best[2])))) best = [d, a, b.id];
    }
    inside.add(best[2]);
    legs.push({ from: best[1], to: best[2], length_m: Math.round(best[0]) });
  }
  return legs;
}
const trailBad = [];
for (const w of W) {
  const nodes = [{ id: 'trailhead', x: w.trailhead.x, z: w.trailhead.z }, ...w.sites.map((s) => ({ id: s.id, x: s.x, z: s.z }))];
  const legs = mst(nodes);
  if (JSON.stringify(legs) !== JSON.stringify(w.trails)) trailBad.push(`${w.id}: ${JSON.stringify(w.trails).slice(0, 120)}`);
  if (w.trail_length_m !== legs.reduce((a, l) => a + l.length_m, 0)) trailBad.push(`${w.id}: trail_length_m`);
}
ok('[trails] the network is the minimum spanning tree over trailhead + sites, lengths derived', trailBad.length === 0, trailBad);
const segDist = (p, a, b) => {
  const dx = b.x - a.x, dz = b.z - a.z, L2 = dx * dx + dz * dz;
  const t = L2 === 0 ? 0 : Math.max(0, Math.min(1, ((p.x - a.x) * dx + (p.z - a.z) * dz) / L2));
  return Math.hypot(p.x - (a.x + t * dx), p.z - (a.z + t * dz));
};
const nearTrail = [];
for (const w of W) {
  const pos = new Map([['trailhead', w.trailhead], ...w.sites.map((s) => [s.id, s])]);
  for (const c of w.caches.filter((k) => k.kind !== 'summit')) {
    const d = Math.min(...w.trails.map((l) => segDist(c, pos.get(l.from), pos.get(l.to))));
    if (d < reg.off_trail_m || Math.round(d) !== c.off_trail_m) nearTrail.push(`${c.id}: ${d.toFixed(0)} m (recorded ${c.off_trail_m})`);
  }
}
ok(`[caches] every placed cache is off-trail (>= off_trail_m) and its recorded distance is re-derived`, nearTrail.length === 0, nearTrail);
ok('[caches] every world hides a cache, a hidden hollow and a summit register',
  W.every((w) => ['cache', 'hollow', 'summit'].every((k) => w.caches.some((c) => c.kind === k))));

/* ------------------------------------------------------ determinism -- */
ok('[core] the terrain core uses no Math.random, Date or performance clock', !/Math\.random|Date\.|performance\./.test(coreSrc));
ok('[core] exactly one WILDS_CORE block', coreSrc.split('/* WILDS_CORE:BEGIN */').length === 2 && coreSrc.split('/* WILDS_CORE:END */').length === 2);
const probe = [];
for (let k = 0; k < 64; k++) probe.push([Math.sin(k * 12.9898) * 0.45, Math.cos(k * 78.233) * 0.45]);
const finger = (w) => { const T = wildsTerrain(w); return probe.map(([a, b]) => T.height(a * w.extent_m, b * w.extent_m).toFixed(6)).join(','); };
ok('[core] the same seed gives the same ground, twice over, in every world', W.every((w) => finger(w) === finger(JSON.parse(JSON.stringify(w)))));
ok('[core] a different seed gives different ground', W.every((w) => finger(w) !== finger({ ...w, seed: w.seed + 1 })));
ok('[core] the scatter hash is deterministic and in [0,1)', [...Array(200).keys()].every((k) => {
  const a = wildsHash(k, -k * 3, 81321, k % 5); return a === wildsHash(k, -k * 3, 81321, k % 5) && a >= 0 && a < 1;
}));
const summitBad = [], wet = [], hollowBad = [];
for (const w of W) {
  const T = wildsTerrain(w), s = T.summit(), lim = w.extent_m / 2;
  if (!(Math.abs(s.x) < lim && Math.abs(s.z) < lim) || s.h <= w.biome.water_level_m) summitBad.push(`${w.id}: summit ${JSON.stringify(s)}`);
  for (const p of [...w.sites, ...w.caches.filter((c) => c.kind === 'cache')]) {
    if (T.height(p.x, p.z) > s.h) summitBad.push(`${w.id}: ${p.id} stands higher than the summit`);
  }
  for (const p of [w.trailhead, ...w.sites]) if (T.height(p.x, p.z) <= w.biome.water_level_m + 1) wet.push(`${w.id}: ${p.id || 'trailhead'} at ${T.height(p.x, p.z).toFixed(1)} (water ${w.biome.water_level_m})`);
  for (const c of w.caches.filter((k) => k.kind === 'hollow')) {
    const drop = T.raw(c.x, c.z) - T.height(c.x, c.z);
    if (Math.abs(drop - c.hollow_depth_m) > 0.01) hollowBad.push(`${c.id}: drop ${drop.toFixed(2)}`);
  }
}
ok('[core] the summit register is the highest ground: inside the world, above water, above every site and cache', summitBad.length === 0, summitBad);
ok('[core] the trailhead and every site stand on dry ground', wet.length === 0, wet);
ok('[core] every hidden hollow is carved to its declared depth', hollowBad.length === 0, hollowBad);

/* -------------------------------------------------------- provenance -- */
ok('[provenance] terrain, sites and caches AUTHORED; trails, names, titles and the summit DERIVED',
  reg.provenance.terrain === 'AUTHORED' && reg.provenance.sites === 'AUTHORED' && reg.provenance.caches === 'AUTHORED'
  && reg.provenance.trails === 'DERIVED' && reg.provenance.summit_register === 'DERIVED');
ok('[provenance] every world and site AUTHORED; summit registers DERIVED, placed caches AUTHORED',
  W.every((w) => w.provenance === 'AUTHORED' && w.sites.every((s) => s.provenance === 'AUTHORED')
    && w.caches.every((c) => c.provenance === (c.kind === 'summit' ? 'DERIVED' : 'AUTHORED'))));
const VOCAB = new Set(['RECORDED', 'DERIVED', 'SCHEMATIC', 'AUTHORED', 'SCRIPTED']);
ok('[provenance] only the repo vocabulary is used', Object.values(reg.provenance).every((v) => VOCAB.has(v)));
ok('[honesty] every world says it is inspiration only and not real elevation',
  W.every((w) => /inspiration only/.test(w.inspiration.standing) && /not real elevation/.test(w.inspiration.standing)));
ok('[honesty] the landscape is called authored and not a survey; play never enters a completion record',
  /not a survey/.test(reg.honesty.landscape) && /never enter a completion record/.test(reg.honesty.play)
  && /unverified general practice/.test(reg.honesty.lessons));
const text = JSON.stringify(reg);
ok('[honesty] no claim of measured terrain (DEM, lidar, survey data, real elevation data)',
  !/\b(DEM|lidar|LiDAR|USGS|SRTM|survey data|real elevation data|surveyed)\b/.test(text));
ok('[honesty] no price, duration or accreditation is stated', !/(\$\d|accredit|certified|\bhours?\b|\bweeks?\b)/i.test(text));

/* ------------------------------------------------------------ counts -- */
const cnt = reg.counts;
ok('[counts] every count is re-added from the worlds',
  cnt.worlds === W.length && cnt.sites === W.reduce((a, w) => a + w.sites.length, 0)
  && cnt.caches === W.reduce((a, w) => a + w.caches.length, 0)
  && cnt.halls_linked === new Set(W.flatMap((w) => w.sites.flatMap((s) => s.halls.map((h) => h.id)))).size
  && cnt.lessons_linked === new Set(W.flatMap((w) => w.sites.flatMap((s) => s.lessons.map((l) => l.id)))).size);

console.log(bad ? `wilds: ${bad} FAILED, ${n} ok` : `wilds: all ${n} checks ok`);
process.exit(bad ? 1 : 0);
