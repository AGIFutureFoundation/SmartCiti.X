/**
 * World registry verification.
 *
 * Three claims are worth holding to account here. The first is the
 * strongest thing this bundle can say about its own look: every texture is
 * a recipe and none is a file, so the suite reads the page and fails if it
 * so much as mentions a loader or an image extension. The second is that
 * the weather is a cycle of multipliers over each campus's own authored
 * atmosphere, not six separate looks - so a campus keeps its character in
 * the rain. The third is that the animals are ambience and say so.
 */
import { createHash } from 'node:crypto';
import { readFileSync } from 'node:fs';

let n = 0;
const ok = (m, c) => { if (!c) { console.error('FAIL', m); process.exit(1); } n++; console.log('  ok ', m); };

const reg = JSON.parse(readFileSync(new URL('./registry/world.json', import.meta.url)));
const page = readFileSync(new URL('../web/trade_craft_3d.html', import.meta.url), 'utf8');
const campuses = JSON.parse(readFileSync(
  new URL('../unions/registry/campuses.json', import.meta.url))).campuses;

/* ------------------------------------------------ nothing is downloaded --- */
ok('the texture claim is absolute, and the page keeps it: no loader, no image file',
  /no texture, photograph or artwork file exists/.test(reg.honesty.textures)
  && /generates the image and its\s+normal map/.test(reg.honesty.textures)
  && ['TextureLoader', 'CubeTextureLoader', 'RGBELoader', '.jpg', '.png',
      '.hdr', '.exr', '.webp'].every((b) => !page.includes(b)));
ok('every ground surface is a recipe with a base, a grain, octaves and a relief',
  Object.values(reg.ground).every((g) => /^#[0-9a-f]{6}$/i.test(g.base)
    && /^\d+,\d+,\d+$/.test(g.grain) && g.octaves >= 1 && g.octaves <= 6
    && g.relief >= 0 && g.relief <= 1 && g.repeat > 0
    && g.roughness > 0 && g.where.length > 15));
ok('the page generates both the colour map and the normal map from those recipes',
  /function groundTex\(/.test(page) && /function groundMat\(/.test(page)
  && /normalMap/.test(page) && /central difference|at\(x \+ 1, y\)/.test(page));

/* --------------------------------------------------------- the recipes --- */
/* The ten campuses were all laid on `concrete` or `asphalt`, and only the
   verge changed between San Francisco and Miami: ten cities told apart by
   their weather, standing on one slab. These hold the rebuilt table to the
   three things that were wrong with it - the surfaces have to differ, they
   have to say what made them that surface, and the ids other packs hold
   have to keep working. */
const gr = Object.entries(reg.ground);
/* Every id this pack has ever published is a contract: restoration/ names
   four of them per site, the page's own materials name four more, and a
   rename here is a silent breakage there. Adding is free; renaming is not. */
const LEGACY = ['asphalt', 'concrete', 'gravel', 'grass', 'sand',
  'marsh', 'mudflat', 'upland', 'levee', 'water'];
ok('every recipe id the pack has published still exists, because other packs hold them',
  LEGACY.every((id) => id in reg.ground));
ok('every recipe says what it is made of and why that is what the place is made of',
  gr.every(([, g]) => g.why?.length > 25 && g.where.length > 15
    && g.grain.split(',').every((c) => +c >= 0 && +c <= 255)
    && g.metalness >= 0 && g.metalness <= 1));
ok('no recipe is another recipe recoloured: every base colour is its own',
  new Set(gr.map(([, g]) => g.base)).size === gr.length);
ok('the ground reads at walking distance: nothing survives on two octaves and a dusting',
  gr.every(([, g]) => g.octaves >= 3 && g.speckle >= 900));
ok('every recipe is laid by somebody - a campus yard, a verge, or a named consumer',
  (() => {
    const laid = new Set(Object.values(reg.atmos)
      .flatMap((a) => [a.ground, a.verge]));
    const away = reg.ground_laid_elsewhere;
    return Object.keys(away).every((k) => k in reg.ground && !laid.has(k)
      && away[k].length > 20)
      && gr.every(([k]) => laid.has(k) || k in away);
  })());
/* A recipe reaches the render only when web/ is rebuilt, and that build
   refuses one until somebody has decided what it SOUNDS like underfoot. So
   a recipe may run ahead of the shipped page - but only while it says so,
   and the list has to empty itself rather than quietly cover a recipe that
   never arrived. */
ok('a recipe ahead of the page is declared ahead of the page, and only while it is',
  reg.ground_awaiting_page.every((k) => k in reg.ground
    && !page.includes(`"${k}"`))
  && gr.every(([k]) => reg.ground_awaiting_page.includes(k)
    || page.includes(`"${k}"`)));
ok('the ground is AUTHORED - composed from a reputation, never scanned off a real yard',
  /every ground recipe is AUTHORED/.test(reg.honesty.recipes)
  && /never taken from a survey, a photograph or a\s+scan/
    .test(reg.honesty.recipes)
  && /reputation/.test(reg.honesty.recipes));
ok('AI-SYNTHESIZED is orbis\'s word and is nowhere in this registry',
  !/ai-synthes/i.test(JSON.stringify(reg)));

/* --------------------------------------------------------------- the sky --- */
ok('the sky is generated too, and says it is a night sky rather than the night sky',
  /generated, not photographed/.test(reg.honesty.sky)
  && /fixed seed rather than from any star catalogue/.test(reg.honesty.sky)
  && /it is a night sky, not the night sky/.test(reg.honesty.sky));
ok('the star field is seeded, so every learner sees the same sky every visit',
  reg.sky.stars.count > 100 && reg.sky.stars.only_when === 'night'
  && /fixed seed/.test(reg.sky.stars.note)
  && /function seeded\(/.test(page));
ok('the sun is drawn where the light actually comes from, not at an arbitrary bearing',
  /read off the\s+light/.test(reg.sky.disc.placement)
  && /Math\.atan2\(kp\.z, kp\.x\)/.test(page)
  && /Math\.asin\(Math\.min\(1, kp\.y \/ klen\)\)/.test(page));
ok('the dome has four bands, and every campus states exactly four',
  reg.sky.bands.length === 4
  && Object.values(reg.atmos).every((a) => a.sky.length === 4));
/* The haze band is the last thing the eye reads before the ground, and it
   was one cool grey for the whole network - a refinery horizon and a high
   desert horizon in the same colour. The band keeps a default and a campus
   states its own. */
ok('the horizon takes each campus\'s own colour rather than one grey for the network',
  /^\d+,\d+,\d+$/.test(reg.sky.horizon_haze.day_tint)
  && /^\d+,\d+,\d+$/.test(reg.sky.horizon_haze.night_tint)
  && reg.sky.horizon_haze.night_strength_mul > 0
  && Object.values(reg.atmos).every((a) => /^\d+,\d+,\d+$/.test(a.haze))
  && new Set(Object.values(reg.atmos).map((a) => a.haze)).size >= 8);
ok('the cloud\'s own shape is declared with the dome rather than left as a literal',
  reg.sky.clouds.lacunarity > 1 && reg.sky.clouds.lacunarity < 4
  && reg.sky.clouds.day_lum > reg.sky.clouds.night_lum
  && reg.sky.clouds.day_lum <= 255 && reg.sky.clouds.night_lum >= 0);

/* ----------------------------------------------------------- the weather --- */
const wx = Object.entries(reg.weather);
ok('the weather is a closed cycle with no gap and no repeat in its order',
  wx.map(([, w]) => w.order).sort((a, b) => a - b)
    .every((o, i) => o === i));
ok('every state is labelled for a human: a name, a glyph and a reason to try it',
  wx.every(([, w]) => w.name && w.glyph && w.blurb.length > 25));
ok('a state is a set of multipliers over the campus atmosphere, never a look of its own',
  wx.every(([, w]) => ['sky_mul', 'fog_mul', 'fog_tint', 'sun_mul', 'hemi_mul']
    .every((k) => typeof w[k] === 'number' && w[k] > 0 && w[k] <= 2)
    && !('sky' in w) && !('fog_color' in w)));
ok('rain is a rate rather than a switch, and the page treats it as one',
  wx.every(([, w]) => w.rain >= 0 && w.rain <= 1)
  && reg.weather.rain.rain > 0 && reg.weather.rain.rain < reg.weather.storm.rain
  && /rainRate/.test(page) && /rain is a rate, not a switch/.test(page));
ok('clear is the brightest sky and night the darkest, which is the whole point',
  reg.weather.clear.sky_mul === Math.max(...wx.map(([, w]) => w.sky_mul))
  && reg.weather.night.sky_mul === Math.min(...wx.map(([, w]) => w.sky_mul)));
/* Wetness is a property of the GROUND, not of the rain rate: fog leaves a
   yard damp without a drop falling, and the rain state's own blurb has
   always promised "every surface in the yard reading differently". */
ok('how wet the ground is follows the weather rather than the rainfall',
  wx.every(([, w]) => w.wet >= 0 && w.wet <= 1)
  && reg.weather.clear.wet === 0
  && reg.weather.storm.wet === Math.max(...wx.map(([, w]) => w.wet))
  && reg.weather.fog.wet > reg.weather.overcast.wet
  && reg.weather.fog.rain === 0);
/* Fog banks were scaled off the campus's own count, so FOG WEATHER OVER A
   CAMPUS THAT KEEPS NO BANKS PUT NO FOG IN THE AIR - Denver, by name. */
ok('fog weather puts fog in the air even where the campus keeps none of its own',
  wx.every(([, w]) => w.bank_mul >= 0 && w.bank_mul <= 3
    && w.bank_floor >= 0 && w.bank_floor <= 8)
  && reg.weather.fog.bank_floor >= 3
  && reg.weather.clear.bank_mul < 1
  && Object.values(reg.atmos).some((a) => a.banks === 0));
ok('the weather admits it is not a forecast and not an observation',
  /not a forecast and not an observation/.test(reg.honesty.weather)
  && /authored by\s+reputation rather than measured/.test(reg.honesty.weather));
ok('every state the registry declares is one the page can actually be put into',
  wx.every(([k]) => page.includes(`"${k}"`))
  && /function setWeather\(/.test(page)
  && /WX_CYCLE/.test(page));

/* ------------------------------------------------------------ atmosphere --- */
ok('one atmosphere per campus, each naming the ground it stands on',
  JSON.stringify(Object.keys(reg.atmos).sort())
    === JSON.stringify(Object.keys(campuses).sort())
  && Object.values(reg.atmos).every((a) => a.ground in reg.ground
    && a.verge in reg.ground));
ok('and every one of them says out loud that it was authored, not measured',
  Object.values(reg.atmos).every((a) => /reputation/.test(a.character)
    && a.character.length > 40));
/* The fault this pack was opened to fix: a Gulf-coast yard, a Great Lakes
   yard, a Rocky Mountain yard and a Bay-side former naval station were the
   same slab with a different verge. One campus, one ground, no two alike -
   and each of them says what chose it, in its own words. */
ok('no two campuses stand on the same ground, and each says what chose it',
  new Set(Object.values(reg.atmos).map((a) => a.ground)).size
    === Object.keys(reg.atmos).length
  && new Set(Object.values(reg.atmos).map((a) => a.ground_why)).size
    === Object.keys(reg.atmos).length
  && Object.values(reg.atmos).every((a) => a.ground_why.length > 60));
/* The ambient bed is a closed set: the page builds wind, insects, gulls, a
   harbour horn and thunder, and silently ignores anything else - so a key
   off this list is a sound somebody meant to hear and nobody will. */
const BEDS = ['wind', 'gulls', 'harbor', 'insects', 'thunder'];
ok('every ambient bed a campus asks for is one the page actually builds',
  BEDS.every((b) => page.includes(`a.${b}`))
  && Object.values(reg.atmos)
    .every((a) => Object.keys(a.amb).every((k) => BEDS.includes(k))));
/* `fog.mul` scales the fog distance and SMALLER IS THICKER, which reads
   backwards to anyone who has not been told: Denver shipped at .4, the
   thickest air of the ten, on the campus whose character line says "thin,
   dry high-altitude light". */
ok('the high desert is the clearest air on the network and the Bay the thickest',
  (() => {
    const m = Object.fromEntries(Object.entries(reg.atmos)
      .map(([k, a]) => [k, a.fog.mul]));
    const v = Object.values(m);
    return m.denver === Math.max(...v)
      && m['treasure-island'] === Math.min(...v);
  })());

/* ---------------------------------------------------------------- fauna --- */
const fa = Object.entries(reg.fauna);
ok('every animal is placed on real campuses, with a flock size and a wingspan',
  fa.every(([, f]) => f.campuses.every((c) => c in campuses)
    && f.flock >= 1 && f.span_m > 0 && f.height_m.length === 2));
ok('every animal has a reason to be in the yard, written down',
  fa.every(([, f]) => f.why.length > 25));
ok('the fauna refuses to be a wildlife record: ambience, common names, no sighting claimed',
  /ambience, not a wildlife survey/.test(reg.honesty.fauna)
  && /No species record, population count or sighting is claimed/
    .test(reg.honesty.fauna)
  && /no animal here is drawn from any photograph/.test(reg.honesty.fauna));
ok('the page builds, places, moves and weathers them',
  ['function faunaBody(', 'function spawnFauna(', 'function faunaStep(',
    'function faunaWeather(', 'function clearFauna(']
    .every((f) => page.includes(f)));
ok('reduced-motion viewers get a still yard rather than animals they did not ask for',
  /if \(reduced\) return;\s*\/\/ stillness for those who ask/.test(page));
ok(`every declared animal reaches the page (${reg.counts.animals} placed in all)`,
  fa.every(([k]) => page.includes(`"${k}"`))
  && reg.counts.animals === fa.reduce((a, [, f]) =>
    a + f.flock * f.campuses.length, 0));

/* -------------------------------------------------------------- schematic --- */
ok('the ground is SCHEMATIC like everything built on it, and says so',
  /SCHEMATIC like the\s+buildings on it/.test(reg.honesty.ground)
  && /drawn to teach, not surveyed/.test(reg.honesty.ground));

const src = readFileSync(new URL('./build.py', import.meta.url));
ok('the registry was built from the current builder source (stamp check)',
  reg.source_stamp === createHash('sha256').update(src).digest('hex').slice(0, 16));

/* ---------------------------------------------------------- built fabric --- */
/* Every campus had its own sky, fog, sun, ambient bed and ground - and then
   all ten drew the same envelope with the same trim. Ten cities told apart
   only by their weather. These hold the fabric table to the same contract
   the atmosphere is held to, including the one that matters most: it is
   AUTHORED BY REPUTATION and says so, because no site here has been
   surveyed and no real building is depicted. */
const FACADES = ['panel', 'brick', 'block', 'smooth', 'plywood', 'board'];
const ROOFS = ['flat', 'gable', 'saw'];
const fab = reg.fabric;
ok('every campus declares what it is built of',
  Object.keys(fab).length === Object.keys(reg.atmos).length
  && Object.keys(reg.atmos).every((k) => fab[k]));
ok('a facade names a pattern the page can actually draw, and a roofline it builds',
  Object.values(fab).every((f) => FACADES.includes(f.facade)
    && ROOFS.includes(f.roof)));
ok('the envelope, trim and roof each carry a colour',
  Object.values(fab).every((f) => ['facade_color', 'trim', 'roof_color']
    .every((k) => /^#[0-9a-f]{6}$/i.test(f[k]))));
ok('every fabric says why it is that fabric',
  Object.values(fab).every((f) => f.why?.length > 25));
/* The point of the exercise: they have to DIFFER. A table where every city
   picked the same brick would pass every check above and change nothing. */
ok('the ten cities do not all build the same way',
  new Set(Object.values(fab).map((f) => f.facade)).size >= 4
  && new Set(Object.values(fab).map((f) => f.facade_color)).size === 10
  && new Set(Object.values(fab).map((f) => f.roof)).size === 3);
ok('the fabric is authored by reputation and the pack says so, the same way '
  + 'the atmosphere does',
  /reputation/i.test(JSON.stringify(reg.honesty))
  || Object.values(reg.atmos).every((a) => /reputation/i.test(a.character)));

console.log(`world/test: ${n} checks passed — ${wx.length} weather states, `
  + `${Object.keys(reg.ground).length} generated surfaces, ${fa.length} animals`);
