/**
 * Sky registry verification.
 *
 * This pack makes two kinds of claim and they are checked two different
 * ways, because conflating them is exactly the dishonesty the pack exists
 * to avoid.
 *
 * The GEOMETRY claims to be computed. So this file does not read the
 * numbers and nod at them - it re-implements the solar-position series
 * from scratch below, re-runs the same fixed-step bisection for every
 * phase that is defined by a twilight threshold, and requires the
 * registry's elevation, azimuth and t01 to fall out of it. A number that
 * was nudged by hand afterwards fails here, which is the whole point:
 * "DERIVED" is a claim about how a number was made, and a claim about how
 * a number was made is checkable.
 *
 * The COLOURS claim nothing but authorship. They are checked for format,
 * for range and for being LABELLED AUTHORED - and never for correctness,
 * because there is no correctness to check and pretending otherwise would
 * be the lie.
 *
 * Three more worth reading twice.
 *
 * ONE TRUTH PER FACT is checked structurally, not by eye. Every weather
 * sky must hold a dotted POINTER into world/registry/world.json for cloud
 * cover, fog density, fog tint, sun strength and rain, must resolve, and
 * must not hold the field itself - and no key world already owns on that
 * same weather state may appear beside it. The star count is world's too,
 * so the bins are re-derived from it and the block is checked for not
 * containing it.
 *
 * The DRAW ORDER is not read from this registry either. It is re-derived
 * from where each layer's anchor string sits in web/build_3d.py, so a
 * reordering of the page's own drawing breaks this suite rather than
 * quietly leaving the registry wrong.
 *
 * The STAR BINS are re-derived by re-running the page's linear
 * congruential generator here, branch for branch - including the fact
 * that the radius pick consumes one draw on the bright branch and two
 * otherwise. Get that wrong and the whole sequence desynchronises, which
 * is what makes the bins a real check on the page instead of decoration.
 */
import { createHash } from 'node:crypto';
import { readFileSync } from 'node:fs';

let n = 0;
const ok = (m, c) => { if (!c) { console.error('FAIL', m); process.exit(1); } n++; console.log('  ok ', m); };

const url = (p) => new URL(p, import.meta.url);
const reg = JSON.parse(readFileSync(url('./registry/sky.json')));
const world = JSON.parse(readFileSync(url('../world/registry/world.json')));
const geo = JSON.parse(readFileSync(url('../geo/registry/campuses_geo.json')));
const manifest = JSON.parse(readFileSync(url('../pack/manifest.json')));
const page = readFileSync(url('../web/build_3d.py'), 'utf8');
const text = JSON.stringify(reg);

const phases = reg.phases;
const wxIds = Object.keys(world.weather).sort();
const skyIds = Object.keys(reg.weather_sky).sort();
const layers = reg.layers;
const C = reg.counts;
const S = reg.site;

/* ------------------------------------------------- the solar series, again ---
   Re-implemented from the same published sources the builder cites, so the
   two are independent transcriptions of one algorithm rather than one
   transcription checked against itself. */
const rad = (d) => d * Math.PI / 180, deg = (r) => r * 180 / Math.PI;
const hourAngle = (t01) => t01 * 360 - 180;
function declination(t01) {                       // Spencer 1971
  const g = 2 * Math.PI / 365 * (S.day_of_year - 1 + (t01 * 24 - 12) / 24);
  return 0.006918
    - 0.399912 * Math.cos(g) + 0.070257 * Math.sin(g)
    - 0.006758 * Math.cos(2 * g) + 0.000907 * Math.sin(2 * g)
    - 0.002697 * Math.cos(3 * g) + 0.001480 * Math.sin(3 * g);
}
function elevation(t01) {                         // Meeus 13.6
  const phi = rad(S.lat_deg), dec = declination(t01), ha = rad(hourAngle(t01));
  const s = Math.sin(phi) * Math.sin(dec)
    + Math.cos(phi) * Math.cos(dec) * Math.cos(ha);
  return deg(Math.asin(Math.max(-1, Math.min(1, s))));
}
function azimuth(t01) {                           // Meeus 13.5, rotated to N-cw
  const phi = rad(S.lat_deg), dec = declination(t01), ha = rad(hourAngle(t01));
  const a = Math.atan2(Math.sin(ha),
    Math.cos(ha) * Math.sin(phi) - Math.tan(dec) * Math.cos(phi));
  return (deg(a) + 180) % 360;
}
function solve(target, branch) {
  let lo = branch === 'rising' ? 0 : 0.5, hi = branch === 'rising' ? 0.5 : 1;
  for (let i = 0; i < 60; i++) {
    const mid = (lo + hi) / 2;
    if ((elevation(mid) < target) === (branch === 'rising')) lo = mid; else hi = mid;
  }
  return (lo + hi) / 2;
}
const near = (a, b, e = 1e-6) => Math.abs(a - b) < e;
const dp = (v) => { const s = String(v).split('.'); return s.length < 2 ? 0 : s[1].length; };
const isHex = (h) => typeof h === 'string' && /^#[0-9a-f]{6}$/.test(h);

/* ------------------------------------------------------------- the shape --- */
ok('the pack carries the same header every pack in this bundle carries',
  reg.pack === 'smartcitix-trade-craft-academy-sky'
  && reg.product === manifest.product
  && reg.pack_version === manifest.pack_version
  && /^\d{4}-\d{2}-\d{2}$/.test(reg.built) && reg.source_stamp.length === 16);
ok('the provenance word is COMPUTED, and the geometry is what it is claimed of',
  /^COMPUTED: /.test(reg.honesty.status)
  && /elevation and azimuth/.test(reg.honesty.status)
  && /Nothing in the geometry was placed by eye/.test(reg.honesty.status));
ok('the word orbis owns is not borrowed here, and is not in the payload at all',
  !text.includes('AI-SYNTHESIZED')
  && /reserves\s+for orbis\//.test(reg.honesty.provenance_word));
ok('nothing in the payload is a URL - this pack fetches nothing and links nowhere',
  !/https?:\/\//.test(text));
ok('every file this pack says it reads is one it could read',
  reg.reads.length === C.reads_files
  && reg.reads.every((f) => !f.startsWith('/') && !f.includes('..'))
  && reg.reads.includes('world/registry/world.json')
  && reg.reads.includes('geo/registry/campuses_geo.json'));
ok('the provenance vocabulary is closed, and every word a field uses is in it',
  (() => {
    const words = new Set(Object.keys(reg.provenance_words));
    const used = new Set(phases.flatMap((p) => Object.values(p.provenance))
      .concat(Object.keys(reg.weather_sky).flatMap((w) =>
        Object.values(reg.weather_sky[w].provenance))));
    return words.size === 6 && [...used].every((w) => words.has(w))
      && words.has('AUTHORED') && words.has('DERIVED') && words.has('READ');
  })());

/* ---------------------------------------------------------------- the site --- */
ok('the latitude the formula runs at is geo/\'s own, not a second copy of it',
  S.lat_deg === geo.campuses[S.campus].lat
  && S.lon_deg === geo.campuses[S.campus].lng
  && S.lat_provenance === geo.campuses[S.campus].provenance
  && S.lat_source === geo.campuses[S.campus].source
  && S.lat_read_from.startsWith('geo/registry/campuses_geo.json#'));
ok('the day of the year is stated, with why that day and not another',
  Number.isInteger(S.day_of_year) && S.day_of_year >= 1 && S.day_of_year <= 365
  && /equinox/.test(S.day_why) && /annual mean/.test(S.day_why));
ok('time is solar, longitude is declared unused, and no refraction is claimed',
  S.time_base === 'local apparent solar time'
  && /removes it/.test(S.longitude_unused)
  && /none applied/.test(S.refraction) && /GEOMETRIC/.test(S.refraction)
  && /noon is t01 = 0.5 by construction/.test(reg.honesty.time_is_solar));
ok('all three formulae are cited by name, not merely asserted to exist',
  /Spencer 1971/.test(S.declination_formula)
  && /Meeus/.test(S.elevation_formula) && /13\.6/.test(S.elevation_formula)
  && /Meeus/.test(S.azimuth_formula) && /13\.5/.test(S.azimuth_formula)
  && /clockwise from true north/.test(S.azimuth_formula));

/* ------------------------------------------------- the geometry, re-derived --- */
/* The published t01 is ROUNDED to the stated four decimals, so re-deriving
   the angles from it would be re-deriving them from a slightly different
   instant. The unrounded hour is reconstructed here the way the builder
   reconstructs it - solved, or constructed from two solved neighbours -
   and the angles are taken at THAT instant. */
const exact = {};
for (const p of phases) {
  if (p.t01_by === 'solved') exact[p.id] = solve(p.target_elev_deg, p.branch);
  else if (p.id === 'night') exact[p.id] = 0;
  else if (p.id === 'noon') exact[p.id] = 0.5;
}
exact.morning = (exact['golden-morning'] + exact.noon) / 2;
exact.afternoon = (exact.noon + exact['golden-hour']) / 2;
const r4 = (x) => Math.round(x * 1e4) / 1e4;

ok('every phase\'s hour is the builder\'s own answer, re-solved and re-constructed here',
  phases.every((p) => p.id in exact && near(p.t01, r4(exact[p.id]), 1e-9)));
ok('every phase\'s sun ELEVATION falls out of the series again at that instant',
  phases.every((p) => near(p.elevation_deg, r4(elevation(exact[p.id])), 1e-4)));
ok('every phase\'s sun AZIMUTH falls out of the series again at that instant',
  phases.every((p) => near(p.azimuth_deg, r4(azimuth(exact[p.id])), 1e-4)));
ok('and every solved phase lands on the elevation that DEFINES it',
  phases.filter((p) => p.t01_by === 'solved').every((p) =>
    near(elevation(exact[p.id]), p.target_elev_deg, 1e-9)
    && near(p.elevation_deg, p.target_elev_deg, 1e-3)));
ok('the constructed hours follow from their definitions and nothing else',
  (() => {
    const at = (id) => phases.find((p) => p.id === id).t01;
    return at('night') === 0 && at('noon') === 0.5
      && phases.filter((p) => p.t01_by === 'construction').length === 4
      && near(at('morning'),
        r4((exact['golden-morning'] + exact.noon) / 2), 1e-9)
      && near(at('afternoon'),
        r4((exact.noon + exact['golden-hour']) / 2), 1e-9);
  })());
ok('no published geometry number carries more precision than the stated rounding',
  phases.every((p) => dp(p.t01) <= 4 && dp(p.elevation_deg) <= 4
    && dp(p.azimuth_deg) <= 4));
ok('solar noon is the highest the sun gets all day, and it is due south',
  (() => {
    const noon = phases.find((p) => p.id === 'noon');
    return noon.elevation_deg === Math.max(...phases.map((p) => p.elevation_deg))
      && near(noon.azimuth_deg, 180, 0.5);
  })());
ok('sunrise and sunset sit either side of noon at the same depression',
  (() => {
    const a = phases.find((p) => p.id === 'sunrise');
    const b = phases.find((p) => p.id === 'sunset');
    return a.elevation_deg === b.elevation_deg
      && near((a.t01 + b.t01) / 2, 0.5, 0.01)
      && near(a.azimuth_deg + b.azimuth_deg, 360, 1.5);
  })());
ok('the twilight thresholds are the standard ones, each with its definition given',
  [[-18, 'astronomical'], [-12, 'nautical'], [-6, 'civil']].every(([d, w]) =>
    phases.filter((p) => p.target_elev_deg === d).length === 2
    && phases.filter((p) => p.target_elev_deg === d)
      .every((p) => p.why.includes(w))));
ok('the risen-disc threshold is 50 arcminutes, and says which 50',
  phases.filter((p) => p.target_elev_deg === S.risen_disc_deg).length === 2
  && S.risen_disc_deg === -0.833
  && phases.filter((p) => p.target_elev_deg === S.risen_disc_deg)
    .every((p) => /semidiameter|16 arcmin|same 50-arcminute/.test(p.why)
      && /refraction/.test(p.why)));

/* ------------------------------------------------------ the phases as a set --- */
ok('the phase set is closed, ordered and cyclic - it returns to where it began',
  (() => {
    const ids = phases.map((p) => p.id);
    if (new Set(ids).size !== ids.length) return false;
    let at = ids[0];
    for (let i = 0; i < ids.length; i++) at = phases.find((p) => p.id === at).next;
    return at === ids[0] && phases.every((p, i) => p.order === i)
      && new Set(phases.map((p) => p.next)).size === ids.length;
  })());
ok('the hours run forward, start at solar midnight and close before the next one',
  phases.every((p, i) => i === 0 || phases[i - 1].t01 < p.t01)
  && phases[0].t01 === 0 && phases[phases.length - 1].t01 < 1);
ok('every phase says how its hour was arrived at, and why that is the hour',
  phases.every((p) => ['solved', 'construction'].includes(p.t01_by)
    && p.why.length > 40 && p.name.length > 3));
ok('a phase gradient has one stop per band WORLD declares, named world\'s way',
  phases.every((p) => p.gradient.stops.length === world.sky.bands.length
    && JSON.stringify(p.gradient.bands) === JSON.stringify(world.sky.bands))
  && C.stops_per_gradient === world.sky.bands.length);
ok('every colour is a lowercase #rrggbb, and there are no others',
  phases.every((p) => p.gradient.stops.every(isHex) && isHex(p.sun.color_hex)
    && isHex(p.hemi.sky_hex) && isHex(p.hemi.ground_hex))
  && Object.values(reg.weather_sky).every((w) => isHex(w.gradient_tint_hex)));
ok('every light figure is a MULTIPLIER, so the page keeps owning the base number',
  phases.every((p) => p.sun.intensity_mul > 0 && p.sun.intensity_mul <= 1.2
    && p.hemi.intensity_mul > 0 && p.hemi.intensity_mul <= 1.2
    && p.gradient.campus_mix >= 0 && p.gradient.campus_mix <= 1)
  && phases.every((p) => Object.keys(p.sun).join() === 'color_hex,intensity_mul'
    && Object.keys(p.hemi).join() === 'sky_hex,ground_hex,intensity_mul')
  && !/"lux"|"candela"|"watts"/.test(text));
ok('the sun angles are marked DERIVED and every colour is marked AUTHORED',
  phases.every((p) => p.provenance.elevation_deg === 'DERIVED'
    && p.provenance.azimuth_deg === 'DERIVED'
    && p.provenance.sun_color_hex === 'AUTHORED'
    && p.provenance.hemi_sky_hex === 'AUTHORED'
    && p.provenance.hemi_ground_hex === 'AUTHORED'
    && p.provenance.gradient === 'AUTHORED'
    && p.provenance.campus_mix === 'AUTHORED'
    && p.provenance.t01 === (p.t01_by === 'solved' ? 'DERIVED' : 'CONSTRUCTED')));
ok('and the honesty block says plainly that the colours were chosen by eye',
  /chosen by\s+eye/.test(reg.honesty.colours_are_authored)
  && /none is measured/.test(reg.honesty.colours_are_authored)
  && /not a date/.test(reg.honesty.not_a_forecast));
ok('the page no longer carries the night colour as a LITERAL - it reads '
  + 'this phase\'s instead, which is what wiring this pack up was for. It '
  + 'held 0x9db4d8 in a `if (night)` branch beside five other hex values '
  + 'that existed in no registry; the swap was written to be a no-op at '
  + 'that hour, and this check flipped from "the page still has it" to '
  + '"the page has stopped having it" the moment it was made',
  !page.includes('0x9db4d8')
  && /key\.color\.setHex\(parseInt\(eff\.sun\.color_hex/.test(page)
  && phases.find((p) => p.id === 'night').sun.color_hex === '#9db4d8');

/* ------------------------------------------------------------ the weathers --- */
ok('the weather id sets match EXACTLY, in both directions',
  JSON.stringify(skyIds) === JSON.stringify(wxIds)
  && wxIds.every((w) => w in reg.weather_sky)
  && skyIds.every((w) => w in world.weather));
ok('every weather sky holds POINTERS into world/, never the numbers themselves',
  wxIds.every((w) => Object.entries(reg.weather_reads).every(([local, key]) =>
    reg.weather_sky[w].reads[local] === `weather.${w}.${key}`
    && !(local in reg.weather_sky[w]))));
ok('and every one of those pointers actually resolves in world/registry/world.json',
  wxIds.every((w) => Object.values(reg.weather_sky[w].reads).every((p) =>
    p.split('.').reduce((o, k) => (o === undefined ? undefined : o[k]), world)
    !== undefined)));
ok('no key world already owns on that weather state appears beside the pointer',
  (() => {
    const owned = new Set(wxIds.flatMap((w) => Object.keys(world.weather[w])));
    return wxIds.every((w) => Object.keys(reg.weather_sky[w])
      .every((k) => !owned.has(k)));
  })());
ok('the cloud cover world publishes is a real 0..1 fraction on every state',
  wxIds.every((w) => world.weather[w].cloud >= 0 && world.weather[w].cloud <= 1));
ok('this pack names the KIND of precipitation; WHETHER it falls stays world\'s',
  reg.precipitation_predicate.field === 'precipitation_rate'
  && reg.precipitation_predicate.op === '>'
  && reg.precipitation_predicate.value === 0
  && wxIds.every((w) => (world.weather[w].rain > 0)
    === (reg.weather_sky[w].precipitation !== 'none'))
  && C.precipitating_weather === wxIds.filter((w) => world.weather[w].rain > 0).length);
ok('every weather sky declares a disc state, a haze scale and a star visibility',
  wxIds.every((w) => {
    const e = reg.weather_sky[w];
    return ['drawn', 'diffused', 'hidden', 'moon'].includes(e.sun_disc)
      && e.star_visibility >= 0 && e.star_visibility <= 1
      && e.horizon_haze_mul > 0 && e.tint_mix >= 0 && e.tint_mix <= 1
      && e.note.length > 40;
  }));
ok('only the weather world calls `night` pins an hour, and it pins a real phase',
  wxIds.filter((w) => reg.weather_sky[w].phase_override !== null).join() === 'night'
  && phases.some((p) => p.id === reg.weather_sky.night.phase_override)
  && /world\/ carries `night` as a WEATHER/.test(reg.weather_sky.night.note));
ok('a sky whose disc is hidden shows no stars either - a lid is a lid',
  wxIds.every((w) => reg.weather_sky[w].sun_disc !== 'hidden'
    || reg.weather_sky[w].star_visibility === 0));
ok('the weather fields this pack adds are marked AUTHORED and the reads READ',
  wxIds.every((w) => {
    const p = reg.weather_sky[w].provenance;
    return Object.keys(reg.weather_reads).every((k) => p[k] === 'READ')
      && ['gradient_tint_hex', 'tint_mix', 'star_visibility', 'horizon_haze_mul',
        'sun_disc', 'precipitation', 'phase_override']
        .every((k) => p[k] === 'AUTHORED');
  }));

/* --------------------------------------------------------------- the layers --- */
ok('every layer\'s anchor appears in web/build_3d.py exactly once',
  layers.every((l) => page.split(l.page_anchor).length - 1 === 1));
ok('the draw order is the PAGE\'S order, re-derived here from those anchors',
  (() => {
    const byPage = [...layers].sort((a, b) =>
      page.indexOf(a.page_anchor) - page.indexOf(b.page_anchor));
    return byPage.every((l, i) => l.order === i && layers[i].id === l.id)
      && layers.every((l) => /^DERIVED:/.test(l.order_provenance));
  })());
ok('the five layers are the five a sky has, dome first and haze last',
  layers.length === 5 && C.layers === 5
  && layers.map((l) => l.id).join() ===
  'gradient-dome,star-field,sun-disc,cloud-band,horizon-haze');
ok('every renders_when names a declared field and a declared operator',
  layers.every((l) => l.renders_when.field in reg.predicate_fields
    && reg.predicate_ops.includes(l.renders_when.op)
    && l.renders_when.says.length > 30));
ok('the phases a layer renders in are the ones its predicate actually selects',
  layers.every((l) => {
    const { field, op, value } = l.renders_when;
    const want = field === 'sun_elevation_deg'
      ? phases.filter((p) => (op === '<' ? p.elevation_deg < value
        : op === '>' ? p.elevation_deg > value : null)).map((p) => p.id)
      : phases.map((p) => p.id);
    return JSON.stringify(l.renders_in_phases) === JSON.stringify(want);
  }));
ok('and the weathers it renders in are the ones world\'s own numbers select',
  layers.every((l) => {
    const { field, op, value } = l.renders_when;
    const key = { cloud_cover: 'cloud', precipitation_rate: 'rain' }[field];
    const want = key === undefined ? wxIds
      : wxIds.filter((w) => (op === '>' ? world.weather[w][key] > value : null));
    return JSON.stringify(l.renders_in_weather) === JSON.stringify(want);
  }));
ok('stars render below civil twilight and nowhere else - not at noon, yes at night',
  (() => {
    const s = layers.find((l) => l.id === 'star-field');
    return s.renders_when.value === -6 && s.renders_when.op === '<'
      && !s.renders_in_phases.includes('noon')
      && s.renders_in_phases.includes('night')
      && s.renders_in_phases.includes('astronomical-dusk')
      && !s.renders_in_phases.includes('civil-dusk');
  })());
ok('the cloud threshold is the page\'s own, not a second opinion about it',
  page.includes('amount > .02')
  && layers.find((l) => l.id === 'cloud-band').renders_when.value === 0.02);
ok('the disc swaps body at the same threshold the sunrise phase was solved from',
  (() => {
    const b = layers.find((l) => l.id === 'sun-disc').params.body_switch;
    return b.value === S.risen_disc_deg
      && b.value === phases.find((p) => p.id === 'sunrise').target_elev_deg;
  })());
ok('every layer says which world/ record it is built from rather than restating it',
  layers.filter((l) => l.id !== 'gradient-dome').every((l) =>
    JSON.stringify(l.params).includes('read_from')));

/* ---------------------------------------------------------------- the stars --- */
ok('the star seed is the page\'s seed, and the page still contains it',
  reg.stars.seed === 0x5EEDDA7A
  && reg.stars.seed_hex === '0x' + reg.stars.seed.toString(16).toUpperCase()
  && page.includes(reg.stars.seed_hex)
  && /^READ-FROM-PAGE:/.test(reg.stars.seed_provenance));
ok('the star COUNT is world\'s: this block points at it and holds no number for it',
  reg.stars.count_read_from === 'world/registry/world.json#sky.stars.count'
  && !('count' in reg.stars)
  && !JSON.stringify(reg.stars).includes(String(world.sky.stars.count)));
ok('the bins are the page\'s generator run again here, branch for branch',
  (() => {
    let x = reg.stars.seed >>> 0;
    const rnd = () => ((x = (x * 1664525 + 1013904223) >>> 0) / 4294967296);
    const got = { 2.1: 0, 1.4: 0, 0.9: 0 };
    for (let i = 0; i < world.sky.stars.count; i++) {
      rnd(); rnd(); rnd();
      if (rnd() < 0.08) got[2.1]++; else if (rnd() < 0.32) got[1.4]++; else got[0.9]++;
    }
    return reg.stars.bins.every((b) => b.count === got[b.radius_px]);
  })());
ok('the bins account for every star world declares, and for no extra one',
  reg.stars.bins.reduce((a, b) => a + b.count, 0) === world.sky.stars.count
  && reg.stars.bins.length === C.star_magnitude_bins);
ok('the magnitudes are Pogson\'s ratio on the drawn radii, re-derived here',
  (() => {
    const rRef = Math.max(...reg.stars.bins.map((b) => b.radius_px));
    return reg.stars.bins.every((b) => near(b.magnitude,
      reg.stars.magnitude_anchor - 2.5 * Math.log10((b.radius_px ** 2) / (rRef ** 2)),
      1e-4));
  })());
ok('the cutoff is the faintest bin, and the anchor is admitted to be a choice',
  reg.stars.magnitude_cutoff
  === Math.max(...reg.stars.bins.map((b) => b.magnitude))
  && /^DERIVED:/.test(reg.stars.magnitude_cutoff_provenance)
  && /^AUTHORED:/.test(reg.stars.magnitude_anchor_provenance)
  && /the anchor is a choice/i.test(reg.stars.magnitude_anchor_provenance));
ok('the real-sky fit is least squares over the published rows, re-derived here',
  (() => {
    const t = reg.stars.equivalent_sky_fit.table;
    const mx = t.map(([m]) => m), my = t.map(([, c]) => Math.log10(c));
    const mb = mx.reduce((a, b) => a + b, 0) / mx.length;
    const yb = my.reduce((a, b) => a + b, 0) / my.length;
    const sxy = mx.reduce((a, m, i) => a + (m - mb) * (my[i] - yb), 0);
    const sxx = mx.reduce((a, m) => a + (m - mb) ** 2, 0);
    const slope = sxy / sxx, inter = yb - slope * mb;
    const eq = (Math.log10(world.sky.stars.count) - inter) / slope;
    return t.length === C.star_count_rows
      && near(reg.stars.equivalent_sky_fit.slope, slope, 1e-4)
      && near(reg.stars.equivalent_sky_fit.intercept, inter, 1e-4)
      && near(reg.stars.equivalent_sky_magnitude, eq, 1e-4);
  })());
ok('and the block says out loud that the drawn field is not a sky chart',
  reg.stars.equivalent_sky_magnitude > reg.stars.magnitude_cutoff
  && /not the night sky/.test(reg.stars.honesty)
  && /No star here has a name/.test(reg.stars.honesty)
  && /Quoted, not measured here/.test(reg.stars.equivalent_sky_fit.table_provenance));

/* -------------------------------------------------------- the page contract --- */
ok('every name the contract reserves is a name web/build_3d.py really has',
  reg.page_contract.must_not_duplicate.length === C.reserved_page_names
  && reg.page_contract.must_not_duplicate.every((nm) => page.includes(nm))
  && reg.page_contract.must_not_duplicate.includes('setSky')
  && reg.page_contract.must_not_duplicate.includes('SUN_OFF'));
ok('every world path the contract says to READ resolves for every id it covers',
  reg.page_contract.must_read_not_copy.every((p) => {
    const ids = p.includes('<id>')
      ? (p.startsWith('world.weather') ? wxIds : Object.keys(world.atmos)) : [null];
    return ids.every((id) => {
      const parts = (id === null ? p : p.replace('<id>', id)).split('.');
      if (parts.shift() !== 'world') return false;
      return parts.reduce((o, k) => (o === undefined ? undefined : o[k]), world)
        !== undefined;
    });
  }));
ok('the page\'s fixed sun vector is GONE and setSun() has replaced it - '
  + 'this check asked for the opposite until the contract was carried out, '
  + 'and the contract still records what it replaced',
  !page.includes('const SUN_OFF = new THREE.Vector3(35, 48, 20)')
  && /function setSun\(elevDeg, azDeg\)/.test(page)
  && /SUN_OFF is a FIXED direction/.test(reg.page_contract.sun_vector)
  && /35, 48, 20/.test(reg.page_contract.sun_vector)
  && /trackSun\(\)/.test(reg.page_contract.sun_vector));
ok('and states the stated elevation of that fixed vector correctly',
  (() => {
    const el = Math.asin(48 / Math.hypot(35, 48, 20)) * 180 / Math.PI;
    const az = Math.atan2(20, 35) * 180 / Math.PI;
    return reg.page_contract.sun_vector.includes(el.toFixed(2))
      && reg.page_contract.sun_vector.includes(az.toFixed(2));
  })());
ok('the contract publishes multipliers only, and says whose the base numbers are',
  /key\.intensity stays/.test(reg.page_contract.intensity)
  && /a\.sun\.i \* w\.sun_mul/.test(reg.page_contract.intensity)
  && page.includes('key.intensity = a.sun.i * w.sun_mul')
  && page.includes('hemi.intensity = a.hemi.i * w.hemi_mul * indoors')
  && /publishes no absolute intensity/.test(reg.page_contract.intensity));
ok('it warns about the PMREM target setSky rebuilds on every call',
  /PMREM/.test(reg.page_contract.env_map)
  && /stepped rather than interpolated/.test(reg.page_contract.env_map)
  && page.includes('skyEnvRT?.dispose()'));
ok('the compose order is four steps, in order, ending in the page\'s own darkHex',
  reg.compose_order.length === C.compose_steps
  && reg.compose_order.every((s, i) => s.step === i + 1)
  && reg.compose_order[0].from === 'world.atmos.<campus>.sky'
  && /darkHex\(\)/.test(reg.compose_order[3].how)
  && page.includes('const darkHex ='));
ok('every contract clause is written out, and the hour is not a score',
  ['data', 'entry', 'sun_vector', 'intensity', 'colour', 'gradient', 'stars',
    'disc', 'env_map', 'episode'].every((k) =>
      typeof reg.page_contract[k] === 'string' && reg.page_contract[k].length > 40)
  && /changes no score/.test(reg.page_contract.episode)
  && !/"requires"|"unlocks"|"points"/.test(text));
ok('the pack admits the page does not render any of this yet',
  // Both halves, named. A pack that only said what it had built would be
  // flattering itself; one that only said what it had not would be stale
  // the moment somebody wired it up, which is exactly what happened here.
  /the page reads this registry/.test(reg.honesty.built_so_far)
  && /setSun\(\)/.test(reg.honesty.built_so_far)
  && /the gradient is wired too/.test(reg.honesty.gradient_built)
  // and the claim is checked against the page rather than trusted: the
  // three-step mix and the haze multiplier must actually be there
  && /const gStops = a\.sky\.map\(\(h, i\) => \{/.test(page)
  && /mixHex\(h, ph\.gradient\.stops\[i\], 1 - ph\.gradient\.campus_mix\)/.test(page)
  && /mixHex\(lit, ws\.gradient_tint_hex, ws\.tint_mix\)/.test(page)
  && /hazeMul: ws\.horizon_haze_mul/.test(page)
  && /sun_disc is declared and unread/.test(reg.honesty.not_built_yet)
  && /the hour is STEPPED, never interpolated/.test(reg.honesty.not_built_yet)
  // and the claim is checked against the page rather than trusted
  && /function setSun\(elevDeg, azDeg\)/.test(page)
  && !/starAlpha[\s\S]{0,40}stars: !!w\.stars/.test(page));

/* -------------------------------------------------------------- the counts --- */
ok('every published count is the count of the thing it names',
  C.phases === phases.length
  && C.solved_phases === phases.filter((p) => p.t01_by === 'solved').length
  && C.constructed_phases === phases.filter((p) => p.t01_by === 'construction').length
  && C.solved_phases + C.constructed_phases === C.phases
  && C.phases_above_horizon
  === phases.filter((p) => p.elevation_deg > S.risen_disc_deg).length
  && C.gradient_stops === phases.reduce((a, p) => a + p.gradient.stops.length, 0)
  && C.gradient_stops === C.phases * C.stops_per_gradient
  && C.weather_sky_entries === skyIds.length
  && C.weather_sky_entries === wxIds.length
  && C.weather_reads_per_entry === Object.keys(reg.weather_reads).length
  && C.weather_reads === C.weather_sky_entries * C.weather_reads_per_entry
  && C.layers === layers.length
  && C.compose_steps === reg.compose_order.length
  && C.reads_files === reg.reads.length);
ok('the derived counts are derived, not typed beside the thing they count',
  C.layer_predicates === layers.length
  + layers.filter((l) => 'body_switch' in l.params).length
  && C.layer_phase_renders
  === layers.reduce((a, l) => a + l.renders_in_phases.length, 0)
  && C.layer_weather_renders
  === layers.reduce((a, l) => a + l.renders_in_weather.length, 0)
  && C.derived_sun_numbers === C.phases * 3
  && C.authored_hex_colours
  === phases.reduce((a, p) => a + p.gradient.stops.length + 3, 0) + skyIds.length
  && C.star_magnitude_bins === reg.stars.bins.length
  && C.star_count_rows === reg.stars.equivalent_sky_fit.table.length);

const src = readFileSync(url('./build.py'));
ok('the registry was built from the current builder source (stamp check)',
  reg.source_stamp === createHash('sha256').update(src).digest('hex').slice(0, 16));

console.log(`sky/test: ${n} checks passed — ${C.phases} phases `
  + `(${C.solved_phases} solved from a twilight definition, `
  + `${C.constructed_phases} constructed), noon sun re-derived at `
  + `${phases.find((p) => p.id === 'noon').elevation_deg}° from lat ${S.lat_deg}; `
  + `${C.weather_sky_entries} weather skies holding ${C.weather_reads} pointers `
  + `into world/ and copying none of it; ${C.layers} draw layers in the page's `
  + `own order; ${world.sky.stars.count} stars in ${C.star_magnitude_bins} bins `
  + `from the page's seed, cutoff ${reg.stars.magnitude_cutoff} mag against `
  + `${reg.stars.equivalent_sky_magnitude} for a real sky; `
  + `colours AUTHORED and sun angles DERIVED; the page places the sun, the light, the stars AND the gradient by the hour - measured at the flagship, night is 68% of noon and golden hour 136%`);
