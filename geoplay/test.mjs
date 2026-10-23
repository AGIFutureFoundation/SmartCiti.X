#!/usr/bin/env node
/* geoplay/test.mjs - the geo-anchored training-drop layer, held to its rules.
   Prints "  ok <name>" per check, FAIL <name> at column 0, exits non-zero on failure.
     node geoplay/test.mjs                 static + on-device logic (no browser)
     node geoplay/test.mjs --root=<copy>   a mutated copy of the tree
     node geoplay/test.mjs --browser [--origin=http://127.0.0.1:PORT]
                                           adds a headless-browser run with a mocked device position
   Playwright: PLAYWRIGHT_MODULE, else the local package, else the global one; the browser: CHROMIUM_PATH. */
import { readFileSync, existsSync } from 'node:fs';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { execFileSync } from 'node:child_process';
import vm from 'node:vm';

const HERE = dirname(fileURLToPath(import.meta.url));
const args = process.argv.slice(2);
const rootArg = args.find((a) => a.startsWith('--root='));
const ROOT = resolve(rootArg ? rootArg.slice(7) : join(HERE, '..'));
const WANT_BROWSER = args.includes('--browser');
const originArg = args.find((a) => a.startsWith('--origin='));
const shotArg = args.find((a) => a.startsWith('--shot='));   // optional directory for two phone-width screenshots

let n = 0, bad = 0;
const ok = (name, cond, ev = []) => {
  if (cond) { n++; console.log('  ok ' + name); return; }
  bad++; console.log('FAIL ' + name);
  for (const e of [].concat(ev).slice(0, 8)) console.log('     ' + e);
};
const read = (rel) => readFileSync(join(ROOT, rel), 'utf8');
const J = (rel) => JSON.parse(read(rel));

const reg = J('geoplay/registry/geoplay.json');
const poseDoc = J('spatial/registry/drops_geopose.json');
const geopose = J('spatial/registry/geopose.json');
const geo = J('geo/registry/campuses_geo.json');
const resto = J('restoration/registry/restoration.json');
const tasks = J('tasks/registry/tasks.json');
const lessons = J('lessons/registry/lessons.json').lessons;
const campuses = J('unions/registry/campuses.json').campuses;
const rules = J('geoplay/source/rules.json');
const playJs = read('geoplay/play.js');
const uiJs = read('geoplay/ui.js');
const page = read('web/trade_craft_geomap.html');
const TASK = Object.fromEntries(tasks.tasks.map((t) => [t.id, t]));
const SAFETY = 'Stay aware of your surroundings; do not enter roads or private property.';

/* the suite's own bounds: independent of the rules file, so loosening that file cannot loosen this */
const HARD_RADIUS_MIN = 40, HARD_RADIUS_MAX = 200, HARD_ACCURACY_MAX = 150;
const OWN_DENY = ['port', 'laboratory', 'station', 'pier', 'museum', 'furnace', 'airport', 'shipyard', 'naval', 'superfund', 'cleanup', 'wetland', 'wetlands', 'marsh', 'pond', 'levee', 'refinery', 'plant', 'tunnel', 'bridge', 'highway', 'residence', 'home'];
const words = (s) => new Set(s.toLowerCase().match(/[a-z]+/g) || []);
const rad = (d) => d * Math.PI / 180;
const dist = (a, b, c, d) => {
  const h = Math.sin(rad(c - a) / 2) ** 2 + Math.cos(rad(a)) * Math.cos(rad(c)) * Math.sin(rad(d - b) / 2) ** 2;
  return 2 * 6371008.8 * Math.asin(Math.sqrt(h));
};

/* ------------------------------------------------------------- stamps --- */
{
  let msg = '';
  try { execFileSync('python3', [join(ROOT, 'geoplay/build.py'), '--check'], { encoding: 'utf8', stdio: 'pipe' }); }
  catch (e) { msg = String(e.stderr || e.message).trim().split('\n').pop(); }
  ok('[stamp] geoplay.json and drops_geopose.json are current with geoplay/build.py and every registry it reads', msg === '', [msg]);
}
ok('[stamp] the registry names the registries it reads and a 16-hex source_stamp',
  /^[0-9a-f]{16}$/.test(reg.source_stamp) && ['geo/registry/campuses_geo.json', 'restoration/registry/restoration.json', 'tasks/registry/tasks.json', 'lessons/registry/lessons.json'].every((r) => reg.reads.includes(r)));
ok('[stamp] the GeoPose file carries the registry\'s stamp', poseDoc.source_stamp === reg.source_stamp);

/* ------------------------------------------------- stops resolve to registry records --- */
const srcOf = (st) => {
  let m = st.source_ref.match(/^geo\/registry\/campuses_geo\.json#anchors\.([a-z-]+)\[(.+)\]$/);
  if (m) {
    const a = (geo.anchors[m[1]] || []).find((x) => x.name === m[2]);
    return a ? { kind: 'anchor', campus: m[1], rec: a } : null;
  }
  m = st.source_ref.match(/^restoration\/registry\/restoration\.json#sites\[([a-z-]+)\]$/);
  if (m) {
    const s = resto.sites.find((x) => x.id === m[1]);
    return s ? { kind: 'restoration-site', campus: s.campus, rec: s } : null;
  }
  return null;
};
const unresolved = [], moved = [], provBad = [], campusBad = [];
for (const st of reg.stops) {
  const src = srcOf(st);
  if (!src) { unresolved.push(`${st.id}: ${st.source_ref}`); continue; }
  const r = src.rec;
  if (r.lat !== st.lat || (r.lng !== st.lng)) moved.push(`${st.id}: registry ${r.lat},${r.lng} vs stop ${st.lat},${st.lng}`);
  if (src.kind === 'anchor' && r.provenance !== st.coordinate_provenance) provBad.push(`${st.id}: ${r.provenance} vs ${st.coordinate_provenance}`);
  if (src.kind === 'restoration-site') {
    const pose = geopose.poses.find((p) => p.subject.ref === 'restoration-site:' + r.id);
    if (!pose || pose.provenance.position_horizontal !== st.coordinate_provenance) provBad.push(`${st.id}: pose provenance differs`);
    if (r.pin !== true) unresolved.push(`${st.id}: site is not pinned`);
  }
  if (src.campus !== st.campus || !(st.campus in campuses)) campusBad.push(st.id);
}
ok(`[stops] all ${reg.stops.length} stops resolve to a real record in geo/ or restoration/`, reg.stops.length > 0 && unresolved.length === 0, unresolved);
ok('[stops] every stop coordinate equals its source record exactly and is a valid WGS84 point',
  moved.length === 0 && reg.stops.every((s) => Math.abs(s.lat) <= 90 && Math.abs(s.lng) <= 180 && Number.isFinite(s.lat) && Number.isFinite(s.lng)), moved);
ok('[stops] each coordinate keeps the provenance word of the registry it came from, never upgraded', provBad.length === 0, provBad);
ok('[stops] each stop sits on a campus the union registry carries', campusBad.length === 0, campusBad);
ok('[stops] stop ids are unique and kebab-case', new Set(reg.stops.map((s) => s.id)).size === reg.stops.length && reg.stops.every((s) => /^stop-[a-z0-9]+(-[a-z0-9]+)*$/.test(s.id)));
ok('[stops] counts in the registry are recounted from its stops',
  reg.counts.stops === reg.stops.length && reg.counts.drops === reg.stops.reduce((a, s) => a + s.drops.length, 0)
  && reg.counts.geoposes === poseDoc.poses.length && reg.counts.unpinned_public_places === reg.unpinned.length && reg.counts.refused === reg.refused.length);

/* ------------------------------------------------------ drops resolve to tasks --- */
const dropBad = [], seen = new Set();
const ON_GLOBE = ['campus', 'restoration-site'];
for (const st of reg.stops) {
  const src = srcOf(st);
  if (st.drops.length < 1 || st.drops.length > 5) dropBad.push(`${st.id}: ${st.drops.length} drops`);
  for (const d of st.drops) {
    const t = TASK[d.task];
    if (!t) { dropBad.push(`${d.id}: task ${d.task} is not in tasks.json`); continue; }
    if (seen.has(t.id)) dropBad.push(`${t.id} pinned twice`);
    seen.add(t.id);
    if (d.id !== 'drop-' + t.id) dropBad.push(`${d.id}: id does not follow its task`);
    if (d.title !== t.title) dropBad.push(`${d.id}: title is not the task's own`);
    if (!t.launch || t.launch.href == null) dropBad.push(`${d.id}: the task has no launch link`);
    if (!ON_GLOBE.includes(t.place.kind)) dropBad.push(`${d.id}: task place ${t.place.kind} is not on the globe`);
    if (t.place.kind === 'restoration-site' && !(src && src.kind === 'restoration-site' && t.place.id === src.rec.id)) dropBad.push(`${d.id}: restoration task is at ${t.place.id}, not this stop`);
    if (t.place.kind === 'campus' && t.place.campus !== st.campus) dropBad.push(`${d.id}: campus task is for ${t.place.campus}, not ${st.campus}`);
    if (JSON.stringify(d.lessons) !== JSON.stringify(t.requires)) dropBad.push(`${d.id}: lessons differ from the task's requires`);
  }
}
ok(`[drops] all ${reg.counts.drops} drops resolve to a real, launchable task at the same place (restoration site id or campus), once each, with the task's own title`, dropBad.length === 0, dropBad);
const lsBad = reg.stops.flatMap((s) => s.drops.flatMap((d) => d.lessons.filter((l) => !(l in lessons)).map((l) => `${d.id}: lesson ${l}`)));
ok('[drops] every linked lesson resolves in lessons/registry/lessons.json', lsBad.length === 0, lsBad);
{
  const href = (id) => TASK[id].launch.href;
  const m = [...page.matchAll(/"task":"([^"]+)","title":"[^"]*","kind_label":"[^"]*","href":"([^"]+)"/g)];
  const wrong = m.filter(([, id, h]) => !(h === href(id).replace(/^web\//, '') || h === '../' + href(id))).map(([, id, h]) => `${id}: ${h}`);
  ok(`[drops] the geomap carries all ${reg.counts.drops} drops, each with the task's own launch link (web/ stripped as the geomap already does)`, m.length === reg.counts.drops && wrong.length === 0, wrong);
}

/* -------------------------------------------------------------- radius --- */
{
  const r = reg.rules.radius_m;
  const bad = reg.stops.filter((s) => !(Number.isInteger(s.radius_m) && s.radius_m >= HARD_RADIUS_MIN && s.radius_m <= HARD_RADIUS_MAX && s.radius_m >= r.min && s.radius_m <= r.max && s.radius_m === r.by_class[s.class]));
  ok(`[radius] every stop radius is within ${HARD_RADIUS_MIN}..${HARD_RADIUS_MAX} m (this suite's own bounds), within the registry's declared bounds, and the class value`, bad.length === 0 && r.min >= HARD_RADIUS_MIN && r.max <= HARD_RADIUS_MAX, bad.map((s) => `${s.id}: ${s.radius_m}`));
  ok('[radius] the accuracy limit for an unlock is declared and no wider than the suite\'s own limit', reg.rules.accuracy_max_m > 0 && reg.rules.accuracy_max_m <= HARD_ACCURACY_MAX);
  let overlap = [];
  for (let i = 0; i < reg.stops.length; i++) for (let j = i + 1; j < reg.stops.length; j++) {
    const a = reg.stops[i], b = reg.stops[j];
    if (dist(a.lat, a.lng, b.lat, b.lng) < a.radius_m + b.radius_m + 100) overlap.push(`${a.id} / ${b.id}`);
  }
  ok('[radius] no two unlock circles touch, so one position never opens two stops', overlap.length === 0, overlap);
}

/* ------------------------------------------------- the public-place rule --- */
{
  const bad = [];
  for (const st of reg.stops) {
    const src = srcOf(st);
    if (!src) continue;
    const r = src.rec;
    if (src.kind === 'anchor') {
      const nm = words(r.name + ' ' + r.source);
      const hit = OWN_DENY.filter((w) => nm.has(w));
      if (hit.length) bad.push(`${st.id}: names ${hit.join(',')}`);
      if (!words(r.blurb + ' ' + r.source).has('public')) bad.push(`${st.id}: the registry does not say the place is public`);
      if (![...words(r.name + ' ' + r.blurb)].some((w) => w === 'university' || w === 'college')) bad.push(`${st.id}: not a university or college`);
      if (st.class !== 'public-university') bad.push(`${st.id}: class ${st.class}`);
    } else {
      const nm = words(r.name + ' ' + r.habitat);
      const hit = OWN_DENY.filter((w) => nm.has(w));
      if (hit.length) bad.push(`${st.id}: names ${hit.join(',')}`);
      if (r.walkable !== true || r.ground !== 'upland' || r.category !== 'habitat-restoration') bad.push(`${st.id}: ground ${r.ground}, walkable ${r.walkable}`);
      if (!/Port of San Francisco|California State Parks/.test(r.org)) bad.push(`${st.id}: operator ${r.org}`);
      if (!/Park|Point/.test(r.name)) bad.push(`${st.id}: name does not say park or point`);
      if (r.participation === true) bad.push(`${st.id}: a cleanup site`);
      if (st.class !== 'public-park') bad.push(`${st.id}: class ${st.class}`);
    }
  }
  ok('[safety] every stop\'s own source record states a public university/college or a public park by the rule, and names no port, laboratory, station, pier, shipyard, cleanup site, wetland or levee', bad.length === 0, bad);
  const cleanup = resto.sites.filter((s) => s.walkable !== true && s.lat != null);
  const near = [];
  for (const st of reg.stops) for (const c of cleanup) if (dist(st.lat, st.lng, c.lat, c.lng) < 800) near.push(`${st.id} is ${Math.round(dist(st.lat, st.lng, c.lat, c.lng))} m from ${c.id}`);
  ok('[safety] no stop is within 800 m of a federal cleanup site the restoration registry refuses to present', near.length === 0, near);
  const mustRefuse = ['Port of Houston Authority', 'Port of Seattle', 'Chicago Union Station', 'Navy Pier', 'Denver Union Station', 'National Renewable Energy Laboratory', 'Museum of Flight', 'PortMiami',
    'Carrie Blast Furnaces National Historic Landmark', 'NOAA Atlantic Oceanographic and Meteorological Laboratory', 'The Henry Ford', 'Tulane University', 'Loyola University', 'Delgado Community College',
    'Hunters Point Naval Shipyard', 'Former Naval Station Treasure Island', 'Montezuma Tidal', 'South Bay Salt Pond', 'San Francisco', 'Oakland'];
  const names = reg.refused.map((r) => r.name);
  const missing = mustRefuse.filter((m) => !names.some((x) => x === m || x.startsWith(m)));
  ok('[safety] the places a learner must not be sent to are refused by name, each with its reason (ports, laboratories, stations, piers, cleanup sites, wetlands, cities, private or not-stated campuses)', missing.length === 0 && reg.refused.every((r) => r.reason.length > 20), missing);
  ok('[safety] no refused place is also a stop, and every anchor and site in the source registries is accounted for once (stop, unpinned or refused)', (() => {
    const refs = [...reg.stops.map((s) => s.source_ref), ...reg.unpinned.map((u) => u.ref), ...reg.refused.map((r) => r.ref)];
    const total = Object.values(geo.anchors).reduce((a, v) => a + v.length, 0) + resto.sites.length;
    const stopNames = new Set(reg.stops.map((s) => s.name));
    return refs.length === total && !reg.refused.some((r) => stopNames.has(r.name)) && !reg.unpinned.some((u) => stopNames.has(u.name));
  })());
}

/* ------------------------------------------------------------ the safety line --- */
{
  ok('[safety] the registry and the rules carry the safety line word for word', reg.safety_line === SAFETY && rules.safety_line === SAFETY);
  ok('[safety] the safety line is visible in the built page: the drops panel, the legend row, and the stop popup', (() => {
    const panel = page.match(/<p class="td-safety" id="dropSafety">([^<]*)<\/p>/);
    const legend = page.match(/data-legend="drops">[\s\S]*?<\/div>/);
    return !!panel && panel[1] === SAFETY && !!legend && legend[0].includes(SAFETY) && uiJs.includes('TDG.safetyLine') && /td-safety/.test(uiJs);
  })());
  ok('[safety] the page also says: public paths only, away from water, rail and construction, the pin is not a surveyed entrance, and a human must confirm a place before any drop is offered elsewhere',
    page.includes('Use public paths and sidewalks only') && page.includes('not a surveyed entrance') && /A human must visit and confirm a place/.test(JSON.stringify(reg.honesty)));
}

/* ---------------------------------------------------- GeoPose anchors --- */
{
  const bad = [];
  if (poseDoc.poses.length !== reg.stops.length) bad.push('pose count differs from stop count');
  for (const st of reg.stops) {
    const p = poseDoc.poses.find((x) => x.subject.ref === st.geopose_ref);
    if (!p) { bad.push(`${st.id}: no pose`); continue; }
    const pos = p.geopose.position;
    if (pos.lat !== st.lat || pos.lon !== st.lng || pos.h !== 0) bad.push(`${st.id}: pose position differs`);
    const o = p.geopose.orientation;
    if (o.yaw !== 0 || o.pitch !== 0 || o.roll !== 0) bad.push(`${st.id}: orientation is not the zero placeholder`);
    if (!/^UNKNOWN/.test(p.provenance.h_provenance) || !/^UNKNOWN/.test(p.provenance.orientation_provenance)) bad.push(`${st.id}: UNKNOWN sidecar missing`);
    if (p.provenance.position_horizontal !== st.coordinate_provenance) bad.push(`${st.id}: pose provenance differs`);
    if (Object.keys(p.geopose).sort().join() !== 'orientation,position' || Object.keys(pos).sort().join() !== 'h,lat,lon') bad.push(`${st.id}: not the Basic-YPR shape`);
  }
  ok(`[geopose] ${poseDoc.poses.length} GeoPose 1.0 Basic-YPR anchors, one per stop, at the stop's coordinate, height and heading zero beside an UNKNOWN sidecar`, bad.length === 0, bad);
  ok('[geopose] same encoding, media type and CRS as spatial/registry/geopose.json, which keeps its own 89 poses untouched',
    poseDoc.encoding === geopose.encoding && poseDoc.media_type === geopose.media_type && poseDoc.crs === geopose.crs
    && geopose.poses.length === geopose.counts.total && !geopose.poses.some((p) => p.subject.kind === 'training-drop-stop'));
}

/* --------------------------------------------------- geolocation code: static --- */
const FORBID = [['fetch(', /\bfetch\s*\(/], ['XMLHttpRequest', /XMLHttpRequest/], ['sendBeacon', /sendBeacon/], ['WebSocket', /WebSocket/], ['EventSource', /EventSource/],
  ['localStorage', /localStorage/], ['sessionStorage', /sessionStorage/], ['indexedDB', /indexedDB/], ['document.cookie', /document\.cookie/], ['caches', /\bcaches\b/],
  ['new Image', /new\s+Image/], ['importScripts', /importScripts/], ['postMessage', /postMessage/], ['navigator.share', /navigator\.share/], ['window.open', /window\.open/],
  ['location assign', /location\.(href|assign|replace)\s*[=(]/], ['<img/<script injection', /createElement\(\s*['"](img|script|iframe)/]];
{
  const strip = (s) => s.replace(/\/\*[\s\S]*?\*\//g, '').replace(/(^|[^:'"])\/\/.*$/gm, '$1');
  const hits = [];
  for (const [file, src] of [['play.js', strip(playJs)], ['ui.js', strip(uiJs)]]) for (const [name, re] of FORBID) if (re.test(src)) hits.push(`${file}: ${name}`);
  ok('[location] the on-device code (play.js and ui.js) calls no fetch, XHR, beacon, socket, storage, cookie, cache, image or navigation', hits.length === 0, hits);
  const gs = (s) => (s.match(/getCurrentPosition|watchPosition|navigator\.geolocation|\.geolocation\b/g) || []).length;
  ok('[location] the device\'s position is read only inside play.js; ui.js never touches coords, latitude, longitude or the geolocation object', gs(playJs) > 0 && gs(uiJs) === 0 && !/\bcoords\b|latitude|longitude/.test(uiJs));
  const page2 = page.replace(/<script id="data"[\s\S]*?<\/script>/, '');
  const around = (re) => [...page2.matchAll(re)].length;
  ok('[location] no other script on the page reads the device position (geolocation appears only in the inlined play.js)', around(/getCurrentPosition|watchPosition/g) === (playJs.match(/getCurrentPosition|watchPosition/g) || []).length);
  const pm = page.match(/<script id="trainingDropsPlay">([\s\S]*?)<\/script>/);
  const um = page.match(/\/\* TRAINING-DROPS BEGIN \*\/\n([\s\S]*?)\n\/\* TRAINING-DROPS END \*\//);
  ok('[location] the page inlines play.js and ui.js exactly as the files stand (what was scanned is what ships)', !!pm && pm[1].trim() === playJs.trim() && !!um && um[1].trim() === uiJs.trim());
  const panelHtml = page.match(/<section class="panel tc-panel" id="drops"[\s\S]*?<\/section>/)[0];
  ok('[location] the drops panel says the position is read on the device, nothing is stored or sent, and reloading forgets the open drops', /read on the device/.test(panelHtml) && /not stored, not written to any storage, and not sent anywhere/.test(panelHtml) && /Reloading the page forgets which drops you opened/.test(panelHtml));
  ok('[location] the position is not in a test hook: window.__geoplay exposes ids, words and hrefs only', /window\.__geoplay = \(\) => \(\{[\s\S]*?\}\);/.test(uiJs) && !/__geoplay[\s\S]{0,900}(latitude|longitude|\.lat\b|\.lng\b)/.test(uiJs.slice(uiJs.indexOf('window.__geoplay'))));
}

/* ------------------------------------------- geolocation code: on-device logic --- */
const loadPlay = (traps) => {
  const ctx = vm.createContext({
    fetch: (...a) => { traps.push(['fetch', a]); throw new Error('fetch'); },
    XMLHttpRequest: class { constructor() { traps.push(['xhr']); throw new Error('xhr'); } },
    localStorage: new Proxy({}, { get: (_, k) => { traps.push(['localStorage', k]); throw new Error('storage'); } }),
    sessionStorage: new Proxy({}, { get: (_, k) => { traps.push(['sessionStorage', k]); throw new Error('storage'); } }),
    indexedDB: new Proxy({}, { get: (_, k) => { traps.push(['indexedDB', k]); throw new Error('idb'); } }),
    document: { get cookie() { traps.push(['cookie-read']); return ''; }, set cookie(v) { traps.push(['cookie-write', v]); } },
    console: { log() {}, error() {} }, Math, Number, Object, JSON, Array,
  });
  return vm.runInContext(playJs + '\nTrainingDrops;', ctx);
};
{
  const traps = [];
  const TD = loadPlay(traps);
  const stop = { id: 's', lat: 30.0288, lng: -90.0664, radius_m: 120 };
  const lim = { accuracy_max_m: 100 };
  const at = (north_m, acc) => ({ lat: stop.lat + north_m / 111195, lng: stop.lng, accuracy: acc });
  const r = (north, acc = 20) => TD.unlockCheck(stop, at(north, acc), lim).state;
  ok('[unlock] a fix on the pin, inside the radius, and one metre inside it unlock', r(0) === 'in-range' && r(119) === 'in-range');
  ok('[unlock] a fix one metre outside the radius, far away, or on the other side of the planet does not', r(122) === 'out-of-range' && r(5000) === 'out-of-range' && TD.unlockCheck(stop, { lat: -30, lng: 90, accuracy: 5 }, lim).state === 'out-of-range');
  ok('[unlock] a fix whose accuracy circle is wider than the limit never unlocks, even on the pin', r(0, 101) === 'too-coarse' && r(0, 100) === 'in-range' && TD.unlockCheck(stop, { lat: stop.lat, lng: stop.lng }, lim).state === 'too-coarse' && r(0, NaN) === 'too-coarse');
  ok('[unlock] a fix that is not a position (NaN, missing, out of range) unlocks nothing', ['no-fix'].every((w) => TD.unlockCheck(stop, { lat: NaN, lng: 1, accuracy: 5 }, lim).state === w && TD.unlockCheck(stop, null, lim).state === w && TD.unlockCheck(stop, { lat: 95, lng: 1, accuracy: 5 }, lim).state === w));
  ok('[unlock] distance is the great-circle distance (one degree of latitude is 111 195 m +/- 50)', Math.abs(TD.distanceM(0, 0, 1, 0) - 111195) < 50 && TD.distanceM(10, 20, 10, 20) === 0);
  const sv = TD.survey([{ id: 'far', lat: 40, lng: -100, radius_m: 75 }, stop], at(30), lim);
  ok('[unlock] a survey is nearest first and returns ids, states and distances rounded to 10 m', sv[0].id === 's' && sv[1].id === 'far' && sv.every((x) => Object.keys(x).sort().join() === 'distance_m,id,state') && sv[0].distance_m % 10 === 0 && sv[0].distance_m === 30);

  const handlers = (log) => ({ onSurvey: (l) => log.push(['survey', JSON.stringify(l)]), onStatus: (w) => log.push(['status', w]) });
  const mockNav = (script) => { const calls = []; return { calls, geolocation: { watchPosition(ok, err, opts) { calls.push(['watch', opts]); script(ok, err); return 7; }, clearWatch(id) { calls.push(['clear', id]); }, getCurrentPosition() { calls.push(['get']); } } }; };
  const SECRET = { latitude: 30.02881234, longitude: -90.06641234, accuracy: 15 };

  let log = [], nav = mockNav((ok) => ok({ coords: SECRET }));
  let loc = TD.createLocator(nav, lim, [stop], handlers(log));
  loc.start();
  ok('[locator] start asks the device once (the browser shows its own prompt), then reports the in-range stop as a rounded survey', nav.calls.filter((c) => c[0] === 'watch').length === 1 && log.some((l) => l[0] === 'survey' && JSON.parse(l[1])[0].state === 'in-range') && log[0][1] === 'asking' && loc.active());
  ok('[locator] the position itself never leaves the locator: no handler argument holds the latitude or longitude', log.length > 0 && !/30\.02881234|90\.06641234|30\.0288123|90\.0664123/.test(JSON.stringify(log)));
  loc.stop();
  ok('[locator] stop clears the watch and reports off', nav.calls.some((c) => c[0] === 'clear' && c[1] === 7) && log.at(-1)[1] === 'off' && !loc.active());

  log = []; nav = mockNav((ok, err) => err({ code: 1 }));
  loc = TD.createLocator(nav, lim, [stop], handlers(log));
  const started = loc.start();
  ok('[locator] a refused permission falls back: status denied, the watch is cleared, nothing is unlocked, the locator is not active', log.some((l) => l[1] === 'denied') && !log.some((l) => l[0] === 'survey') && nav.calls.some((c) => c[0] === 'clear') && !loc.active() && started === false);
  log = []; nav = { };
  loc = TD.createLocator(nav, lim, [stop], handlers(log));
  ok('[locator] a browser with no geolocation reports unsupported and does not throw', loc.start() === false && log[0][1] === 'unsupported');
  log = []; nav = mockNav((ok, err) => err({ code: 2 }));
  loc = TD.createLocator(nav, lim, [stop], handlers(log));
  loc.start();
  ok('[locator] a position error that is not a refusal reports unavailable and keeps the watch for a later fix', log.some((l) => l[1] === 'unavailable') && loc.active());
  ok('[locator] across all of the above, the module made zero network, storage or cookie calls', traps.length === 0, traps.map((t) => t.join(' ')));
}

/* -------------------------------------------------------------- AR --- */
{
  const arSrc = (s) => s.replace(/\/\*[\s\S]*?\*\//g, '');
  ok('[ar] no AR is built or claimed: the registry marks it PROPOSED, the page says so, and neither script touches WebXR, a camera or getUserMedia',
    reg.ar.status === 'PROPOSED' && /data-ar-status="PROPOSED">AR is PROPOSED\./.test(page) && !/requestSession|immersive-ar|navigator\.xr|getUserMedia|mediaDevices/.test(arSrc(playJs) + arSrc(uiJs)));
}

/* -------------------------------------------------- wiring and honesty --- */
{
  const data = JSON.parse(page.match(/<script id="data" type="application\/json">([\s\S]*?)<\/script>/)[1]);
  ok('[page] the geomap data carries the registry\'s stops and its source stamp', data.geoplay && data.geoplay.stops.length === reg.stops.length && data.geoplay.sourceStamp === reg.source_stamp
    && data.geoplay.stops.every((s) => { const r = reg.stops.find((x) => x.id === s.id); return r && r.lat === s.lat && r.lng === s.lng && r.radius_m === s.radius_m; }));
  ok('[page] the drops panel, its bar button, its layer toggle and its legend row exist', /data-panel="drops"/.test(page) && /id="drops"/.test(page) && /key: 'drops'/.test(page) && /data-legend="drops"/.test(page) && /id="dropLocate"/.test(page) && /id="dropHere"/.test(page));
  const panelHtml2 = page.match(/<section class="panel tc-panel" id="drops"[\s\S]*?<\/section>/)[0];
  ok('[page] the drops panel says play, simulated and unverified, no partner, and that the place hosts nothing', /Training drops are play\./.test(panelHtml2) && /unverified general practice/.test(panelHtml2) && /not a partner/.test(panelHtml2) && /hosts nothing/.test(panelHtml2));
  const mine = [page.match(/<section class="panel tc-panel" id="drops"[\s\S]*?<\/section>/)[0], uiJs, playJs, reg.honesty.play, reg.honesty.privacy, reg.honesty.no_hosting, reg.honesty.safety_more, reg.ar.claim].join('\n');
  const leak = mine.match(/\$SP|\/tmp\/|\/home\/|\/root\/|memory\/|\bconsole\b|GEOPLAY|[Cc]odename|\bagent\b/);
  ok('[page] the drops code and words carry no internal reference: no scratch path, no console or memory mention, no team codename (and none anywhere in the built page)', !leak && !/GEOPLAY/.test(page), [leak && leak[0]]);
  ok('[page] the phone layout rule holds: the panel is capped at the viewport width', /\.panel\{[^}]*width:min\(380px,calc\(100vw - 28px\)\)/.test(page));
}
ok('[source] the builder is the only thing that writes the registry (build.py reads, never fetches, and holds no default on a registry field)', (() => {
  const b = read('geoplay/build.py').replace(/#.*$/gm, '');
  return !/urllib|requests|socket|http\.client/.test(b) && !/\.get\(/.test(b) && b.includes('def need(d, k, where):');
})());

/* ------------------------------------------------------------- browser --- */
async function loadPlaywright() {
  if (process.env.PLAYWRIGHT_MODULE) return import(process.env.PLAYWRIGHT_MODULE);
  try { return await import('playwright'); } catch { /* try the global package */ }
  const root = execFileSync('npm', ['root', '-g'], { encoding: 'utf8' }).trim();
  return import(pathToFileURL(join(root, 'playwright', 'index.mjs')).href);
}
if (WANT_BROWSER) {
  const origin = originArg ? originArg.slice(9) : null;
  if (!origin) { bad++; console.log('FAIL [browser] pass --origin=http://127.0.0.1:PORT of a server rooted at the tree'); }
  else {
    const { chromium } = await loadPlaywright();
    const browser = await chromium.launch({ executablePath: process.env.CHROMIUM_PATH || undefined, args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader'] });
    const url = origin + '/web/trade_craft_geomap.html';
    const target = reg.stops.find((s) => s.class === 'public-park') || reg.stops[0];
    const other = reg.stops.find((s) => s.id !== target.id);
    const fix = { latitude: target.lat + 0.00031, longitude: target.lng - 0.00027, accuracy: 18 };   // ~45 m from the pin
    const far = { latitude: other.lat + 0.5, longitude: other.lng + 0.5, accuracy: 18 };
    const probe = `(() => { const hits = []; const keys = ${JSON.stringify([String(fix.latitude).slice(0, 8), String(fix.longitude).slice(0, 9), String(far.latitude).slice(0, 8), String(far.longitude).slice(0, 8)])};
      const has = (v) => { try { const s = typeof v === 'string' ? v : JSON.stringify(v); return keys.some((k) => s.includes(k)); } catch { return false; } };
      const of = window.fetch; window.fetch = function (...a) { if (has(a)) hits.push('fetch'); return of.apply(this, a); };
      const ox = XMLHttpRequest.prototype.open; XMLHttpRequest.prototype.open = function (m, u) { if (has(u)) hits.push('xhr'); return ox.apply(this, arguments); };
      const os = XMLHttpRequest.prototype.send; XMLHttpRequest.prototype.send = function (b) { if (has(b)) hits.push('xhr-body'); return os.apply(this, arguments); };
      if (navigator.sendBeacon) { const ob = navigator.sendBeacon.bind(navigator); navigator.sendBeacon = (u, d) => { hits.push('beacon'); return ob(u, d); }; }
      const sp = Storage.prototype.setItem; Storage.prototype.setItem = function (k, v) { if (has(k) || has(v)) hits.push('storage:' + k); return sp.apply(this, arguments); };
      window.__leaks = () => hits.slice(); })();`;
    const run = async (label, ctxOpts, body) => {
      const ctx = await browser.newContext({ viewport: { width: 390, height: 844 }, ...ctxOpts });
      const p = await ctx.newPage();
      const errs = [], reqs = [];
      p.on('pageerror', (e) => errs.push(e.message));
      p.on('request', (r) => reqs.push(r.url()));
      await p.addInitScript(probe);
      await p.goto(url, { waitUntil: 'load' });
      await p.waitForFunction(() => window.__geomap && window.__geomap().loaded && window.__geoplay && window.__geoplay().layer, null, { timeout: 40000 });
      await p.waitForTimeout(500);
      await body(p, errs, reqs, ctx);
      await ctx.close();
    };
    // run 1: permission granted, a position ~45 m from the park pin
    await run('granted', { permissions: ['geolocation'], geolocation: fix }, async (p, errs, reqs, ctx) => {
      const before = await p.evaluate(() => window.__geoplay());
      ok('[browser] before any press, nothing is unlocked and no position was asked for (the prompt is opt-in)', before.open.length === 0 && before.status === 'off' && before.locks === reg.counts.drops && before.unlocks.length === 0 && before.active === false);
      await p.click('[data-panel="drops"]');
      ok('[browser] the safety line is visible in the open drops panel', await p.isVisible('#dropSafety') && (await p.textContent('#dropSafety')).trim() === SAFETY);
      await p.click('#dropLocate');
      await p.waitForFunction((id) => window.__geoplay().open.includes(id), target.id, { timeout: 15000 });
      if (shotArg) {
        await p.waitForTimeout(500); await p.screenshot({ path: join(shotArg.slice(7), 'panel.png') });
        await p.click(`[data-drop-fly="${target.id}"]`); await p.click('[data-panel="drops"]'); await p.waitForTimeout(4500);
        await p.screenshot({ path: join(shotArg.slice(7), 'map.png') }); await p.click('[data-panel="drops"]');
      }
      const mid = await p.evaluate(() => window.__geoplay());
      ok(`[browser] with a mocked position ~45 m from "${target.name}", that stop unlocks by the device and the others stay locked`, mid.open.length === 1 && mid.open[0] === target.id && mid.via[target.id] === 'device' && mid.unlocks.length === target.drops.length && mid.locks === reg.counts.drops - target.drops.length && mid.status === 'watching');
      ok('[browser] the unlocked drops are the existing tasks\' own launch links', mid.unlocks.length > 0 && mid.unlocks.every((h) => target.drops.some((d) => { const t = TASK[d.task].launch.href; return h === t.replace(/^web\//, '') || h === '../' + t; })), mid.unlocks);
      await ctx.setGeolocation(far);
      await p.waitForFunction((id) => window.__geoplay().states[id] === 'out-of-range', target.id, { timeout: 15000 }).catch(() => {});
      const moved = await p.evaluate(() => window.__geoplay());
      ok('[browser] moving the mocked device far away reports out-of-range for the stop (the open drop stays open for this visit; nothing re-locks silently)', moved.states[target.id] === 'out-of-range' && moved.open.includes(target.id));
      await p.click('#dropLocate');
      const off = await p.evaluate(() => window.__geoplay());
      ok('[browser] pressing again stops the locator: status off, no states held', off.status === 'off' && off.active === false && Object.keys(off.states).length === 0);
      const leaks = await p.evaluate(() => window.__leaks());
      const urlLeak = reqs.filter((u) => [String(fix.latitude).slice(0, 8), String(fix.longitude).slice(0, 9), String(far.latitude).slice(0, 8)].some((k) => u.includes(k)));
      const store = await p.evaluate(() => JSON.stringify([Object.entries(localStorage), Object.entries(sessionStorage), document.cookie]));
      ok('[browser] the mocked coordinates reached no fetch, XHR, beacon, storage write, cookie or request URL', leaks.length === 0 && urlLeak.length === 0 && !store.includes(String(fix.latitude).slice(0, 8)) && !store.includes(String(fix.longitude).slice(0, 8)), [...leaks, ...urlLeak, store.slice(0, 120)]);
      ok('[browser] no page error', errs.length === 0, errs);
    });
    // run 2: permission denied -> manual "I am here"
    await run('denied', { permissions: [] }, async (p, errs, reqs) => {
      await p.click('[data-panel="drops"]');
      await p.evaluate(() => { navigator.geolocation.watchPosition = (ok, err) => { setTimeout(() => err({ code: 1, message: 'denied' }), 10); return 1; }; navigator.geolocation.clearWatch = () => {}; });
      await p.click('#dropLocate');
      await p.waitForFunction(() => window.__geoplay().status === 'denied', null, { timeout: 10000 });
      const d = await p.evaluate(() => window.__geoplay());
      ok('[browser] a refused permission leaves everything locked and shows the manual fallback', d.open.length === 0 && d.active === false && /pick a place/.test(await p.textContent('#dropStatus')));
      await p.selectOption('#dropHere', other.id);
      await p.waitForFunction((id) => window.__geoplay().open.includes(id), other.id, { timeout: 10000 });
      const m = await p.evaluate(() => window.__geoplay());
      ok('[browser] the manual "I am here" pick opens that stop, recorded as manual, and only that stop', m.open.length === 1 && m.via[other.id] === 'manual' && m.unlocks.length === other.drops.length);
      const hasSafety = await p.evaluate(() => document.getElementById('dropSafety').textContent.trim());
      ok('[browser] the safety line is still shown after the manual pick, and no storage or request carries a position', hasSafety === SAFETY && (await p.evaluate(() => window.__leaks())).length === 0 && errs.length === 0, errs);
    });
    await browser.close();
  }
}

console.log(`${n} ok, ${bad} failed`);
process.exit(bad ? 1 : 0);
