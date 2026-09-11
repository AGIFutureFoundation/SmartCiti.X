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

console.log(`world/test: ${n} checks passed — ${wx.length} weather states, `
  + `${Object.keys(reg.ground).length} generated surfaces, ${fa.length} animals`);
