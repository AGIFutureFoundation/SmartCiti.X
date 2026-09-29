/* holodeck/test.mjs - the "SmartCiti.X Powered by AGI Corp" holodeck packs, recounted.
 * Every figure in holodeck/registry/packs.json is recomputed here from the registries it names;
 * statuses must follow content; no price, no certification, no partner in any pack.
 * Prints `  ok ` per check, FAIL at column 0; exits non-zero on any failure. Network-free. */
import { readFileSync, existsSync } from 'node:fs';
import { createHash } from 'node:crypto';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const HERE = dirname(fileURLToPath(import.meta.url));
const ROOT = join(HERE, '..');
let pass = 0, fail = 0;
const ok = (c, m) => { if (c) { pass++; console.log('  ok ' + m); } else { fail++; console.log('FAIL ' + m); } };
const raw = (p) => readFileSync(join(ROOT, p));
const J = (p) => JSON.parse(raw(p).toString('utf8'));
const sha16 = (p) => createHash('sha256').update(raw(p)).digest('hex').slice(0, 16);
const has = (p) => existsSync(join(ROOT, p));
const eq = (a, b) => JSON.stringify(a) === JSON.stringify(b);
const sortObj = (o) => Object.fromEntries(Object.entries(o).sort(([a], [b]) => (a < b ? -1 : 1)));
console.log('holodeck/test.mjs');

const D = J('holodeck/registry/packs.json');
const SERIES = 'SmartCiti.X Powered by AGI Corp';
const PATHS = ['trades', 'k12', 'responders', 'un', 'relief', 'teachers', 'roam'];
const KINDS = ['union', 'k12', 'path', 'world', 'system'];
const P = Object.fromEntries(D.packs.map((p) => [p.id, p]));

/* ---- identity ---- */
ok(D.series === SERIES, `series is exactly "${SERIES}"`);
ok(D.packs.every((p) => p.series === SERIES), 'every pack carries the exact series name');
ok(D.source_stamp === sha16('holodeck/build.py'), 'source_stamp = sha256[:16] of holodeck/build.py (registry is current)');
ok(new Set(D.packs.map((p) => p.id)).size === D.packs.length, `pack ids unique (${D.packs.length})`);
ok(eq(D.kinds, KINDS) && D.packs.every((p) => KINDS.includes(p.kind)), 'kinds are union / k12 / path / world / system');
ok(D.packs.every((p) => p.requires.every((r) => r in P)), 'every requires names a pack in this registry');
ok(D.packs.every((p) => p.sources.every((s) => has(s.path) && s.sha256 === sha16(s.path))), 'every source registry exists and its sha256[:16] matches the file now');

/* ---- recount: union packages ---- */
const B = J('bundles/registry/bundles.json');
const HALLS = new Set(J('pack/registry/halls.json').halls.map((h) => h.slug));
const UNIONS = new Set(J('unions/registry/unions.json').unions.map((u) => u.slug));
const SIMS = new Set(Object.keys(J('sims/registry/sims.json').sims));
const LES = J('lessons/registry/lessons.json').lessons;
const unionIds = Object.keys(B.packages).map((k) => 'union-' + k);
ok(eq(D.packs.filter((p) => p.kind === 'union').map((p) => p.id), unionIds), `one union pack per bundles/ package, in order (${unionIds.length})`);
for (const [k, pk] of Object.entries(B.packages)) {
  const c = pk.contents, p = P['union-' + k];
  const want = sortObj({ trades: c.trades.length, ladder_cells: c.ladder_cells.length, seats: c.seats.length, lessons: c.lessons.length });
  ok(p && eq(sortObj(p.contents), want) && p.title === pk.name, `union-${k}: title and counts recomputed ${JSON.stringify(want)}`);
  ok(c.trades.every((t) => HALLS.has(t) && UNIONS.has(t)) && c.seats.every((s) => SIMS.has(s)) && c.lessons.every((l) => l in LES),
    `union-${k}: every trade is a pack/ hall and a unions/ union, every seat a sim, every lesson a lesson`);
}

/* ---- recount: Cognition.X K-12 ---- */
const LAY = J('layers/registry/layers.json'), SCH = J('schools/registry/schools.json');
const unitHalls = new Set(SCH.units.map((u) => u.hall));
const stations = LAY.parishes.flatMap((x) => x.stations);
const k = P['cognition-x-k12'];
ok(k && k.title === 'Cognition.X K-12' && LAY.layers['k12-unit'].label === k.title, 'K-12 pack is titled "Cognition.X K-12" (= layers k12-unit label)');
ok(k && eq(sortObj(k.contents), sortObj({ units: SCH.units.length, bands: SCH.bands.length,
  stations: stations.filter((s) => s.layer === 'k12-unit').length,
  lessons: Object.values(LES).filter((l) => unitHalls.has(l.hall)).length })), 'K-12 counts recomputed (units, bands, stations, lessons)');

/* ---- recount: the seven paths ---- */
ok(eq(D.packs.filter((p) => p.kind === 'path').map((p) => p.id), PATHS.map((x) => 'path-' + x)), 'seven path packs in the fixed order');
const PR = has('layers/registry/paths.json') ? J('layers/registry/paths.json') : null;
for (const id of PATHS) {
  const p = P['path-' + id];
  if (!PR) { ok(p.status === 'PROPOSED' && Object.values(p.contents).every((v) => v === 0), `path-${id}: no paths registry -> PROPOSED with 0`); continue; }
  const es = PR.parishes.map((x) => x.paths.find((y) => y.id === id));
  const want = sortObj({ parishes: es.length, steps: es.reduce((a, e) => a + e.steps.length, 0),
    stories: PR.parishes.reduce((a, x) => a + x.stories.filter((s) => s.path === id).length, 0) });
  const regStatus = es[0].status;
  const st = regStatus === 'AVAILABLE' && Object.values(want).some((v) => v > 0) ? 'SHIPPING' : 'PROPOSED';
  ok(eq(sortObj(p.contents), want) && p.status === st, `path-${id}: counts ${JSON.stringify(want)} and status ${st} recomputed (registry ${regStatus})`);
}
ok(P['path-un'].status === 'PROPOSED' && P['path-un'].open === null, 'UN training stays a PROPOSED module, with no deep link');

/* ---- recount: worlds and systems ---- */
const PAR = J('parishes/registry/parishes.json').parishes;
ok(eq(sortObj(P['parish-worlds'].contents), sortObj({ parishes: Object.keys(PAR).length,
  landmarks: Object.values(PAR).reduce((a, x) => a + x.landmarks.length, 0),
  maps: Object.values(PAR).filter((x) => x.map).length, stations: stations.length })), 'parish-worlds counts recomputed');
const FL = J('fleet/registry/fleet.json').fleet;
ok(eq(sortObj(P.fleet.contents), sortObj({ vehicles: FL.length, land: FL.filter((v) => v.medium === 'land').length,
  water: FL.filter((v) => v.medium === 'water').length, families: new Set(FL.map((v) => v.family)).size })), 'fleet counts recomputed');
const NEW = {
  'city-life': ['economy/registry/economy.json', (e) => ({ lots: Object.values(e.parishes).reduce((a, x) => a + x.lots.length, 0),
    business_types: e.business_types.length, rentals: Object.keys(e.rentals).length })],
  'living-world': ['ambient/registry/ambient.json', (a) => ({ species: Object.keys(a.species).length, land_uses: a.land_uses.length,
    vegetation: Object.keys(a.vegetation).length, litter: Object.keys(a.litter).length })],
  physics: ['physics/registry/physics.json', (f) => ({ coefficients: Object.values(f.coeffs).reduce((a, g) => a + Object.keys(g).length, 0),
    pedestrian_classes: f.pedestrian_classes.length })],
};
for (const [id, [reg, count]] of Object.entries(NEW)) {
  const p = P[id];
  if (!has(reg)) { ok(p.status === 'PROPOSED' && Object.values(p.contents).every((v) => v === 0) && p.sources.length === 0, `${id}: ${reg} absent -> PROPOSED with 0, no source`); continue; }
  ok(eq(sortObj(p.contents), sortObj(count(J(reg)))) && p.sources.some((s) => s.path === reg), `${id}: counts recomputed from ${reg}`);
}

/* ---- statuses and links honest ---- */
ok(D.packs.every((p) => p.status === 'SHIPPING' || p.status === 'PROPOSED'), 'status is SHIPPING or PROPOSED only');
ok(D.packs.filter((p) => p.kind !== 'path').every((p) => (p.status === 'SHIPPING') === Object.values(p.contents).some((v) => v > 0)),
  'SHIPPING exactly when counted content exists (paths: also the registry status, checked above)');
ok(D.packs.every((p) => p.status === 'SHIPPING' || p.open === null), 'a PROPOSED pack never deep-links');
ok(D.packs.every((p) => p.open === null || has(p.open)), 'every deep link names a page that exists');
const KIT = { 'city-life': 'econkit', 'living-world': 'ambientkit', physics: 'physkit' };
ok(Object.entries(KIT).every(([id, kit]) => P[id].open === null || readFileSync(join(ROOT, P[id].open), 'utf8').includes(kit)),
  'a city-life / living-world / physics link exists only when that page embeds the kit');
const c = D.counts;
ok(c.packs === D.packs.length && c.shipping === D.packs.filter((p) => p.status === 'SHIPPING').length
  && c.proposed === D.packs.filter((p) => p.status === 'PROPOSED').length
  && KINDS.every((k2) => c.by_kind[k2] === D.packs.filter((p) => p.kind === k2).length), 'counts block recomputed');

/* ---- no price, no accreditation, no partner claim in any pack ---- */
const packText = JSON.stringify(D.packs);
ok(!/price|coin|\$|€|£|¥|₹|\busd\b|\beur\b|\bgbp\b|purchase|buy\b|download/i.test(packText), 'no price, currency, coin, purchase or download in any pack');
ok(!/accredit|certif|licen[cs]|partner|endorse|affiliat/i.test(packText), 'no accreditation, certification or partner claim in any pack');
ok(/PROPOSED partners/.test(D.honesty.partners) && /unverified general practice/.test(D.honesty.certification) && /not live/.test(D.honesty.price),
  'honesty block: PROPOSED partners, unverified general practice, payments not live');

/* ---- 8 locales: every packs.* key translated ---- */
const LOC = ['ar', 'de', 'en', 'es', 'fr', 'hi', 'pt', 'zh'];
const EN = J('i18n/locales/en.json').strings;
const PK = Object.keys(EN).filter((x) => x.startsWith('packs.'));
ok(PK.length >= 60, `en carries ${PK.length} packs.* keys`);
ok(D.packs.every((p) => p.kind === 'union' || p.kind === 'k12' || p.title_key in EN), 'every pack title other than the quoted union and Cognition.X names has an en packs.* key');
for (const l of LOC.filter((x) => x !== 'en')) {
  const S = J(`i18n/locales/${l}.json`).strings;
  ok(PK.every((x) => typeof S[x] === 'string' && S[x].trim() && S[x] !== EN[x]), `${l}: all ${PK.length} packs.* keys present and translated`);
}

console.log(`holodeck: ${pass} passed, ${fail} failed`);
process.exit(fail ? 1 : 0);
