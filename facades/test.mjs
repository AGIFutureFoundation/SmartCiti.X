/* facades/test.mjs - the facade recipes and play signs, checked. Browser-free, network-free.
 * Recompute, never re-read: counts are recounted, the denylist is re-applied here with its own matcher, sign
 * lots are re-read from economy/registry/economy.json (read-only input), the stamp is recomputed. */
import { readFileSync } from 'node:fs';
import { createHash } from 'node:crypto';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const HERE = dirname(fileURLToPath(import.meta.url));
const ROOT = join(HERE, '..');
let pass = 0, fail = 0;
const ok = (c, m) => { if (c) { pass++; console.log('  ok  ' + m); } else { fail++; console.log('FAIL  ' + m); } };
const read = (p) => readFileSync(join(ROOT, p));
const R = JSON.parse(read('facades/registry/facades.json'));
const E = JSON.parse(read('economy/registry/economy.json'));
console.log('facades/test.mjs');

/* provenance + stamp */
const eco = createHash('sha256').update(read('economy/registry/economy.json')).digest('hex');
const stamp = createHash('sha256').update(Buffer.concat([read('facades/build.py'), Buffer.from(eco)])).digest('hex');
ok(R.pack === 'facades' && R.source_stamp === stamp.slice(0, 16) && R.source_stamp_sha256 === stamp, 'stamp: registry built from the current builder and economy registry');
ok(R.pack_version === JSON.parse(read('pack/manifest.json')).pack_version, 'pack_version read from the manifest');
ok(Object.values(R.styles).every((s) => s.provenance === 'AUTHORED') && R.signs.every((s) => s.provenance === 'AUTHORED'), 'provenance: every style and sign is AUTHORED');
ok(/AUTHORED/.test(R.honesty.styles) && /play/.test(R.honesty.signs) && /never a real business/.test(R.honesty.signs), 'honesty: styles AUTHORED, signs are play and never a real business');

/* styles */
const WANT = ['brick-warehouse', 'civic', 'craftsman-bungalow', 'creole-cottage', 'italianate-row', 'midcentury-commercial', 'modern-glass', 'shotgun-gallery'];
ok(Object.keys(R.styles).sort().join() === WANT.join(), `styles: the 8 AUTHORED families (${WANT.length})`);
const comps = Object.values(R.styles).flatMap((s) => s.components);
ok(comps.length === R.counts.components, `components: count recounted ${comps.length}`);
ok(comps.every((c) => c.colour_category in R.colour_categories), 'components: every colour category exists');
ok(comps.every((c) => c.pattern_id in R.patterns), 'components: every pattern id exists');
ok(comps.every((c) => ['band', 'repeat', 'pair', 'single', 'roof'].includes(c.layout) && ['ground', 'eave'].includes(c.y_ref)), 'components: layout and y_ref are known');
ok(comps.every((c) => [c.y_m, c.h_m, c.depth_m, c.out_m].every(Number.isFinite) && c.depth_m > 0 && c.h_m !== 0), 'components: finite dimensions, positive depth');
ok(comps.every((c) => c.layout === 'band' || (c.width_m > 0 && c.width_m < 12)), 'components: non-band parts carry a width in 0..12 m');
const KINDS = new Set(comps.map((c) => c.component));
for (const k of ['cornice', 'parapet', 'railing', 'gallery_post', 'shutters', 'awning', 'bracket', 'window_trim', 'door_trim', 'storefront_glazing', 'stoop', 'downpipe', 'rooftop_unit'])
  ok(KINDS.has(k), `components: the recipes include a ${k}`);
ok(Object.values(R.colour_categories).every((c) => /^#[0-9A-F]{6}$/.test(c.hex) && c.use), 'colours: AUTHORED name + hex + use');
ok(!/pantone|ral \d|sherwin|benjamin moore|behr /i.test(JSON.stringify(R.colour_categories)), 'colours: no paint brand or standard name');
ok(Object.values(R.styles).every((s) => !/replica|real building at/i.test(s.geography)), 'styles: geography is general, no replica claim');
ok(R.rules.every((r) => r.style in R.styles), 'rules: every rule names a style');
for (const w of ['parishes', 'bay']) for (const [fam, use] of [['house', 'residential'], ['midrise', 'commercial'], ['midrise', 'industrial']])
  for (const v of [0, 1]) ok(R.rules.some((r) => (r.world === w || r.world === '*') && r.family === fam && r.use === use && (r.variant === v || r.variant === '*')), `rules: ${w} ${fam}/${use} variant ${v} has a style`);

/* PATTERN_CONTRACT v1 colour map */
const EXT = JSON.parse(read('surfaces/registry/exterior.json'));
const EXT_IDS = new Set(Object.values(EXT.colour_families).flatMap((f) => f.colours.map((c) => c.id)));
ok(Object.keys(R.pattern_map).sort().join() === Object.keys(R.colour_categories).sort().join(), 'pattern map: every colour category is mapped exactly once');
ok(Object.values(R.pattern_map).every((v) => v === null || EXT_IDS.has(v)), 'pattern map: every PATTERN id exists in surfaces/registry/exterior.json');
ok(R.pattern_families.join() === [...new Set(Object.values(R.pattern_map).filter(Boolean).map((v) => v.split('.')[0]))].sort().join(), 'pattern map: the families list is exactly the families the map names');
/* signs */
const lots = Object.values(E.parishes).flatMap((p) => p.lots).filter((l) => l.zone === 'commercial');
ok(R.signs.length === lots.length && lots.every((l) => R.signs.some((s) => s.lot_id === l.id && s.x === l.x && s.z === l.z && s.parish === l.parish)), `signs: one per economy commercial lot at the lot's own point (${lots.length})`);
const BT = new Set(E.business_types.map((b) => b.id));
ok(R.signs.every((s) => BT.has(s.business_type) && s.icon === R.sign_rules.icons[s.business_type]), 'signs: business type is an economy type, icon matches');
ok(R.signs.every((s) => R.sign_rules.placements.includes(s.placement)), 'signs: placement is fascia|blade|window|monument');
ok(new Set(R.signs.map((s) => s.name)).size === R.signs.length, 'signs: names are unique');
ok(R.signs.every((s) => R.sign_rules.place_words.some((p) => s.name.startsWith(p + ' ')) && R.sign_rules.type_words[s.business_type].some((t) => s.name.endsWith(' ' + t))), 'signs: every name is built from the word lists');
ok(R.denylist.partial === true && /PARTIAL/.test(R.denylist.note) && R.denylist.names.length >= 50, `denylist: marked partial, ${R.denylist.names.length} names`);
const words = (s) => ' ' + (s.toLowerCase().match(/[a-z0-9]+(?:['\-][a-z0-9]+)*/g) || []).join(' ') + ' ';
const hit = (n) => R.denylist.names.find((d) => words(n).includes(words(d)));
ok(R.signs.every((s) => !hit(s.name)), 'denylist: no sign name equals or contains a listed chain/brand');
ok(hit('Harbor Freight Tools') === 'Harbor Freight' && hit('Big Walmart') === 'Walmart' && !hit('Harbor Bike Repair'), 'denylist: the matcher catches known names and passes a generic one');
ok(R.signs.every((s) => /not a real business/.test(s.label)), 'signs: every sign carries the play label');
ok(R.signs.every((s) => s.palette.length === 2 && s.palette.every((h) => /^#[0-9A-F]{6}$/.test(h))), 'signs: palette is [bg, text] hex');

console.log(`facades: ${pass} passed, ${fail} failed`);
if (fail) process.exit(1);
