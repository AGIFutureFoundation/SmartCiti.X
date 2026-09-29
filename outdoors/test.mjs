#!/usr/bin/env node
// outdoors/test.mjs - the outdoors pack: spots DERIVED from AUTHORED water (re-derived here from the sources), the
// AUTHORED catalogue (rods, bait, species) and the honesty rules. "  ok <name>" per check, FAIL at column 0, exit 1.
import { readFileSync, existsSync } from 'node:fs';
import { execFileSync } from 'node:child_process';
import { wildsTerrain } from '../wilds/core.mjs';

const ROOT = new URL('..', import.meta.url).pathname;
let fails = 0, n = 0;
const ok = (c, name, info = '') => { n++; if (c) console.log('  ok ' + name); else { fails++; console.log('FAIL ' + name + (info ? ' :: ' + info : '')); } };
const J = (p) => JSON.parse(readFileSync(ROOT + p, 'utf8'));

let fresh = true; try { execFileSync('python3', ['outdoors/build.py', '--check'], { cwd: ROOT, stdio: 'pipe' }); } catch (e) { fresh = false; }
ok(fresh, 'registry: outdoors/registry/outdoors.json is current (build --check)');
const R = J('outdoors/registry/outdoors.json');
ok(/^[0-9a-f]{16}$/.test(R.source_stamp) && R.source_stamp_sha256.startsWith(R.source_stamp), 'registry: sha256 source_stamp');

// spots: several per world, each with a habitat, DERIVED, source resolves
const by = (w) => R.spots.filter((s) => s.world === w);
ok(by('parishes').length >= 13 * 3 && by('bay').length >= 9 * 3 && by('wilds').length >= 4 * 2, 'spots: several per world (>=3 per parish/county, >=2 per wilds world)', JSON.stringify(R.counts.by_world));
ok(R.worlds.wilds.every((w) => by('wilds').filter((s) => s.region_id === w).length >= 2), 'spots: every wilds world holds at least two shore spots');
ok(R.spots.every((s) => s.provenance === 'DERIVED' && R.habitats[s.habitat] && typeof s.source === 'string'), 'spots: DERIVED, a catalogue habitat and a source path each');
ok(new Set(R.spots.map((s) => s.id)).size === R.spots.length, 'spots: ids unique');

// re-derive parish / Bay water spots from the map files: a bank spot sits SHORE_STEP m off a polygon vertex of its feature
const cache = new Map();
const mapOf = (rel) => { if (!cache.has(rel)) cache.set(rel, J(rel)); return cache.get(rel); };
let far = [];
for (const s of R.spots.filter((s) => s.world !== 'wilds' && /#water\./.test(s.source))) {
  const [rel, path] = s.source.split('#');
  const m = mapOf(rel), [, coll, idx] = path.match(/^water\.(lakes|channels|ponds)\[(\d+)\]$/) || [];
  const f = coll && m.water[coll][Number(idx)];
  if (!f || m.water.provenance !== 'AUTHORED') { far.push(s.id + ' (no AUTHORED feature)'); continue; }
  const d = Math.min(...f.polygon.map(([e, nn]) => Math.hypot(e - s.x, -nn - s.z)));
  if (!Number.isFinite(d) || Math.abs(d - R.rules.shore_step_m) > 0.2) far.push(s.id + ' ' + d.toFixed(2));
}
ok(far.length === 0, 'spots: every parish/Bay bank spot stands shore_step_m off a vertex of its AUTHORED water feature', far.slice(0, 5).join(', '));
const kinds = (w) => new Set(by(w).map((s) => s.habitat));
ok(['lake', 'bayou', 'canal', 'stream', 'pond'].every((h) => kinds('parishes').has(h)), 'spots: the parish world offers lake, bayou, canal, stream and pond water');
ok(kinds('bay').has('bay-shore') && by('bay').filter((s) => s.habitat === 'bay-shore').length >= 3, 'spots: the Bay offers several bay-shore spots (crab lines)');
const bay = J('bayarea/registry/bayarea.json');
let coastBad = [];
for (const s of by('bay').filter((s) => s.habitat === 'bay-shore')) {
  const c = bay.counties[s.region_id];
  const d = Math.min(...c.outline_local_m.flat(2).map(([e, nn]) => Math.hypot(e - s.x, -nn - s.z)));
  if (!Number.isFinite(d) || Math.abs(d - R.rules.coast_inland_m) > 0.2) coastBad.push(s.id + ' ' + d.toFixed(1));
}
ok(coastBad.length === 0, 'spots: every Bay coast spot stands coast_inland_m inside a vertex of its county outline', coastBad.join(', '));

// wilds: every shore spot is under its world's water level next to dry ground (re-sampled from wilds/core.mjs)
const W = J('wilds/registry/wilds.json');
let wbad = [];
for (const s of by('wilds')) {
  const w = W.worlds.find((x) => x.id === s.region_id), T = wildsTerrain(w), lvl = w.biome.water_level_m, st = 32;
  const wet = T.height(s.x, s.z) < lvl, dry = [[st, 0], [-st, 0], [0, st], [0, -st]].some(([dx, dz]) => T.height(s.x + dx, s.z + dz) >= lvl);
  if (!wet || !dry) wbad.push(s.id);
}
ok(wbad.length === 0, 'spots: every wilds spot is water below water_level_m beside dry ground (wilds/core.mjs)', wbad.join(', '));

// hidden spots + quest eggs
ok(R.hidden.length === 2 + R.worlds.wilds.length && R.hidden.every((id) => R.spots.find((s) => s.id === id && s.hidden && s.hidden_rule)), 'hidden: one rule-chosen quiet spot per world group (parish, Bay, each wilds world)');
if (existsSync(ROOT + 'quests/source/fish.json')) {
  const Q = J('quests/source/fish.json');
  ok(Q.from === 'FISH' && Q.entries.every((e) => /^(egg|treasure|side)-fish-[a-z0-9-]+$/.test(e.id) && e.id.startsWith(e.kind + '-') && e.reward.badge === 'badge-' + e.id && e.provenance === 'AUTHORED'), 'quests: fish.json ids, kinds and badges follow GAMES_CONTRACT v1');
  const eggs = Q.entries.filter((e) => e.kind === 'egg');
  ok(eggs.length === R.hidden.length && R.hidden.every((id) => { const s = R.spots.find((x) => x.id === id); return eggs.filter((e) => e.place === id || (s.world === 'wilds' && e.world === 'wilds:' + s.region_id && e.place === s.near_site)).length === 1; }), 'quests: every hidden spot has exactly one fish egg placed on it (wilds: on its nearest site)');
  ok(Q.entries.every((e) => e.reveal.length >= 20 && !/\d/.test(e.reveal) && /state wildlife agency/.test(e.reveal)), 'quests: reveal lines are general, number-free and name the kind of source');
  ok(Q.entries.filter((e) => e.band === 'K-5').every((e) => !e.requires.lessons.length && !e.requires.halls.length), 'quests: K-5 entries are explore-only');
}

// catalogue
const RODS = ['cane-pole', 'spinning-rod', 'baitcasting-rod', 'fly-rod', 'surf-rod', 'crab-line', 'crawfish-trap'];
ok(RODS.every((id) => R.rods.some((r) => r.id === id)), 'rods: cane pole, spinning, baitcasting, fly, surf rod, crab line and crawfish trap');
ok(R.rods.every((r) => Object.values(r.stats).every((v) => Number.isInteger(v) && v >= 1 && v <= 5)), 'rods: AUTHORED 1-5 game stats');
const NEED = ['largemouth-bass', 'bluegill', 'crappie', 'channel-catfish', 'red-drum', 'spotted-seatrout', 'southern-flounder', 'blue-crab', 'red-swamp-crawfish', 'striped-bass', 'california-halibut', 'dungeness-crab'];
ok(NEED.every((id) => R.species.some((s) => s.id === id)), 'species: the regional species of the brief are all present');
ok(R.species.every((s) => s.fact && s.handling && !/\d/.test(s.fact) && s.season.length === 2), 'species: a general fact (no numbers), a handling tip and a game-calendar season each');
ok(R.species.every((s) => s.spot_count >= 1), 'species: every species is catchable at some spot (region x habitat x rod)');
ok(R.species.every((s) => s.baits.every((b) => R.baits.some((x) => x.id === b))), 'species: every bait resolves');
const crawfish = R.species.find((s) => s.id === 'red-swamp-crawfish');
ok(crawfish.methods.join() === 'trap' && by('parishes').some((s) => ['canal', 'pond'].includes(s.habitat)), 'crawfish: trap-only, and the parish world has ditch/pond trap water');
ok(crawfish.seasons_link === null || (existsSync(ROOT + crawfish.seasons_link.registry) && readFileSync(ROOT + crawfish.seasons_link.registry, 'utf8').includes('"' + crawfish.seasons_link.id + '"')), 'crawfish: the FIELDS rice-crawfish link resolves, or is null (fail open)');

// honesty
const H = R.honesty;
ok(/Louisiana Department of Wildlife and Fisheries/.test(H.real) && /California Department of Fish and Wildlife/.test(H.real) && /state rules/.test(H.real), 'honesty: real activity follows state rules, naming both state wildlife agencies');
const text = JSON.stringify(R);
const agencies = new Set([...text.matchAll(/[A-Z][a-z]+ Department of [A-Z][A-Za-z ]+?(?=[;),.\"])/g)].map((m) => m[0]));
ok(agencies.size === 2 && [...agencies].every((a) => ['Louisiana Department of Wildlife and Fisheries', 'California Department of Fish and Wildlife'].includes(a)), 'honesty: no agency other than the two named in the wave notes', [...agencies].join(' | '));
ok(/approximate, game calendar/.test(H.seasons), 'honesty: seasons are labelled "approximate, game calendar"');
ok(/PLAY/.test(H.play) && /never a completion record/.test(H.play) && /never money/.test(H.play), 'honesty: catches are play, never a completion record, never money');
ok(/Never approach, feed or harass wildlife/.test(H.wildlife) && /alligators/.test(H.wildlife), 'honesty: wildlife safety line (never approach/feed/harass; alligators)');
ok(!/\b(record|world record|lb|kg|inches|cm)\b/i.test(JSON.stringify(R.species.map((s) => s.fact + s.handling))), 'honesty: no record sizes or measurements in species text');

console.log(fails ? `outdoors/test: ${fails} FAILED of ${n}` : `outdoors/test: ${n} checks passed`);
process.exit(fails ? 1 : 0);
