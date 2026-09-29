/* smiles/test.mjs - the AUTHORED Unspoken Smiles district pack (SMILES, wave 12). Recompute, never re-read:
 * stamps, counts, station placement and image digests are recomputed from the inputs and the files on disk. */
import { readFileSync, existsSync } from 'node:fs';
import { createHash } from 'node:crypto';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const HERE = dirname(fileURLToPath(import.meta.url));
const ROOT = join(HERE, '..');
let pass = 0, fail = 0;
const ok = (m, c) => { if (c) { pass++; console.log('  ok  ' + m); } else { fail++; console.log('FAIL  ' + m); } };
const sha = (b) => createHash('sha256').update(b).digest('hex');
const reg = JSON.parse(readFileSync(join(HERE, 'registry/smiles.json'), 'utf8'));
const dist = JSON.parse(readFileSync(join(HERE, 'authored/district.json'), 'utf8'));
const st = JSON.parse(readFileSync(join(HERE, 'authored/stations.json'), 'utf8'));
const eggsSrc = JSON.parse(readFileSync(join(ROOT, 'quests/source/smiles.json'), 'utf8'));

ok('source_stamp is the sha256 of build.py + render.py + every input, in order',
  reg.source_stamp === sha(Buffer.concat(reg.inputs.map((p) => readFileSync(join(ROOT, p))))) && reg.inputs.length === 5);
ok('the district is AUTHORED and says it is not a real place', reg.provenance === 'AUTHORED' && /not a real place/.test(reg.place_note)
  && reg.map.provenance === 'AUTHORED' && reg.atlas.provenance === 'AUTHORED');
ok('the district has the clinic, school, park, playground, community centre, shop and van lot zones',
  ['clinic', 'school', 'park', 'playground', 'community', 'shop', 'vanlot'].every((z) => reg.zones.some((x) => x.id === z)));
const ids = reg.stations.map((s) => s.id);
ok('37 unique stations, the union of both programme pack lists', ids.length === 37 && new Set(ids).size === 37
  && new Set(st.programmes.flatMap((p) => p.station_ids)).size === 37 && st.programmes.flatMap((p) => p.station_ids).every((i) => ids.includes(i)));
ok('every station sits in exactly one clinic room', reg.stations.every((s) => reg.rooms.filter((r) => r.stations.includes(s.id)).length === 1
  && reg.rooms.find((r) => r.id === s.room).stations.includes(s.id)));
const inside = (a, b) => a[0] >= b[0] && a[1] >= b[1] && a[0] + a[2] <= b[0] + b[2] && a[1] + a[3] <= b[1] + b[3];
const clinic = reg.zones.find((z) => z.id === 'clinic');
ok('every room lies inside the clinic', reg.rooms.every((r) => inside(r.rect, clinic.rect)));
ok('every station link is the GitHub URL of its source file on the programme branch',
  reg.stations.every((s) => s.url === `https://github.com/AGIFutureFoundation/vr-safety-training/blob/claude/vr-ar-safety-training-wkwmve/${s.source}`
    && /^WebXR\/(smartcity|trades)\/js\/.+\.js$/.test(s.source)));
ok('station provenance records the source repository and a full commit', /^[0-9a-f]{40}$/.test(reg.stations_from.ref_commit)
  && reg.stations_from.from === 'AGIFutureFoundation/vr-safety-training');
ok('map and atlas digests match the files on disk (one map, one atlas, no tile set)',
  sha(readFileSync(join(ROOT, reg.map.image))) === reg.map.sha256 && sha(readFileSync(join(ROOT, reg.atlas.image))) === reg.atlas.sha256
  && !existsSync(join(HERE, 'maps/tiles')));
ok('the 4k map is 4096 px and within the site file budget (< 1 MB, atlas < 256 KB)', reg.map.px === 4096
  && reg.map.bytes < 1048576 && reg.atlas.bytes < 262144);
ok('every egg comes from quests/source/smiles.json, world smiles:<zone>, spot inside its zone',
  reg.eggs.length === eggsSrc.entries.length && eggsSrc.entries.every((e) => {
    const g = reg.eggs.find((x) => x.id === e.id); const z = reg.zones.find((x) => `smiles:${x.id}` === e.world);
    return g && z && inside([...g.at, 0, 0], z.rect) && e.kind === 'egg' && e.provenance === 'AUTHORED' && g.reveal === e.reveal && e.reveal.length >= 20; }));
ok('six games, each placed in a real zone with a guidance line', ['brushing', 'flossing', 'snacks', 'plaque', 'handwash', 'drinks'].every((g) =>
  reg.games[g] && reg.zones.some((z) => z.id === reg.games[g].zone) && typeof reg.guidance[g] === 'string' && reg.guidance[g].length > 10));
ok('the disclaimer reads exactly "General guidance, not medical or dental advice."', reg.disclaimer === 'General guidance, not medical or dental advice.');
ok('the drinks game compares categories only - no sugar amounts anywhere in it',
  !/\d\s*(g|grams?|tsp|teaspoons?|cubes?)\b/i.test(JSON.stringify(reg.games.drinks)) && reg.games.drinks.categories.every((c) => Number.isInteger(c.rank)));
ok('brushing splits its time evenly across four quadrants', reg.games.brushing.quadrants.length === 4 && reg.games.brushing.total_s % 4 === 0);
ok('handwashing scrub time is the recorded guidance figure with its source named', reg.games.handwash.scrub_s === dist.games.handwash.scrub_s
  && /guidance/.test(reg.games.handwash.source));
const segs = reg.van_route.path.slice(1).map((b, i) => [reg.van_route.path[i], b]);
const onSt = ([a, b]) => reg.streets.some((s) => (a[1] === b[1] && s.from[1] === s.to[1] && s.from[1] === a[1] && Math.min(s.from[0], s.to[0]) <= Math.min(a[0], b[0]) && Math.max(a[0], b[0]) <= Math.max(s.from[0], s.to[0]))
  || (a[0] === b[0] && s.from[0] === s.to[0] && s.from[0] === a[0] && Math.min(s.from[1], s.to[1]) <= Math.min(a[1], b[1]) && Math.max(a[1], b[1]) <= Math.max(s.from[1], s.to[1])));
ok('the van route is a loop along street centrelines and passes every stop', segs.every(onSt)
  && JSON.stringify(reg.van_route.path[0]) === JSON.stringify(reg.van_route.path.at(-1))
  && reg.van_route.stops.every((p) => segs.some(([a, b]) => (a[0] === b[0] && b[0] === p.at[0] && Math.min(a[1], b[1]) <= p.at[1] && p.at[1] <= Math.max(a[1], b[1]))
    || (a[1] === b[1] && b[1] === p.at[1] && Math.min(a[0], b[0]) <= p.at[0] && p.at[0] <= Math.max(a[0], b[0])))));
ok('counts are recounted', reg.counts.stations === reg.stations.length && reg.counts.rooms === reg.rooms.length
  && reg.counts.zones === reg.zones.length && reg.counts.eggs === reg.eggs.length);
ok('play note says games are device-only play, never a completion record', /device only/.test(reg.play_note) && /never a completion record/.test(reg.play_note));

ok('the district grew to a large 4k world: 1200 m square, library, sports field, market plaza, bus stop and 3 residential blocks, 16 eggs',
  reg.size_m[0] === 1200 && reg.size_m[1] === 1200 && ['library', 'sports', 'market', 'busstop'].every((k) => reg.zones.some((z) => z.kind === k))
  && reg.zones.filter((z) => z.kind === 'residential').length === 3 && reg.eggs.length >= 16);
ok('solid footprints (houses, stalls) sit inside their zones and no egg is inside or against one', reg.zones.every((z) => z.solids.every((r) => inside(r, z.rect))
  && reg.eggs.filter((g) => g.zone === z.id).every((g) => !z.solids.some((r) => r[0] - 2 <= g.at[0] && g.at[0] <= r[0] + r[2] + 2 && r[1] - 2 <= g.at[1] && g.at[1] <= r[1] + r[3] + 2))));
ok('every walled zone and clinic room has one doorway in its south wall, as wide as the rule says', reg.doors.every((d) => d.width_m > 1.5)
  && reg.rooms.every((r) => reg.doors.filter((d) => d.id === 'room-' + r.id).length === 1)
  && reg.zones.filter((z) => ['clinic', 'school', 'community', 'shop', 'vanlot', 'library'].includes(z.kind)).every((z) => reg.doors.filter((d) => d.id === z.id).length === 1
    && reg.doors.find((d) => d.id === z.id).at[1] === z.rect[1] + z.rect[3]));
console.log(`smiles/test: ${pass} passed, ${fail} failed`);
if (fail) process.exit(1);
